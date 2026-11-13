"""Agente pesquisador: monta uma referência de mercado ANTES do debate.

Etapas:
    1. IA planeja: tipo, produto e cidade (o código monta 3 buscas: geral, popular, premium) + categoria do mapa.
    2. Busca na internet (Tavily/Ollama) e, ao mesmo tempo, conta lojas no mapa (OpenStreetMap).
       Se vierem menos de 12 preços ou menos de 5 lojas, faz até 2 rodadas extras com outros termos (só páginas novas).
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
import unicodedata
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
MAX_TRECHOS_FONTE = 8
MAX_TRECHOS = 40        # por rodada: limita os tokens da extração (~3 mil; o limite do Groq grátis é por minuto)
RESULTADOS_POR_BUSCA = 8  # páginas por busca (no Tavily, custa o mesmo crédito que 5)
MAX_RODADAS = 3          # rodadas de busca: só passa para a próxima se ainda faltar preço
MAX_POR_LOJA = 3        # no máximo 3 preços por estabelecimento
MIN_PARA_TERCOS = 3     # a partir daqui, as faixas são definidas pelos terços de preço (1+ preço em cada faixa)
META_POR_FAIXA = 4      # objetivo: 4 preços por faixa (12 no total); abaixo disso, faz mais uma rodada de buscas
META_LOJAS = 5          # e pelo menos 5 estabelecimentos diferentes
FAIXA_VALIDA = (0.2, 5.0)  # descarta preços < 20% ou > 5x o preço do usuário (ex.: "R$ 1,00" de taxa)
CACHE_HORAS = 24

SISTEMA_PLANO = """Você ajuda a pesquisar preços de mercado para um pequeno negócio no Brasil.
A partir dos dados do negócio, identifique o tipo de estabelecimento concorrente, o produto ou serviço comparável
(como um cliente digitaria numa busca) e a cidade. Use termos simples e genéricos, sem adjetivos de posicionamento
(nada de "premium" ou "barato": as buscas por faixa são montadas depois)."""


def normalizar(texto: str) -> str:
    """'São Paulo' / 'sao-paulo' / 'SÃO PAULO' → 'sao paulo' (para comparar nomes de cidade e bairro)."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).split())


def extrair_bairro(localizacao: str, cidade: str) -> str:
    """'Boa Viagem, Recife - PE' → 'Boa Viagem'. Vazio se o usuário informou só a cidade."""
    primeiro = (localizacao or "").split(",")[0].split(" - ")[0].strip()
    return "" if not primeiro or normalizar(primeiro) == normalizar(cidade) else primeiro


def menciona(texto_normalizado: str, nome: str) -> bool:
    alvo = normalizar(nome)
    return bool(alvo) and f" {alvo} " in f" {texto_normalizado} "


def montar_consultas(plano: PlanoPesquisa, bairro: str = "") -> list[str]:
    """Três buscas no mesmo padrão (geral, popular, premium): previsível e sem repetição.
    A primeira inclui o bairro, para achar primeiro os negócios mais próximos."""
    base = " ".join(dict.fromkeys(f"{plano.tipo_estabelecimento} {plano.cidade}".split()))  # evita palavra repetida
    produto = plano.produto_comparavel.strip()
    perto = " ".join(dict.fromkeys(f"{plano.tipo_estabelecimento} {bairro} {plano.cidade}".split())) if bairro else base
    return [
        f"{perto} preço {produto}",
        f"{base} barato popular preço {produto}",
        f"{base} premium preço {produto}",
    ]


