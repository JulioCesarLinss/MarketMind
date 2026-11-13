"""Testes do orquestrador: consumidores e especialistas opinam sozinhos, sem conversar (sem chave nem internet)."""

import asyncio

from app.agents.especialistas import ESPECIALISTAS, escolher_especialistas
from app.agents.exemplos import NEGOCIO_EXEMPLO
from app.agents.personas import PERSONAS
from app.llm.base import LLMProvider
from app.services.orquestrador import Orquestrador

PARECER = ('{"resumo": "Bom.", "nota": 7, "veredito": "favoravel", "pontos_fortes": ["a"], "riscos": ["b"], '
           '"recomendacoes": ["c"], "avaliacao_preco": "adequado", "preco_sugerido": null}')


class ProviderEspiao(LLMProvider):
    """Responde opinião ou parecer (conforme o prompt) e guarda tudo o que recebeu."""

    def __init__(self, nome="espiao", falhar=False):
        super().__init__(modelo="teste")
        self.nome = nome
        self.falhar = falhar
        self.recebidos: list[tuple[str, list[dict]]] = []

    async def _completar(self, sistema, mensagens):
        if self.falhar:
            raise RuntimeError("fora do ar")
        self.recebidos.append((sistema, [dict(m) for m in mensagens]))
        self.tokens_usados += 100
        if "consultor de pequenos negócios" in sistema:
            return PARECER
        return '{"fala": "Achei caro.", "interesse": 4, "compraria": "talvez"}'


def simular(especialistas=None, provider_esp=None):
    provider = ProviderEspiao()
    publicadas, pareceres = [], []

    async def ao_publicar(m):
        publicadas.append(m)

    async def ao_publicar_parecer(p):
        pareceres.append(p)

    resultado = asyncio.run(Orquestrador(
        provider, ao_publicar=ao_publicar, especialistas=especialistas,
        provider_especialistas=provider_esp, ao_publicar_parecer=ao_publicar_parecer,
    ).executar(NEGOCIO_EXEMPLO))
    return provider, resultado, publicadas, pareceres


def test_uma_rodada_so_sem_debate():
    provider, resultado, _, _ = simular()
    assert resultado.rodadas == 1
    assert len(resultado.da_rodada(1)) == len(PERSONAS) and resultado.da_rodada(2) == []
    # cada persona recebeu UMA mensagem, sem o que os outros disseram
    assert all(len(msgs) == 1 for _, msgs in provider.recebidos)
    assert not any("RODADA 2" in msgs[0]["content"] for _, msgs in provider.recebidos)


def test_cada_fala_e_publicada_no_feed():
    _, resultado, publicadas, _ = simular()
    assert len(publicadas) == len(resultado.mensagens)


def test_especialistas_no_proprio_provedor():
    gemini = ProviderEspiao(nome="gemini")
    groq, resultado, _, pareceres = simular(escolher_especialistas(), gemini)
    assert len(resultado.pareceres) == len(ESPECIALISTAS) == len(pareceres) == 6
    assert len(gemini.recebidos) == 6                     # especialistas foram para o "Gemini"
    assert len(groq.recebidos) == len(PERSONAS)           # consumidores ficaram no "Groq"
    assert resultado.tokens_usados == 100 * (6 + len(PERSONAS))  # soma os dois provedores
    # o especialista não vê a opinião de ninguém
    assert all("Você não conhece a opinião de mais ninguém" in m[0]["content"] for _, m in gemini.recebidos)


def test_especialista_que_falha_fica_de_fora_sem_derrubar():
    _, resultado, _, _ = simular(escolher_especialistas(["precificacao"]), ProviderEspiao(falhar=True))
    assert resultado.pareceres == [] and len(resultado.mensagens) == len(PERSONAS)


def test_so_especialistas():
    provider = ProviderEspiao()
    resultado = asyncio.run(Orquestrador(provider, personas=[], especialistas=escolher_especialistas(["marketing", "mercado"]))
                            .executar(NEGOCIO_EXEMPLO))
    assert resultado.mensagens == [] and [p.especialista_id for p in resultado.pareceres] == ["marketing", "mercado"]


def test_criterio_objetivo_de_mudanca():
    from app.models.schemas import Opiniao, mudou_de_posicao

    antes = Opiniao(fala="x", interesse=4, compraria="talvez")
    assert mudou_de_posicao(antes, Opiniao(fala="x", interesse=3, compraria="nao"))  # decisão mudou
    assert mudou_de_posicao(antes, Opiniao(fala="x", interesse=6, compraria="talvez"))  # nota +2
    assert not mudou_de_posicao(antes, Opiniao(fala="x", interesse=5, compraria="talvez", mudou_de_opiniao=True))


def test_conta_tokens():
    _, resultado, _, _ = simular()
    assert resultado.tokens_usados == 100 * len(PERSONAS)
