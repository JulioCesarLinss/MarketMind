"""Testes do agente analista (sem chave nem internet)."""

import asyncio

from app.agents.analista import analisar, calcular_indicadores, montar_pedido
from app.agents.exemplos import NEGOCIOS
from app.llm.base import LLMProvider
from app.llm.mock import MockProvider
from app.models.schemas import AnaliseDebate, MensagemDebate, Opiniao, ResultadoSimulacao


def _msg(pid, nome, rodada, interesse, compraria, preco=None, objecoes=()):
    return MensagemDebate(
        persona_id=pid, persona_nome=nome, rodada=rodada, origem="teste", duracao_segundos=0,
        opiniao=Opiniao(fala=f"fala {nome} r{rodada}", interesse=interesse, compraria=compraria,
                        preco_maximo=preco, objecoes=list(objecoes), o_que_mudaria="desconto de entrada"),
    )


def resultado_exemplo():
    return ResultadoSimulacao(
        mensagens=[
            _msg("economico", "Consumidor Econômico", 1, 3, "nao", 50, ["caro"]),
            _msg("exigente", "Consumidor Exigente", 1, 6, "talvez", 80),
            _msg("economico", "Consumidor Econômico", 2, 5, "talvez", 60, ["caro"]),
            _msg("exigente", "Consumidor Exigente", 2, 6, "talvez", None),
        ],
        rodadas=2, provedor_principal="teste", tokens_usados=0, duracao_segundos=0,
    )


def test_indicadores_calculados_pelo_codigo():
    ind = calcular_indicadores(resultado_exemplo(), 85.0)
    assert ind.interesse_medio_r1 == 4.5 and ind.interesse_medio_r2 == 5.5
    assert ind.decisoes_r2 == {"sim": 0, "talvez": 2, "nao": 0}
    assert ind.preco_maximo_medio == 60.0  # só quem respondeu na rodada 2
    assert ind.mudaram_de_posicao == 1  # Econômico: nao → talvez
    assert [p.mudou for p in ind.por_persona] == [True, False]


def test_pedido_tem_debate_e_numeros():
    r = resultado_exemplo()
    pedido = montar_pedido(NEGOCIOS["barbearia"], r, calcular_indicadores(r, 85.0))
    assert "Barbearia premium" in pedido
    assert "Consumidor Econômico — rodada 2" in pedido
    assert "Objeções: caro" in pedido and "Sugestão ao dono: desconto de entrada" in pedido
    assert "Interesse médio: 4.5 na rodada 1 → 5.5 na rodada 2" in pedido


def test_relatorio_com_mock():
    rel = asyncio.run(analisar(MockProvider(atraso_segundos=0), NEGOCIOS["barbearia"], resultado_exemplo()))
    assert isinstance(rel.analise, AnaliseDebate)
    assert rel.analise.recomendacoes
    assert rel.origem_analise == "mock/demo" and rel.erro_analise is None


class ProviderQuebrado(LLMProvider):
    nome = "quebrado"

    def __init__(self):
        super().__init__(modelo="x")

    async def _completar(self, sistema, mensagens):
        raise RuntimeError("fora do ar")


def test_falha_do_analista_mantem_os_numeros():
    rel = asyncio.run(analisar(ProviderQuebrado(), NEGOCIOS["barbearia"], resultado_exemplo()))
    assert rel.analise is None and "Não foi possível" in rel.erro_analise
    assert rel.indicadores.interesse_medio_r2 == 5.5


def test_analista_nao_configurado():
    rel = asyncio.run(analisar(None, NEGOCIOS["barbearia"], resultado_exemplo()))
    assert rel.analise is None and "LLM_MODEL_ANALISTA" in rel.erro_analise
