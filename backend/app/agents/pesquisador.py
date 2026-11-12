"""Agente pesquisador: monta uma referência de mercado ANTES do debate.

Etapas:
    1. IA planeja: 3 buscas (popular, intermediária, premium) + categoria do mapa + palavras do nome.
    2. Busca na internet (Tavily/Ollama) e, ao mesmo tempo, conta lojas no mapa (OpenStreetMap).
    3. O código recorta só os trechos com preços (R$) — menos tokens e menos ruído.
    4. IA extrai os exemplos (estabelecimento, item, preço, faixa, trecho de origem).
    5. O CÓDIGO valida (o preço tem que estar escrito no trecho) e calcula média, desvio-padrão,
       mínimo, máximo e a posição do preço do usuário. A IA não calcula nenhum número.

Qualquer parte pode falhar sem derrubar a simulação: o que deu certo é usado, o resto vira `erro`.
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from statistics import mean, pstdev

from app.agents.contexto import formatar_negocio
from app.config import settings
from app.llm.base import LLMProvider
from app.models.pesquisa import (
    FAIXAS,
    ExemploMercado,
    ExtracaoMercado,
    FaixaMercado,
    Fonte,
    LojasRegiao,
    PesquisaMercado,
    PlanoPesquisa,
    PosicaoPreco,
)
from app.services import mapa
from app.services.busca import BuscaIndisponivelError, BuscaWeb, ResultadoBusca

log = logging.getLogger(__name__)

PRECO_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)")
JANELA = 120            # caracteres antes/depois de cada preço
MAX_TRECHOS_FONTE = 6
MAX_TRECHOS = 25        # limita os tokens da extração (o limite do Groq grátis é por minuto)
MAX_POR_LOJA = 3        # no máximo 3 preços por estabelecimento
MIN_PARA_TERCOS = 6     # a partir daqui, as faixas são definidas pelos terços de preço
FAIXA_VALIDA = (0.2, 5.0)  # descarta preços < 20% ou > 5x o preço do usuário (ex.: "R$ 1,00" de taxa)
CACHE_HORAS = 24

SISTEMA_PLANO = """Você ajuda a pesquisar preços de mercado para um pequeno negócio no Brasil.
A partir dos dados do negócio, identifique o tipo de estabelecimento concorrente, o produto ou serviço comparável
(como um cliente digitaria numa busca) e a cidade. Use termos simples e genéricos, sem adjetivos de posicionamento
(nada de "premium" ou "barato": as buscas por faixa são montadas depois)."""


def montar_consultas(plano: PlanoPesquisa) -> list[str]:
    """Três buscas no mesmo padrão (geral, popular, premium): previsível e sem repetição."""
    base = " ".join(dict.fromkeys(f"{plano.tipo_estabelecimento} {plano.cidade}".split()))  # evita palavra repetida
    produto = plano.produto_comparavel.strip()
    return [
        f"{base} preço {produto}",
        f"{base} barato popular preço {produto}",
        f"{base} premium preço {produto}",
    ]

SISTEMA_EXTRACAO = """Você extrai preços de trechos de páginas da internet para comparar com uma oferta.
Regras:
- Liste apenas itens COMPARÁVEIS à oferta (mesmo tipo de produto ou serviço).
- Use somente preços escritos nos trechos. Nunca invente, arredonde ou calcule preços.
- Classifique cada estabelecimento em uma faixa (popular, intermediaria, premium) pelo posicionamento e pelo preço.
- Ignore taxas, fretes, descontos isolados e itens de outro tipo."""


def _numero(texto: str) -> float | None:
    """'1.234,56' → 1234.56 · '32,90' → 32.9 · '45' → 45.0"""
    t = texto.strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def precos_no_texto(texto: str) -> list[float]:
    return [v for v in (_numero(m) for m in PRECO_RE.findall(texto)) if v is not None]


def recortar_trechos(resultados: list[ResultadoBusca], preco_usuario: float) -> list[dict]:
    """Recorta janelas de texto ao redor de preços plausíveis. Devolve [{id, url, titulo, texto}]."""
    minimo, maximo = preco_usuario * FAIXA_VALIDA[0], preco_usuario * FAIXA_VALIDA[1]
    trechos: list[dict] = []
    urls_vistas = set()
    for r in resultados:
        if not r.url or r.url in urls_vistas:
            continue
        urls_vistas.add(r.url)
        texto = " ".join(r.conteudo.split())
        janelas: list[list[int]] = []
        for m in PRECO_RE.finditer(texto):
            valor = _numero(m.group(1))
            if valor is None or not (minimo <= valor <= maximo):
                continue
            ini, fim = max(0, m.start() - JANELA), min(len(texto), m.end() + JANELA)
            if janelas and ini <= janelas[-1][1]:
                janelas[-1][1] = fim  # junta janelas sobrepostas
            else:
                janelas.append([ini, fim])
        for ini, fim in janelas[:MAX_TRECHOS_FONTE]:
            trechos.append({"url": r.url, "titulo": r.titulo, "texto": texto[ini:fim]})
    trechos = trechos[:MAX_TRECHOS]
    for i, t in enumerate(trechos, 1):
        t["id"] = f"T{i}"
    return trechos


def validar_exemplos(linhas: list[str], trechos: list[dict]) -> list[ExemploMercado]:
    """Aceita só exemplos cujo preço está escrito no trecho citado (anti-invenção)."""
    por_id = {t["id"]: t for t in trechos}
    validos, vistos = [], set()
    for linha in linhas:
        partes = [p.strip() for p in linha.split("|")]
        if len(partes) != 5:
            continue
        faixa, estabelecimento, item, preco_txt, trecho_id = partes
        faixa = faixa.lower().replace("á", "a")
        preco = _numero(preco_txt.replace("R$", ""))
        achado = re.search(r"T\d+", trecho_id.upper())  # aceita "T3", "[T3]", "trecho T3"
        trecho = por_id.get(achado.group(0)) if achado else None
        if faixa not in FAIXAS or preco is None or not trecho or not estabelecimento:
            continue
        if not any(abs(preco - p) < 0.01 for p in precos_no_texto(trecho["texto"])):
            continue  # a IA citou um preço que não está no trecho
        chave = (estabelecimento.lower(), item.lower(), preco)
        if chave in vistos:
            continue
        # Limite por loja: uma loja com cardápio grande não pode dominar a média do mercado
        if sum(e.estabelecimento.lower() == estabelecimento.lower() for e in validos) >= MAX_POR_LOJA:
            continue
        vistos.add(chave)
        validos.append(ExemploMercado(faixa=faixa, estabelecimento=estabelecimento, item=item, preco=preco, fonte_url=trecho["url"]))
    return validos


def reclassificar_por_preco(exemplos: list[ExemploMercado]) -> list[ExemploMercado]:
    """Com preços suficientes, as faixas são os TERÇOS da distribuição de preços:
    o terço mais barato = popular, o do meio = intermediária, o mais caro = premium.
    É mais objetivo que a classificação da IA (que tende a jogar tudo no meio)."""
    if len(exemplos) < MIN_PARA_TERCOS:
        return exemplos
    ordenados = sorted(exemplos, key=lambda e: e.preco)
    n = len(ordenados)
    corte1, corte2 = round(n / 3), round(2 * n / 3)
    return [e.model_copy(update={"faixa": FAIXAS[0 if i < corte1 else 1 if i < corte2 else 2]})
            for i, e in enumerate(ordenados)]


def calcular_faixas(exemplos: list[ExemploMercado]) -> list[FaixaMercado]:
    exemplos = reclassificar_por_preco(exemplos)
    faixas = []
    for nome in FAIXAS:
        da_faixa = [e for e in exemplos if e.faixa == nome]
        precos = [e.preco for e in da_faixa]
        suficiente = len(precos) >= 2
        faixas.append(FaixaMercado(
            faixa=nome,
            quantidade=len(precos),
            media=round(mean(precos), 2) if precos else None,
            desvio_padrao=round(pstdev(precos), 2) if suficiente else None,
            minimo=min(precos) if precos else None,
            maximo=max(precos) if precos else None,
            dados_suficientes=suficiente,
            exemplos=da_faixa[:6],
        ))
    return faixas


def _reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def posicionar(preco: float, exemplos: list[ExemploMercado], faixas: list[FaixaMercado]) -> PosicaoPreco:
    precos = [e.preco for e in exemplos]
    media = round(mean(precos), 2) if precos else None
    desvio = round(pstdev(precos), 2) if len(precos) >= 2 else None
    z = round((preco - media) / desvio, 2) if media is not None and desvio else None
    com_media = [f for f in faixas if f.media is not None]
    proxima = min(com_media, key=lambda f: abs(preco - f.media)).faixa if com_media else None

    if media is None:
        resumo = "Não foram encontrados preços comparáveis suficientes na internet."
    else:
        diferenca = (preco - media) / media * 100
        direcao = "acima" if diferenca > 0 else "abaixo"
        resumo = f"Seu preço ({_reais(preco)}) está {abs(diferenca):.0f}% {direcao} da média encontrada ({_reais(media)})"
        if z is not None:
            resumo += f", {abs(z):.1f}".replace(".", ",") + f" desvio-padrão {direcao}"
        if proxima:
            nomes = {"popular": "popular", "intermediaria": "intermediária", "premium": "premium"}
            resumo += f"; o mais próximo é a faixa {nomes[proxima]}"
        resumo += "."
    return PosicaoPreco(preco_usuario=preco, media_mercado=media, desvio_padrao_mercado=desvio,
                        desvios_da_media=z, faixa_mais_proxima=proxima, resumo=resumo)


class Pesquisador:
    def __init__(self, ia_rapida: LLMProvider, ia_extracao: LLMProvider, busca: BuscaWeb | None, usar_mapa: bool = True):
        self.ia_rapida = ia_rapida
        self.ia_extracao = ia_extracao
        self.busca = busca
        self.usar_mapa = usar_mapa
        self._cache: dict[tuple, tuple[float, PesquisaMercado]] = {}

    def _chave(self, negocio: dict) -> tuple:
        return tuple(str(negocio.get(k, "")).strip().lower() for k in ("tipo", "produto", "localizacao", "preco"))

    async def executar(self, negocio: dict) -> PesquisaMercado:
        chave = self._chave(negocio)
        guardada = self._cache.get(chave)
        if guardada and time.time() - guardada[0] < CACHE_HORAS * 3600:
            return guardada[1]
        inicio = time.perf_counter()
        tokens_antes = self.ia_rapida.total_tokens() + self.ia_extracao.total_tokens()
        pesquisa = await self._pesquisar(negocio)
        pesquisa.tokens_usados = self.ia_rapida.total_tokens() + self.ia_extracao.total_tokens() - tokens_antes
        pesquisa.duracao_segundos = round(time.perf_counter() - inicio, 1)
        if pesquisa.tem_dados():
            self._cache[chave] = (time.time(), pesquisa)
        return pesquisa

    async def _pesquisar(self, negocio: dict) -> PesquisaMercado:
        preco = float(negocio.get("preco") or 0)
        pesquisa = PesquisaMercado(gerada_em=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                   provedor_busca=self.busca.nome if self.busca else None)

        # 1. Planejar (se falhar, não há como buscar nem contar com critério)
        try:
            plano = await self.ia_rapida.gerar(SISTEMA_PLANO, [{"role": "user", "content": formatar_negocio(negocio)}], PlanoPesquisa)
        except Exception as erro:  # noqa: BLE001
            log.exception("Pesquisador: planejamento falhou")
            pesquisa.erro = f"Não foi possível planejar a pesquisa ({type(erro).__name__})."
            return pesquisa
        pesquisa.consultas = montar_consultas(plano)

        # 2. Buscar preços e contar lojas ao mesmo tempo
        tarefa_mapa = (
            asyncio.create_task(mapa.contar_lojas(str(negocio.get("localizacao", "")), plano.categoria_mapa,
                                                  plano.palavras_nome, settings.mapa_raio_metros))
            if self.usar_mapa else None
        )
        resultados: list[ResultadoBusca] = []
        if not self.busca:
            pesquisa.erro = "Busca na internet não configurada (defina TAVILY_API_KEY)."
        else:
            respostas = await asyncio.gather(*(self.busca.buscar(c) for c in pesquisa.consultas), return_exceptions=True)
            for r in respostas:
                if isinstance(r, list):
                    resultados += r
                elif isinstance(r, BuscaIndisponivelError):
                    pesquisa.erro = f"Busca na internet indisponível: {r}"
                elif isinstance(r, Exception):
                    pesquisa.erro = f"Busca na internet falhou ({type(r).__name__})."

        # 3-5. Recortar, extrair e validar
        if resultados and preco > 0:
            trechos = recortar_trechos(resultados, preco)
            if trechos:
                await self._extrair(negocio, trechos, pesquisa, preco)
            else:
                pesquisa.erro = pesquisa.erro or "As páginas encontradas não traziam preços comparáveis."

        if tarefa_mapa:
            lojas, erro_mapa = await tarefa_mapa
            pesquisa.lojas_regiao = LojasRegiao(
                quantidade=lojas.quantidade if lojas else None,
                raio_metros=settings.mapa_raio_metros,
                categoria=plano.categoria_mapa,
                nivel_concorrencia=mapa.nivel_concorrencia(lojas.quantidade if lojas else None, lojas.parcial if lojas else False),
                # Na contagem parcial (busca por nome) os nomes podem ser de outro ramo: melhor não mostrar
                nomes=lojas.nomes if lojas and not lojas.parcial else [],
                fonte=lojas.fonte if lojas else "",
                erro=erro_mapa,
            )
            if lojas and lojas.parcial:
                pesquisa.lojas_regiao.observacao = (
                    "Contagem parcial: o serviço principal do mapa estava indisponível e a busca por nome encontra "
                    "bem menos lojas que o real. Não use este número para medir a concorrência."
                )
        return pesquisa

    async def _extrair(self, negocio: dict, trechos: list[dict], pesquisa: PesquisaMercado, preco: float) -> None:
        texto_trechos = "\n".join(f"[{t['id']}] ({t['titulo'][:60]}) {t['texto']}" for t in trechos)
        pedido = (
            f"Oferta a comparar: {negocio.get('produto')} ({negocio.get('tipo')}), {negocio.get('localizacao')}, "
            f"preço R$ {preco:.2f}.\n\nTrechos de páginas da internet:\n{texto_trechos}"
        )
        try:
            extracao = await self.ia_extracao.gerar(SISTEMA_EXTRACAO, [{"role": "user", "content": pedido}], ExtracaoMercado)
        except Exception as erro:  # noqa: BLE001
            log.exception("Pesquisador: extração falhou")
            pesquisa.erro = f"Não foi possível ler os preços encontrados ({type(erro).__name__})."
            return
        exemplos = validar_exemplos(extracao.exemplos, trechos)
        if not exemplos:
            pesquisa.erro = pesquisa.erro or "Nenhum preço comparável foi confirmado nas páginas encontradas."
            return
        pesquisa.faixas = calcular_faixas(exemplos)
        pesquisa.total_precos = len(exemplos)
        precos = [e.preco for e in exemplos]
        pesquisa.media_geral = round(mean(precos), 2)
        pesquisa.desvio_padrao_geral = round(pstdev(precos), 2) if len(precos) >= 2 else None
        pesquisa.posicao = posicionar(preco, exemplos, pesquisa.faixas)
        usadas = {e.fonte_url for e in exemplos}
        pesquisa.fontes = [Fonte(titulo=t["titulo"] or t["url"], url=t["url"])
                           for t in {t["url"]: t for t in trechos if t["url"] in usadas}.values()]
