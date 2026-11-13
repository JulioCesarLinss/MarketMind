"""Conta lojas do mesmo ramo perto da localização informada (OpenStreetMap).

- Nominatim: transforma "bairro, cidade" em coordenadas.
- Overpass: conta os estabelecimentos de uma categoria num raio.
- Nominatim por categoria ("hairdresser", "cafe"...) num quadrado ao redor do ponto: roda junto
  com o Overpass e cobre quando os servidores do Overpass estão sobrecarregados (é comum).

Limitações (sempre mostradas ao usuário): o OpenStreetMap não tem todas as lojas pequenas
do Brasil, então o número é um PISO ("pelo menos N mapeadas"), não o total.
Regras de uso: no máximo 1 pedido por segundo ao Nominatim e User-Agent identificando o app.
"""

import asyncio
import logging
import math
import re
from dataclasses import dataclass, field

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "MarketMind/0.1 (+https://github.com/JulioCesarLinss/MarketMind)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Lista FECHADA de categorias: a IA escolhe uma delas (não inventa tags do OpenStreetMap)
CATEGORIAS: dict[str, list[str]] = {
    "restaurante": ['["amenity"="restaurant"]'],
    "lanchonete": ['["amenity"="fast_food"]'],
    "hamburgueria": ['["cuisine"~"burger"]'],
    "pizzaria": ['["cuisine"~"pizza"]'],
    "cafeteria": ['["amenity"="cafe"]'],
    "padaria": ['["shop"="bakery"]'],
    "doceria_confeitaria": ['["shop"~"^(confectionery|pastry)$"]'],
    "sorveteria": ['["amenity"="ice_cream"]'],
    "bar": ['["amenity"~"^(bar|pub)$"]'],
    "barbearia_salao": ['["shop"~"^(hairdresser|barber)$"]'],
    "estetica_beleza": ['["shop"~"^(beauty|cosmetics)$"]'],
    "academia": ['["leisure"="fitness_centre"]'],
    "roupas": ['["shop"~"^(clothes|boutique)$"]'],
    "calcados": ['["shop"="shoes"]'],
    "mercado": ['["shop"~"^(supermarket|convenience|greengrocer)$"]'],
    "farmacia": ['["amenity"="pharmacy"]'],
    "pet_shop": ['["shop"="pet"]'],
    "eletronicos_celular": ['["shop"~"^(electronics|mobile_phone|computer)$"]'],
    "oficina_mecanica": ['["shop"~"^(car_repair|motorcycle_repair)$"]'],
    "lavanderia": ['["shop"~"^(laundry|dry_cleaning)$"]'],
    "papelaria_presentes": ['["shop"~"^(stationery|gift)$"]'],
    "outro": [],  # só pelas palavras-chave do nome
}


@dataclass
class LojasEncontradas:
    quantidade: int
    nomes: list[str] = field(default_factory=list)
    fonte: str = ""
    parcial: bool = False  # True = plano B (busca por nome): conta bem menos que o real, não serve para medir concorrência


def _escapar_regex(palavra: str) -> str:
    return re.sub(r"[^\w\sÀ-ÿ-]", "", palavra).strip()


def montar_consulta_overpass(lat: float, lon: float, categoria: str, palavras: list[str], raio: int) -> str:
    filtros = list(CATEGORIAS.get(categoria, []))
    palavras = [p for p in (_escapar_regex(p) for p in palavras) if len(p) >= 3][:3]
    if palavras:
        filtros.append(f'["name"~"{"|".join(palavras)}",i]')
    if not filtros:
        raise ValueError("categoria 'outro' exige palavras-chave")
    partes = "".join(f"nwr{f}(around:{raio},{lat},{lon});" for f in filtros)
    return f"[out:json][timeout:25];({partes});out tags center 150;"


async def geocodificar(client: httpx.AsyncClient, localizacao: str) -> tuple[float, float, str] | None:
    resposta = await client.get(
        NOMINATIM, params={"q": localizacao, "format": "jsonv2", "limit": 1, "countrycodes": "br"}
    )
    if resposta.status_code != 200 or not resposta.json():
        return None
    r = resposta.json()[0]
    return float(r["lat"]), float(r["lon"]), r.get("display_name", "")


def _nomes_unicos(elementos: list[dict]) -> list[str]:
    vistos, nomes = set(), []
    for e in elementos:
        nome = (e.get("tags") or {}).get("name")
        if nome and nome.lower() not in vistos:
            vistos.add(nome.lower())
            nomes.append(nome)
    return nomes


