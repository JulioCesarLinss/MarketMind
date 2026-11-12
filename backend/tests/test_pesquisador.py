"""Testes do agente pesquisador e da contagem de lojas (sem internet nem chave)."""

import asyncio

import pytest

from app.agents import pesquisador as mod
from app.agents.contexto import formatar_negocio
from app.agents.exemplos import NEGOCIOS
from app.agents.pesquisador import (
    Pesquisador,
    calcular_faixas,
    posicionar,
    precos_no_texto,
    recortar_trechos,
    validar_exemplos,
)
from app.llm.base import LLMProvider
from app.models.pesquisa import ExemploMercado, PesquisaMercado
from app.services import mapa
from app.services.busca import BuscaIndisponivelError, BuscaWeb, ResultadoBusca

PAGINA = (
    "Barbearia Navalha: corte R$ 35,00 e barba R$ 25. Combo corte + barba R$ 55,00. "
    + "texto " * 80
    + "Studio Premium: corte + barba com toalha quente R$ 95,00 · taxa de agendamento R$ 1,00"
)


def _ex(faixa, preco, nome="Loja"):
    return ExemploMercado(faixa=faixa, estabelecimento=nome, item="corte + barba", preco=preco, fonte_url="u")


# ---------- Funções puras ----------

def test_le_precos_em_reais():
    assert precos_no_texto("R$ 32,90 · R$45 · R$ 1.234,56") == [32.9, 45.0, 1234.56]


def test_recorta_trechos_e_ignora_precos_fora_da_escala():
    trechos = recortar_trechos([ResultadoBusca("Página", "https://x.com", PAGINA)], preco_usuario=85)
    texto = " ".join(t["texto"] for t in trechos)
    assert "R$ 55,00" in texto and "R$ 95,00" in texto
    assert all(t["id"].startswith("T") for t in trechos)
    # R$ 1,00 (taxa) fica fora da escala e não gera trecho próprio
    assert len(trechos) == 2


def test_validacao_descarta_preco_que_nao_esta_no_trecho():
    trechos = [{"id": "T1", "url": "https://x.com", "titulo": "", "texto": "Combo corte + barba R$ 55,00"}]
    linhas = [
        "intermediaria | Navalha | corte + barba | 55,00 | T1",   # ok
        "premium | Inventada | corte + barba | 120,00 | T1",      # preço não está no trecho
        "popular | Navalha | corte | 55 | T9",                    # trecho inexistente
        "luxo | Navalha | corte | 55 | T1",                       # faixa inválida
        "linha sem o formato certo",
        "intermediaria | Navalha | corte + barba | 55,00 | T1",   # repetida
        "intermediária | Navalha | combo | R$ 55,00 | [T1]",      # acento, R$ e colchetes: aceito
    ]
    validos = validar_exemplos(linhas, trechos)
    assert [(e.estabelecimento, e.item, e.preco, e.faixa) for e in validos] == [
        ("Navalha", "corte + barba", 55.0, "intermediaria"),
        ("Navalha", "combo", 55.0, "intermediaria"),
    ]


def test_media_desvio_e_dados_insuficientes():
    faixas = {f.faixa: f for f in calcular_faixas([_ex("popular", 30), _ex("popular", 40), _ex("premium", 100)])}
    assert faixas["popular"].media == 35 and faixas["popular"].desvio_padrao == 5.0
    assert faixas["popular"].dados_suficientes
    assert faixas["premium"].quantidade == 1 and not faixas["premium"].dados_suficientes
    assert faixas["premium"].desvio_padrao is None
    assert faixas["intermediaria"].quantidade == 0 and faixas["intermediaria"].media is None


def test_posicao_do_preco():
    exemplos = [_ex("popular", 30), _ex("popular", 40), _ex("premium", 90), _ex("premium", 100)]
    pos = posicionar(85, exemplos, calcular_faixas(exemplos))
    assert pos.media_mercado == 65 and pos.faixa_mais_proxima == "premium"
    assert pos.desvios_da_media == round((85 - 65) / pos.desvio_padrao_mercado, 2)
    assert "acima" in pos.resumo


@pytest.mark.parametrize("qtd,nivel", [(None, "indeterminado"), (0, "nenhum concorrente mapeado"),
                                       (2, "baixa"), (7, "media"), (25, "alta")])
def test_nivel_de_concorrencia(qtd, nivel):
    assert mapa.nivel_concorrencia(qtd) == nivel


def test_consulta_overpass_usa_lista_fechada_e_palavras():
    q = mapa.montar_consulta_overpass(-8.1, -34.9, "barbearia_salao", ["barbear", 'x"]; drop'], 2000)
    assert '["shop"~"^(hairdresser|barber)$"]' in q and "around:2000,-8.1,-34.9" in q
    assert '"name"~"barbear|x drop",i' in q  # caracteres perigosos removidos


# ---------- Agente completo com dublês ----------

class IAFalsa(LLMProvider):
    """Responde o plano e a extração, conforme o schema pedido."""

    nome = "falsa"

    def __init__(self, extracao=None, falhar=False):
        super().__init__(modelo="x")
        self.extracao = extracao or ["intermediaria | Navalha | corte + barba | 55,00 | T1",
                                     "premium | Studio Premium | corte + barba | 95,00 | T2"]
        self.falhar = falhar

    async def _completar(self, sistema, mensagens):
        if self.falhar:
            raise RuntimeError("fora do ar")
        self.tokens_usados += 10
        if "extrai preços" in sistema:
            import json
            return json.dumps({"exemplos": self.extracao})
        return ('{"tipo_estabelecimento": "barbearia", "produto_comparavel": "corte e barba", "cidade": "Recife", '
                '"categoria_mapa": "barbearia_salao", "palavras_nome": ["barbearia"]}')


