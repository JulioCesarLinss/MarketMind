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



# ---------- Avaliação do preço ----------

def _ind(pm, compraria="talvez"):
    from app.models.schemas import IndicadorPersona
    return IndicadorPersona(persona_id="x", persona_nome="x", interesse_r1=5, interesse_r2=5, compraria_r1=compraria,
                            compraria_r2=compraria, mudou=False, preco_maximo=pm)


def test_maioria_aceita_vira_preco_ideal():
    from app.agents.analista import avaliar_preco
    # caso do usuário: todos elogiaram, máximos 118, 119, 120... para um preço de 119
    aceitam, avaliacao, referencia, _ = avaliar_preco([_ind(118), _ind(118.5), _ind(119), _ind(120), _ind(116)], 119)
    assert aceitam == 5 and avaliacao == "ideal" and referencia == 119


def test_quem_compraria_aceita_mesmo_com_maximo_menor():
    from app.agents.analista import avaliar_preco
    aceitam, avaliacao, _, _ = avaliar_preco([_ind(100, "sim"), _ind(105, "sim"), _ind(80, "nao")], 119)
    assert aceitam == 2 and avaliacao == "ideal"


def test_espaco_para_subir_e_preco_acima_do_aceito():
    from app.agents.analista import avaliar_preco
    assert avaliar_preco([_ind(150), _ind(140), _ind(90)], 119)[1] == "espaco_para_subir"
    aceitam, avaliacao, referencia, _ = avaliar_preco([_ind(80), _ind(90), _ind(130)], 119)
    assert aceitam == 1 and avaliacao == "acima_do_aceito" and referencia == 90  # mediana do que pagariam
    assert avaliar_preco([_ind(None), _ind(None)], 119)[1] == "sem_dados"


def test_analista_nao_tem_amostra_gratis_como_padrao():
    from app.agents.analista import SISTEMA_ANALISTA
    assert "Amostra grátis, degustação e brinde NÃO são o padrão" in SISTEMA_ANALISTA
    assert "marmita" in SISTEMA_ANALISTA and "NÃO recomende baixar o preço" in SISTEMA_ANALISTA