async def _consultar_um(client, url: str, consulta: str) -> LojasEncontradas | None:
    try:
        resposta = await client.post(url, data={"data": consulta}, timeout=12)
        if resposta.status_code == 200:
            elementos = resposta.json().get("elements", [])
            ids = {(e.get("type"), e.get("id")) for e in elementos}
            return LojasEncontradas(len(ids), _nomes_unicos(elementos)[:10], "OpenStreetMap (Overpass)")
        log.warning("Overpass %s respondeu HTTP %s", url, resposta.status_code)
    except (httpx.HTTPError, ValueError) as erro:
        log.warning("Overpass %s falhou (%s)", url, type(erro).__name__)
    return None


async def _contar_overpass(client, lat, lon, categoria, palavras, raio) -> LojasEncontradas | None:
    """Pergunta aos servidores públicos AO MESMO TEMPO e usa a primeira resposta boa
    (eles vivem sobrecarregados; um de cada vez demoraria demais)."""
    consulta = montar_consulta_overpass(lat, lon, categoria, palavras, raio)
    tarefas = [asyncio.create_task(_consultar_um(client, url, consulta)) for url in OVERPASS]
    try:
        for proxima in asyncio.as_completed(tarefas):
            lojas = await proxima
            if lojas is not None:
                return lojas
        return None
    finally:
        for t in tarefas:
            t.cancel()


# Como achar cada categoria no Nominatim: frases (de preferência as "special phrases" do OpenStreetMap,
# em inglês, testadas em Recife; lojas usam "X shop")
# e os tipos aceitos (categoria/tipo que o Nominatim devolve). Categorias por cozinha (hamburgueria,
# pizzaria) não têm frase própria: entram pelas palavras do nome, filtradas pelos tipos aceitos.
NOMINATIM_TIPOS: dict[str, tuple[list[str], set[tuple[str, str]]]] = {
    "restaurante": (["restaurant"], {("amenity", "restaurant")}),
    "lanchonete": (["fast food"], {("amenity", "fast_food")}),
    "hamburgueria": ([], {("amenity", "fast_food"), ("amenity", "restaurant")}),
    "pizzaria": ([], {("amenity", "fast_food"), ("amenity", "restaurant")}),
    "cafeteria": (["cafe"], {("amenity", "cafe")}),
    "padaria": (["bakery"], {("shop", "bakery")}),
    "doceria_confeitaria": (["confectionery shop", "doceria"], {("shop", "confectionery"), ("shop", "pastry")}),
    "sorveteria": (["ice cream"], {("amenity", "ice_cream"), ("shop", "ice_cream")}),
    "bar": (["bar"], {("amenity", "bar"), ("amenity", "pub")}),
    "barbearia_salao": (["hairdresser", "barbearia"], {("shop", "hairdresser"), ("shop", "barber")}),
    "estetica_beleza": (["beauty shop", "cosmetics shop"], {("shop", "beauty"), ("shop", "cosmetics")}),
    "academia": (["academia", "fitness"], {("leisure", "fitness_centre"), ("leisure", "sports_centre"), ("amenity", "gym")}),
    "roupas": (["clothes shop"], {("shop", "clothes"), ("shop", "boutique")}),
    "calcados": (["shoe shop"], {("shop", "shoes")}),
    "mercado": (["supermarket", "convenience store"], {("shop", "supermarket"), ("shop", "convenience"), ("shop", "greengrocer")}),
    "farmacia": (["pharmacy"], {("amenity", "pharmacy"), ("shop", "chemist")}),
    "pet_shop": (["pet shop"], {("shop", "pet")}),
    "eletronicos_celular": (["electronics shop", "mobile phone shop"], {("shop", "electronics"), ("shop", "mobile_phone"), ("shop", "computer")}),
    "oficina_mecanica": (["car repair", "oficina"], {("shop", "car_repair"), ("shop", "motorcycle_repair")}),
    "lavanderia": (["lavanderia", "laundry"], {("shop", "laundry"), ("shop", "dry_cleaning")}),
    "papelaria_presentes": (["stationery shop", "gift shop"], {("shop", "stationery"), ("shop", "gift")}),
    "outro": ([], set()),
}
CATEGORIAS_POI = {"shop", "amenity", "leisure", "craft", "office", "tourism"}
# Na busca só pelo nome (categoria "outro"), academias, parques e hotéis dão falso positivo
# (ex.: "fitness" acha academias quando o negócio é marmita fitness)
CATEGORIAS_POI_SO_NOME = {"shop", "amenity", "craft", "office"}
TIPOS_IGNORADOS = {("amenity", "parking"), ("amenity", "school"), ("amenity", "place_of_worship"), ("amenity", "bank")}
LIMITE_NOMINATIM = 50  # máximo por busca; se uma busca enche, o número é um piso ("pelo menos")


def distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(a))


def filtrar_nominatim(resultados: list[dict], lat: float, lon: float, raio: int,
                      aceitos: set[tuple[str, str]], por_tipo: bool) -> dict[str, str]:
    """Fica só com estabelecimentos do ramo dentro do raio. Devolve {id_osm: nome}."""
    lojas = {}
    for r in resultados:
        tipo = (r.get("category", ""), r.get("type", ""))
        if por_tipo and tipo not in aceitos:
            continue
        if not por_tipo:  # busca por nome: descarta ruas, bairros e lojas de outro ramo
            if aceitos and tipo not in aceitos:
                continue
            if not aceitos and (tipo[0] not in CATEGORIAS_POI_SO_NOME or tipo in TIPOS_IGNORADOS):
                continue
        try:
            if distancia_metros(lat, lon, float(r["lat"]), float(r["lon"])) > raio:
                continue
        except (KeyError, ValueError):
            continue
        lojas[f"{r.get('osm_type')}{r.get('osm_id')}"] = r.get("name") or ""
    return lojas


async def _contar_nominatim(client, lat, lon, categoria, palavras, raio) -> LojasEncontradas | None:
    """Busca por categoria (e por palavras do nome) só dentro de um quadrado ao redor do ponto."""
    frases, aceitos = NOMINATIM_TIPOS.get(categoria, ([], set()))
    consultas = [(f, True) for f in frases] + [(p, False) for p in palavras[:2] if len(p.strip()) >= 3]
    d_lat = raio / 111_000
    d_lon = raio / (111_000 * max(math.cos(math.radians(lat)), 0.1))
    caixa = f"{lon - d_lon},{lat + d_lat},{lon + d_lon},{lat - d_lat}"
    lojas: dict[str, str] = {}
    respondeu = False
    for q, por_tipo in consultas:
        await asyncio.sleep(1.1)  # regra de uso do Nominatim: 1 pedido por segundo
        try:
            resposta = await client.get(NOMINATIM, params={"q": q, "format": "jsonv2", "limit": LIMITE_NOMINATIM,
                                                           "viewbox": caixa, "bounded": 1})
        except httpx.HTTPError as erro:
            log.warning("Nominatim falhou para '%s' (%s)", q, type(erro).__name__)
            continue
        if resposta.status_code != 200:
            log.warning("Nominatim respondeu HTTP %s para '%s'", resposta.status_code, q)
            continue
        respondeu = True
        lojas.update(filtrar_nominatim(resposta.json(), lat, lon, raio, aceitos, por_tipo))
    if not respondeu:
        return None
    nomes = list(dict.fromkeys(n for n in lojas.values() if n))
    return LojasEncontradas(len(lojas), nomes[:10], "OpenStreetMap (Nominatim)")


async def contar_lojas(localizacao: str, categoria: str, palavras: list[str], raio: int) -> tuple[LojasEncontradas | None, str | None]:
    """Devolve (lojas, erro). Nunca levanta exceção: a simulação segue mesmo sem a contagem.

    O Overpass (mais completo) e o Nominatim (mais estável) rodam AO MESMO TEMPO:
    usa o Overpass se ele responder; senão, o Nominatim. Os servidores públicos do Overpass
    vivem sobrecarregados, então não dá para depender só deles."""
    try:
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
            local = await geocodificar(client, localizacao)
            if not local:
                return None, f"não foi possível localizar '{localizacao}' no mapa"
            lat, lon, _ = local
            overpass = (asyncio.create_task(_contar_overpass(client, lat, lon, categoria, palavras, raio))
                        if CATEGORIAS.get(categoria) or palavras else None)
            nominatim = await _contar_nominatim(client, lat, lon, categoria, palavras, raio)
            lojas = None
            if overpass:
                try:
                    lojas = await asyncio.wait_for(overpass, timeout=5)  # o Nominatim já levou alguns segundos
                except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                    lojas = None
            lojas = lojas or nominatim
            if lojas is None:
                return None, "serviços do OpenStreetMap indisponíveis no momento"
            return lojas, None
    except Exception as erro:  # noqa: BLE001
        log.exception("Contagem de lojas falhou")
        return None, f"falha ao consultar o mapa ({type(erro).__name__})"


def nivel_concorrencia(quantidade: int | None, parcial: bool = False) -> str:
    if quantidade is None or parcial:
        return "indeterminado"
    if quantidade == 0:
        return "nenhum concorrente mapeado"
    if quantidade <= 3:
        return "baixa"
    if quantidade <= 10:
        return "media"
    return "alta"