def montar_consultas_extras(plano: PlanoPesquisa, rodada: int = 2, localizacao: str = "") -> list[str]:
    """Rodadas 2 e 3 (só se as anteriores trouxeram poucos preços): termos diferentes para achar outras páginas."""
    produto = plano.produto_comparavel.strip()
    tipo, cidade = plano.tipo_estabelecimento, plano.cidade
    if rodada == 2:
        return [
            f"{tipo} {cidade} tabela de preços",
            f"quanto custa {produto} em {cidade}",
            f"melhores {tipo} {cidade} {produto} valor",
        ]
    bairro = extrair_bairro(localizacao, cidade)
    return [
        f"{tipo} {bairro} {cidade} preços" if bairro else f"{tipo} perto de mim {cidade} preços",
        f"{produto} {cidade} promoção preço",
        f"cardápio ou lista de serviços {tipo} {cidade} valores",
    ]

SISTEMA_EXTRACAO = """Você extrai preços de trechos de páginas da internet para comparar com uma oferta.
Regras:
- Liste apenas itens COMPARÁVEIS à oferta (mesmo tipo de produto ou serviço).
- Liste TODOS os estabelecimentos diferentes que aparecerem (até 3 preços por estabelecimento): queremos exemplos baratos, médios e caros.
- Use somente preços escritos nos trechos. Nunca invente, arredonde ou calcule preços.
- Classifique cada estabelecimento em uma faixa (popular, intermediaria, premium) pelo posicionamento e pelo preço.
- Ignore taxas, fretes, descontos isolados e itens de outro tipo.
- Considere SOMENTE estabelecimentos da cidade informada. Ignore os de outras cidades, mesmo que apareçam na mesma página."""


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


def filtrar_por_cidade(resultados: list[ResultadoBusca], cidade: str, bairro: str = "") -> list[ResultadoBusca]:
    """Fica só com páginas que citam a cidade do usuário (no título, no endereço ou no texto)
    e coloca primeiro as que citam o bairro: os trechos têm limite, então os mais próximos entram antes."""
    if not cidade:
        return resultados
    da_cidade = []
    for r in resultados:
        texto = normalizar(f"{r.titulo} {r.url} {r.conteudo}")
        if menciona(texto, cidade):
            da_cidade.append((not (bairro and menciona(texto, bairro)), r))
    return [r for _, r in sorted(da_cidade, key=lambda par: par[0])]


def recortar_trechos(resultados: list[ResultadoBusca], preco_usuario: float, ignorar_urls: set[str] | None = None) -> list[dict]:
    """Recorta janelas de texto ao redor de preços plausíveis. Devolve [{id, url, titulo, texto}]."""
    minimo, maximo = preco_usuario * FAIXA_VALIDA[0], preco_usuario * FAIXA_VALIDA[1]
    trechos: list[dict] = []
    urls_vistas = set(ignorar_urls or ())
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


def validar_exemplos(linhas: list[str], trechos: list[dict], anteriores: list[ExemploMercado] | None = None) -> list[ExemploMercado]:
    """Aceita só exemplos cujo preço está escrito no trecho citado (anti-invenção).
    `anteriores` = exemplos de uma rodada anterior (contam para o limite por loja e para repetição)."""
    por_id = {t["id"]: t for t in trechos}
    anteriores = anteriores or []
    validos: list[ExemploMercado] = []
    vistos = {(e.estabelecimento.lower(), e.item.lower(), e.preco) for e in anteriores}
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
        if sum(e.estabelecimento.lower() == estabelecimento.lower() for e in anteriores + validos) >= MAX_POR_LOJA:
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


def precisa_mais_precos(exemplos: list[ExemploMercado]) -> bool:
    lojas = {e.estabelecimento.lower() for e in exemplos}
    return len(exemplos) < 3 * META_POR_FAIXA or len(lojas) < META_LOJAS


