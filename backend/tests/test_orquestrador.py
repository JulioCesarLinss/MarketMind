"""Testes do orquestrador do debate (sem chave nem internet)."""

import asyncio

from app.agents.exemplos import NEGOCIO_EXEMPLO
from app.agents.personas import PADRAO_AGENTES, PERSONAS
from app.llm.base import LLMProvider
from app.services.orquestrador import Orquestrador


class ProviderEspiao(LLMProvider):
    """Responde sempre a mesma opinião e guarda tudo o que recebeu."""

    nome = "espiao"

    def __init__(self):
        super().__init__(modelo="teste")
        self.recebidos: list[tuple[str, list[dict]]] = []

    async def _completar(self, sistema, mensagens):
        self.recebidos.append((sistema, [dict(m) for m in mensagens]))
        self.tokens_usados += 100
        return '{"fala": "Achei caro.", "interesse": 4, "compraria": "talvez"}'


def simular():
    provider = ProviderEspiao()
    publicadas = []

    async def ao_publicar(m):
        publicadas.append(m)

    resultado = asyncio.run(Orquestrador(provider, ao_publicar=ao_publicar).executar(NEGOCIO_EXEMPLO))
    return provider, resultado, publicadas


def test_duas_rodadas_com_todas_as_personas():
    _, resultado, _ = simular()
    assert len(resultado.da_rodada(1)) == PADRAO_AGENTES
    assert len(resultado.da_rodada(2)) == PADRAO_AGENTES


def test_cada_fala_e_publicada_no_feed():
    _, resultado, publicadas = simular()
    assert len(publicadas) == len(resultado.mensagens)


def test_rodada_2_ve_os_outros_mas_nao_a_si_mesma():
    provider, _, _ = simular()
    economico = PERSONAS["economico"]
    # Chamadas da rodada 2 são as que têm histórico (pedido r1, resposta r1, pedido r2)
    chamadas_r2 = [(s, msgs) for s, msgs in provider.recebidos if len(msgs) == 3]
    sistema, msgs = next((s, m) for s, m in chamadas_r2 if economico.nome in s)
    pedido_r2 = msgs[-1]["content"]
    assert "RODADA 2" in pedido_r2
    assert PERSONAS["exigente"].nome in pedido_r2
    assert f"- {economico.nome}" not in pedido_r2


def test_persona_lembra_da_propria_resposta_da_rodada_1():
    provider, _, _ = simular()
    _, msgs = next((s, m) for s, m in provider.recebidos if len(m) == 3)
    assert msgs[0]["role"] == "user" and "RODADA 1" in msgs[0]["content"]
    assert msgs[1]["role"] == "assistant" and "Achei caro" in msgs[1]["content"]


def test_criterio_objetivo_de_mudanca():
    from app.models.schemas import Opiniao, mudou_de_posicao

    antes = Opiniao(fala="x", interesse=4, compraria="talvez")
    assert mudou_de_posicao(antes, Opiniao(fala="x", interesse=3, compraria="nao"))  # decisão mudou
    assert mudou_de_posicao(antes, Opiniao(fala="x", interesse=6, compraria="talvez"))  # nota +2
    assert not mudou_de_posicao(antes, Opiniao(fala="x", interesse=5, compraria="talvez", mudou_de_opiniao=True))


def test_conta_tokens():
    _, resultado, _ = simular()
    assert resultado.tokens_usados == 100 * 2 * PADRAO_AGENTES
