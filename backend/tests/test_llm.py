"""Testes da camada de LLM que não precisam de chave nem internet."""

import asyncio

import pytest

from app.llm.base import LLMProvider, RespostaInvalidaError, extrair_json
from app.llm.factory import ConfiguracaoLLMError, criar_provider
from app.llm.fallback import FallbackProvider, TodosProvedoresFalharamError
from app.llm.mock import MockProvider
from app.models.schemas import Opiniao


class ProviderFalso(LLMProvider):
    """Devolve respostas pré-definidas, uma por chamada."""

    nome = "falso"

    def __init__(self, respostas: list[str]):
        super().__init__(modelo="falso")
        self.respostas = list(respostas)
        self.chamadas = 0

    async def _completar(self, sistema, mensagens):
        self.chamadas += 1
        return self.respostas.pop(0)


VALIDA = '{"fala": "ok", "interesse": 7, "compraria": "sim"}'


def test_mock_devolve_opiniao_valida():
    opiniao = asyncio.run(MockProvider(atraso_segundos=0).gerar("s", [], Opiniao))
    assert 0 <= opiniao.interesse <= 10


def test_remove_cerca_de_codigo():
    assert extrair_json("```json\n{\"a\": 1}\n```") == '{"a": 1}'


def test_tenta_de_novo_quando_json_invalido():
    provider = ProviderFalso(["isso não é json", VALIDA])
    opiniao = asyncio.run(provider.gerar("s", [], Opiniao))
    assert opiniao.interesse == 7 and provider.chamadas == 2


def test_falha_apos_esgotar_tentativas():
    provider = ProviderFalso(['{"interesse": 99}', '{"interesse": 99}'])
    with pytest.raises(RespostaInvalidaError):
        asyncio.run(provider.gerar("s", [], Opiniao))


def test_provedor_invalido():
    with pytest.raises(ConfiguracaoLLMError):
        criar_provider("inexistente")


class ProviderQueFalha(LLMProvider):
    nome = "quebrado"

    def __init__(self):
        super().__init__(modelo="x")

    async def _completar(self, sistema, mensagens):
        raise ConnectionError("servidor fora do ar")


def test_reserva_assume_quando_principal_falha():
    cadeia = FallbackProvider([ProviderQueFalha(), ProviderFalso([VALIDA])])
    opiniao, origem = asyncio.run(cadeia.gerar_com_origem("s", [], Opiniao))
    assert opiniao.interesse == 7
    assert origem == "falso/falso"


def test_principal_responde_sem_chamar_reserva():
    reserva = ProviderFalso([VALIDA])
    cadeia = FallbackProvider([ProviderFalso([VALIDA]), reserva])
    asyncio.run(cadeia.gerar("s", [], Opiniao))
    assert reserva.chamadas == 0


def test_mock_no_fim_da_cadeia():
    cadeia = FallbackProvider([ProviderQueFalha(), ProviderQueFalha(), MockProvider(atraso_segundos=0)])
    _, origem = asyncio.run(cadeia.gerar_com_origem("s", [], Opiniao))
    assert origem.startswith("mock")


def test_erro_quando_todos_falham():
    with pytest.raises(TodosProvedoresFalharamError):
        asyncio.run(FallbackProvider([ProviderQueFalha(), ProviderQueFalha()]).gerar("s", [], Opiniao))
