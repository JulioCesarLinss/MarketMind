"""Conta lojas do mesmo ramo perto da localização informada (OpenStreetMap).

- Nominatim: transforma "bairro, cidade" em coordenadas.
- Overpass: conta os estabelecimentos de uma categoria num raio.
- Plano B (se o Overpass estiver fora do ar): busca por nome no próprio Nominatim.

Limitações (sempre mostradas ao usuário): o OpenStreetMap não tem todas as lojas pequenas
do Brasil, então o número é um PISO ("pelo menos N mapeadas"), não o total.
Regras de uso: no máximo 1 pedido por segundo ao Nominatim e User-Agent identificando o app.
"""

import asyncio
import logging
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
        resposta = await client.post(url, data={"data": consulta}, timeout=15)
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


async def _contar_nominatim(client, localizacao, palavras) -> LojasEncontradas | None:
    nomes: list[str] = []
    for palavra in palavras[:2]:
        await asyncio.sleep(1.1)  # regra de uso do Nominatim: 1 pedido por segundo
        resposta = await client.get(
            NOMINATIM, params={"q": f"{palavra}, {localizacao}", "format": "jsonv2", "limit": 40, "countrycodes": "br"}
        )
        if resposta.status_code == 200:
            nomes += [r.get("name") for r in resposta.json() if r.get("name")]
    unicos = list(dict.fromkeys(nomes))
    return LojasEncontradas(len(unicos), unicos[:10], "OpenStreetMap (Nominatim, busca por nome)", parcial=True)


async def contar_lojas(localizacao: str, categoria: str, palavras: list[str], raio: int) -> tuple[LojasEncontradas | None, str | None]:
    """Devolve (lojas, erro). Nunca levanta exceção: a simulação segue mesmo sem a contagem."""
    try:
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
            local = await geocodificar(client, localizacao)
            if not local:
                return None, f"não foi possível localizar '{localizacao}' no mapa"
            lat, lon, _ = local
            lojas = await _contar_overpass(client, lat, lon, categoria, palavras, raio)
            if lojas is None and palavras:
                lojas = await _contar_nominatim(client, localizacao, palavras)
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