class BuscaFalsa(BuscaWeb):
    nome = "falsa"

    def __init__(self, falhar=False):
        self.falhar = falhar
        self.consultas = []

    async def buscar(self, consulta, max_resultados=5):
        self.consultas.append(consulta)
        if self.falhar:
            raise BuscaIndisponivelError("sem créditos")
        return [ResultadoBusca("Página", "https://exemplo.com/precos", PAGINA)]


@pytest.fixture
def mapa_falso(monkeypatch):
    async def contar(localizacao, categoria, palavras, raio):
        return mapa.LojasEncontradas(5, ["A", "B"], "teste"), None
    monkeypatch.setattr(mod.mapa, "contar_lojas", contar)


def test_pesquisa_completa(mapa_falso):
    busca = BuscaFalsa()
    p = asyncio.run(Pesquisador(IAFalsa(), IAFalsa(), busca).executar(NEGOCIOS["barbearia"]))
    assert busca.consultas == ["barbearia Recife preço corte e barba",
                               "barbearia Recife barato popular preço corte e barba",
                               "barbearia Recife premium preço corte e barba"]
    assert p.total_precos == 2 and p.erro is None
    assert p.posicao.faixa_mais_proxima == "premium"
    assert p.lojas_regiao.quantidade == 5 and p.lojas_regiao.nivel_concorrencia == "media"
    assert p.fontes[0].url == "https://exemplo.com/precos"
    assert p.tokens_usados > 0
    # e entra no contexto das personas
    texto = formatar_negocio(NEGOCIOS["barbearia"], p)
    assert "Referência de mercado" in texto and "pelo menos 5" in texto


def test_busca_fora_do_ar_ainda_conta_lojas(mapa_falso):
    p = asyncio.run(Pesquisador(IAFalsa(), IAFalsa(), BuscaFalsa(falhar=True)).executar(NEGOCIOS["barbearia"]))
    assert p.total_precos == 0 and "indisponível" in p.erro
    assert p.lojas_regiao.quantidade == 5 and p.tem_dados()


def test_sem_busca_configurada(mapa_falso):
    p = asyncio.run(Pesquisador(IAFalsa(), IAFalsa(), None).executar(NEGOCIOS["barbearia"]))
    assert "TAVILY_API_KEY" in p.erro


def test_ia_fora_do_ar_nao_derruba(mapa_falso):
    p = asyncio.run(Pesquisador(IAFalsa(falhar=True), IAFalsa(), BuscaFalsa()).executar(NEGOCIOS["barbearia"]))
    assert not p.tem_dados() and p.erro
    # sem dados úteis, a pesquisa nem entra no contexto das personas
    assert "Referência de mercado" not in formatar_negocio(NEGOCIOS["barbearia"], p)


def test_cache_evita_nova_busca(mapa_falso):
    busca = BuscaFalsa()
    pesquisador = Pesquisador(IAFalsa(), IAFalsa(), busca)
    asyncio.run(pesquisador.executar(NEGOCIOS["barbearia"]))
    asyncio.run(pesquisador.executar(NEGOCIOS["barbearia"]))
    assert len(busca.consultas) == 3  # a segunda veio do cache


def test_demo_data_e_valido():
    from app.services.simulacoes import DEMO_PESQUISA
    p = PesquisaMercado.model_validate_json(DEMO_PESQUISA.read_text(encoding="utf-8"))
    assert p.tem_dados() and "DEMONSTRAÇÃO" in p.aviso


def test_contagem_parcial_nao_mede_concorrencia(monkeypatch):
    async def contar(localizacao, categoria, palavras, raio):
        return mapa.LojasEncontradas(2, ["A", "B"], "Nominatim", parcial=True), None
    monkeypatch.setattr(mod.mapa, "contar_lojas", contar)
    p = asyncio.run(Pesquisador(IAFalsa(), IAFalsa(), BuscaFalsa()).executar(NEGOCIOS["barbearia"]))
    assert p.lojas_regiao.nivel_concorrencia == "indeterminado"
    assert "parcial" in p.lojas_regiao.observacao.lower()
    assert "contagem incompleta" in formatar_negocio(NEGOCIOS["barbearia"], p)


def test_faixas_por_tercos_de_preco_com_6_ou_mais():
    exemplos = [_ex("intermediaria", p, f"Loja {p}") for p in (10, 12, 20, 22, 40, 45)]
    faixas = {f.faixa: f for f in calcular_faixas(exemplos)}
    assert [e.preco for e in faixas["popular"].exemplos] == [10, 12]
    assert [e.preco for e in faixas["intermediaria"].exemplos] == [20, 22]
    assert [e.preco for e in faixas["premium"].exemplos] == [40, 45]


def test_limite_de_precos_por_loja():
    trechos = [{"id": "T1", "url": "u", "titulo": "", "texto": "R$ 10 R$ 11 R$ 12 R$ 13"}]
    linhas = [f"popular | Mesma Loja | item {p} | {p} | T1" for p in (10, 11, 12, 13)]
    assert len(validar_exemplos(linhas, trechos)) == 3
