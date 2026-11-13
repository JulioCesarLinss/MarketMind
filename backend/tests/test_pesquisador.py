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
    # Com menos de 3 preços, vale a faixa que a IA deu
    faixas = {f.faixa: f for f in calcular_faixas([_ex("popular", 30), _ex("premium", 100)])}
    assert faixas["popular"].media == 30 and faixas["popular"].desvio_padrao is None
    assert faixas["premium"].quantidade == 1 and not faixas["premium"].dados_suficientes
    assert faixas["intermediaria"].quantidade == 0 and faixas["intermediaria"].media is None
    # Com 3 ou mais, os terços de preço garantem as 3 faixas preenchidas
    faixas = {f.faixa: f for f in calcular_faixas([_ex("popular", 30, "A"), _ex("popular", 40, "B"), _ex("popular", 100, "C")])}
    assert [faixas[n].media for n in ("popular", "intermediaria", "premium")] == [30, 40, 100]


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
    assert busca.consultas[:3] == ["barbearia Recife preço corte e barba",
                                   "barbearia Recife barato popular preço corte e barba",
                                   "barbearia Recife premium preço corte e barba"]
    # Só 2 preços: faz as rodadas 2 e 3 (3 buscas novas cada); a página repetida não é lida de novo
    assert len(busca.consultas) == 9 and "tabela de preços" in busca.consultas[3]
    assert "Boa Viagem" in busca.consultas[6]  # a 3ª rodada usa o bairro
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
    assert len(busca.consultas) == 9  # 3 rodadas na 1ª vez; a segunda veio do cache


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


def test_segunda_rodada_soma_precos_de_paginas_novas(mapa_falso):
    class BuscaDuasPaginas(BuscaFalsa):
        async def buscar(self, consulta, max_resultados=5):
            self.consultas.append(consulta)
            if "tabela de preços" in consulta:
                return [ResultadoBusca("Outra", "https://outra.com", "Barbearia Popular corte e barba R$ 40,00")]
            return [ResultadoBusca("Página", "https://exemplo.com/precos", PAGINA)]

    class IADuasRodadas(IAFalsa):
        async def _completar(self, sistema, mensagens):
            if "extrai preços" in sistema and "Barbearia Popular" in mensagens[0]["content"]:
                import json
                return json.dumps({"exemplos": ["popular | Barbearia Popular | corte e barba | 40,00 | T1"]})
            return await super()._completar(sistema, mensagens)

    p = asyncio.run(Pesquisador(IADuasRodadas(), IADuasRodadas(), BuscaDuasPaginas()).executar(NEGOCIOS["barbearia"]))
    assert p.total_precos == 3
    assert all(f.quantidade == 1 for f in p.faixas)  # 3 preços → uma em cada faixa
    assert {f.url for f in p.fontes} == {"https://exemplo.com/precos", "https://outra.com"}


def test_precisa_mais_precos():
    poucos = [_ex("popular", 10 + i, f"Loja {i}") for i in range(11)]
    assert mod.precisa_mais_precos(poucos)
    muitos_poucas_lojas = [_ex("popular", 10 + i, f"Loja {i % 4}") for i in range(12)]
    assert mod.precisa_mais_precos(muitos_poucas_lojas)
    assert not mod.precisa_mais_precos([_ex("popular", 10 + i, f"Loja {i % 5}") for i in range(12)])


def test_para_de_buscar_quando_atinge_a_meta(mapa_falso):
    linhas = [f"popular | Loja {i % 5} | corte {i} | {30 + i},00 | T1" for i in range(12)]
    pagina = " ".join(f"corte R$ {30 + i},00" for i in range(12))

    class BuscaCheia(BuscaFalsa):
        async def buscar(self, consulta, max_resultados=5):
            self.consultas.append(consulta)
            return [ResultadoBusca("Página", "https://cheia.com", pagina)]

    busca = BuscaCheia()
    p = asyncio.run(Pesquisador(IAFalsa(extracao=linhas), IAFalsa(extracao=linhas), busca).executar(NEGOCIOS["barbearia"]))
    assert p.total_precos == 12 and len(busca.consultas) == 3  # bateu a meta na 1ª rodada


def test_filtro_do_nominatim_fica_com_o_ramo_e_o_raio():
    lat, lon = -8.12, -34.90
    resultados = [
        {"osm_type": "node", "osm_id": 1, "name": "Barbearia A", "category": "shop", "type": "hairdresser", "lat": "-8.121", "lon": "-34.901"},
        {"osm_type": "node", "osm_id": 2, "name": "Rua da Barbearia", "category": "highway", "type": "residential", "lat": "-8.121", "lon": "-34.901"},
        {"osm_type": "node", "osm_id": 3, "name": "Barbearia Longe", "category": "shop", "type": "hairdresser", "lat": "-8.20", "lon": "-34.90"},
        {"osm_type": "node", "osm_id": 4, "name": "Padaria", "category": "shop", "type": "bakery", "lat": "-8.121", "lon": "-34.901"},
    ]
    aceitos = mapa.NOMINATIM_TIPOS["barbearia_salao"][1]
    assert mapa.filtrar_nominatim(resultados, lat, lon, 2000, aceitos, por_tipo=True) == {"node1": "Barbearia A"}
    assert mapa.filtrar_nominatim(resultados, lat, lon, 2000, aceitos, por_tipo=False) == {"node1": "Barbearia A"}


def test_toda_categoria_tem_regra_no_nominatim():
    assert set(mapa.NOMINATIM_TIPOS) == set(mapa.CATEGORIAS)