def observar_regiao(pesquisa: PesquisaMercado, cidade: str, bairro: str, busca_funcionou: bool) -> str:
    """Observação em texto quando faltam concorrentes (ex.: possível negócio único na região).
    Só afirma algo quando a busca e o mapa funcionaram: falha técnica não é ausência de concorrente."""
    perto = f"perto de {bairro}" if bairro else f"em {cidade}"
    lojas = pesquisa.lojas_regiao.quantidade if pesquisa.lojas_regiao else None
    tem_precos = pesquisa.total_precos > 0
    if not tem_precos and busca_funcionou and lojas == 0:
        return (f"Não encontramos negócios parecidos em {cidade}: nenhum preço na internet e nenhuma loja do ramo "
                f"mapeada {perto}. Pode ser um negócio único na região (ou ainda pouco presente na internet e no mapa).")
    if not tem_precos and busca_funcionou and lojas is None:
        return (f"Nenhum negócio parecido com preço publicado foi encontrado na internet em {cidade}. "
                "Pode ser um negócio único na região (ou que divulga pouco os preços).")
    if not tem_precos and busca_funcionou and lojas:
        return (f"Há lojas do ramo {perto}, mas nenhuma com preço publicado na internet em {cidade}: "
                "a comparação de preço fica por conta dos concorrentes que você informar.")
    if tem_precos and lojas == 0:
        return (f"Nenhuma loja do ramo mapeada {perto}: na vizinhança pode ser um negócio único. "
                f"Os preços acima são de outras partes de {cidade}.")
    return ""


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
        bairro = extrair_bairro(str(negocio.get("localizacao", "")), plano.cidade)
        pesquisa.consultas = montar_consultas(plano, bairro)

        # 2. Buscar preços e contar lojas ao mesmo tempo
        tarefa_mapa = (
            asyncio.create_task(mapa.contar_lojas(str(negocio.get("localizacao", "")), plano.categoria_mapa,
                                                  plano.palavras_nome, settings.mapa_raio_metros))
            if self.usar_mapa else None
        )
        exemplos: list[ExemploMercado] = []
        trechos_usados: list[dict] = []
        if not self.busca:
            pesquisa.erro = "Busca na internet não configurada (defina TAVILY_API_KEY)."
        elif preco > 0:
            # 1ª rodada: geral, popular e premium
            exemplos, trechos_usados = await self._rodada_busca(negocio, plano, bairro, pesquisa, pesquisa.consultas,
                                                                preco, [], set())
            # Rodadas 2 e 3: só se ainda faltar preço (meta: 4 por faixa e 5 estabelecimentos diferentes)
            for rodada in range(2, MAX_RODADAS + 1):
                if not precisa_mais_precos(exemplos) or (pesquisa.erro or "").startswith("Busca na internet indisponível"):
                    break
                extras = montar_consultas_extras(plano, rodada, str(negocio.get("localizacao", "")))
                pesquisa.consultas += extras
                novos, trechos_novos = await self._rodada_busca(negocio, plano, bairro, pesquisa, extras, preco, exemplos,
                                                                 {t["url"] for t in trechos_usados})
                exemplos += novos
                trechos_usados += trechos_novos
            if exemplos:
                pesquisa.erro = None  # achou preços: falhas pontuais de uma busca não importam
                self._consolidar(pesquisa, exemplos, trechos_usados, preco)
            else:
                pesquisa.erro = pesquisa.erro or "Nenhum preço comparável foi confirmado nas páginas encontradas."

        if tarefa_mapa:
            lojas, erro_mapa = await tarefa_mapa
            pesquisa.lojas_regiao = LojasRegiao(
                quantidade=lojas.quantidade if lojas else None,
                raio_metros=settings.mapa_raio_metros,
                categoria=plano.categoria_mapa,
                nivel_concorrencia=mapa.nivel_concorrencia(lojas.quantidade if lojas else None, lojas.parcial if lojas else False),
                nomes=lojas.nomes if lojas and not lojas.parcial else [],
                fonte=lojas.fonte if lojas else "",
                erro=erro_mapa,
            )
            if lojas and lojas.parcial:
                pesquisa.lojas_regiao.observacao = (
                    "Contagem parcial: o serviço principal do mapa estava indisponível e a busca por nome encontra "
                    "bem menos lojas que o real. Não use este número para medir a concorrência."
                )
        busca_funcionou = bool(self.busca) and preco > 0 and not (pesquisa.erro or "").startswith(
            ("Busca na internet indisponível", "Busca na internet falhou", "Não foi possível"))
        pesquisa.observacao = observar_regiao(pesquisa, plano.cidade, bairro, busca_funcionou)
        return pesquisa

    async def _rodada_busca(self, negocio: dict, plano: PlanoPesquisa, bairro: str, pesquisa: PesquisaMercado,
                            consultas: list[str], preco: float, anteriores: list[ExemploMercado],
                            urls_vistas: set[str]) -> tuple[list[ExemploMercado], list[dict]]:
        """Busca as consultas em paralelo, recorta os trechos com preço e extrai/valida os exemplos."""
        resultados: list[ResultadoBusca] = []
        respostas = await asyncio.gather(*(self.busca.buscar(c, RESULTADOS_POR_BUSCA) for c in consultas),
                                         return_exceptions=True)
        for r in respostas:
            if isinstance(r, list):
                resultados += r
            elif isinstance(r, BuscaIndisponivelError):
                pesquisa.erro = f"Busca na internet indisponível: {r}"
            elif isinstance(r, Exception):
                pesquisa.erro = f"Busca na internet falhou ({type(r).__name__})."
        da_cidade = filtrar_por_cidade(resultados, plano.cidade, bairro)
        trechos = recortar_trechos(da_cidade, preco, urls_vistas) if da_cidade else []
        if not trechos:
            if resultados and not da_cidade:
                pesquisa.erro = pesquisa.erro or f"As páginas encontradas eram de outras cidades, não de {plano.cidade}."
            elif resultados:
                pesquisa.erro = pesquisa.erro or "As páginas encontradas não traziam preços comparáveis."
            return [], []
        return await self._extrair(negocio, plano.cidade, trechos, pesquisa, preco, anteriores), trechos

    async def _extrair(self, negocio: dict, cidade: str, trechos: list[dict], pesquisa: PesquisaMercado, preco: float,
                       anteriores: list[ExemploMercado] | None = None) -> list[ExemploMercado]:
        texto_trechos = "\n".join(f"[{t['id']}] ({t['titulo'][:60]}) {t['texto']}" for t in trechos)
        pedido = (
            f"Oferta a comparar: {negocio.get('produto')} ({negocio.get('tipo')}), {negocio.get('localizacao')}, "
            f"preço R$ {preco:.2f}.\nCidade: {cidade} — liste só estabelecimentos desta cidade."
            f"\n\nTrechos de páginas da internet:\n{texto_trechos}"
        )
        try:
            extracao = await self.ia_extracao.gerar(SISTEMA_EXTRACAO, [{"role": "user", "content": pedido}], ExtracaoMercado)
        except Exception as erro:  # noqa: BLE001
            log.exception("Pesquisador: extração falhou")
            pesquisa.erro = f"Não foi possível ler os preços encontrados ({type(erro).__name__})."
            return []
        return validar_exemplos(extracao.exemplos, trechos, anteriores)

    def _consolidar(self, pesquisa: PesquisaMercado, exemplos: list[ExemploMercado], trechos: list[dict], preco: float) -> None:
        pesquisa.faixas = calcular_faixas(exemplos)
        pesquisa.total_precos = len(exemplos)
        precos = [e.preco for e in exemplos]
        pesquisa.media_geral = round(mean(precos), 2)
        pesquisa.desvio_padrao_geral = round(pstdev(precos), 2) if len(precos) >= 2 else None
        pesquisa.posicao = posicionar(preco, exemplos, pesquisa.faixas)
        usadas = {e.fonte_url for e in exemplos}
        pesquisa.fontes = [Fonte(titulo=t["titulo"] or t["url"], url=t["url"])
                           for t in {t["url"]: t for t in trechos if t["url"] in usadas}.values()]
