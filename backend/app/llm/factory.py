"""Monta o provedor de LLM a partir do .env.

Sem argumentos, `criar_provider()` devolve a cadeia completa:
    principal (LLM_PROVIDER) → reserva (LLM_FALLBACK_PROVIDER) → mock (LLM_MOCK_NO_FIM)
Passando `provider=...`, devolve só aquele provedor (útil para testar um isoladamente).
"""

from typing import Literal

from app.config import settings
from app.llm.base import LLMProvider

PROVEDORES = ("mock", "groq", "gemini", "ollama")
Papel = Literal["personas", "analista"]


class ConfiguracaoLLMError(Exception):
    """Falta alguma variável no .env para o provedor escolhido."""


def _exigir(valor: str, variavel: str, dica: str) -> str:
    if not valor:
        raise ConfiguracaoLLMError(f"Defina {variavel} no arquivo .env. {dica}")
    return valor


def criar_provider_unico(nome: str, modelo: str, variavel_modelo: str = "LLM_MODEL_PERSONAS") -> LLMProvider:
    """Cria um único provedor, sem reserva."""
    nome = nome.lower()

    if nome == "mock":
        from app.llm.mock import MockProvider

        return MockProvider()

    if nome == "groq":
        from app.llm.openai_compat import GROQ_BASE_URL, OpenAICompatProvider

        chave = _exigir(settings.groq_api_key, "GROQ_API_KEY", "Gere em https://console.groq.com/keys")
        modelo = _exigir(modelo, variavel_modelo, "Veja os modelos em https://console.groq.com/docs/models")
        return OpenAICompatProvider("groq", GROQ_BASE_URL, chave, modelo)

    if nome == "ollama":
        from app.llm.openai_compat import OpenAICompatProvider

        modelo = _exigir(modelo, variavel_modelo, "Use o nome do modelo baixado com `ollama pull`")
        return OpenAICompatProvider("ollama", settings.ollama_base_url, "ollama", modelo)

    if nome == "gemini":
        from app.llm.gemini import GeminiProvider

        chave = _exigir(settings.gemini_api_key, "GEMINI_API_KEY", "Gere em https://aistudio.google.com/apikey")
        modelo = _exigir(modelo, variavel_modelo, "Veja os modelos em https://ai.google.dev/gemini-api/docs/models")
        return GeminiProvider(chave, modelo)

    raise ConfiguracaoLLMError(f"Provedor inválido: '{nome}'. Use um de: {', '.join(PROVEDORES)}")


def criar_provider(
    provider: str | None = None,
    modelo: str | None = None,
    papel: Papel = "personas",
    mock_no_fim: bool | None = None,
) -> LLMProvider:
    """Cria o provedor para um papel (personas ou analista).

    - Sem `provider`: cadeia do .env (principal → reserva → mock).
    - Com `provider`: só aquele provedor, sem reserva.
    - `mock_no_fim=False`: não termina a cadeia no mock (o analista usa isso: um
      relatório gravado de outro negócio seria enganoso).
    """
    usar_mock = settings.llm_mock_no_fim if mock_no_fim is None else mock_no_fim
    if provider:
        return criar_provider_unico(provider, modelo or _modelo_principal(papel), _var_principal(papel))

    from app.llm.fallback import FallbackProvider
    from app.llm.mock import MockProvider

    principal = criar_provider_unico(settings.llm_provider, modelo or _modelo_principal(papel), _var_principal(papel))
    cadeia: list[LLMProvider] = [principal]

    if settings.llm_fallback_provider and settings.llm_fallback_provider != settings.llm_provider:
        modelo_reserva = (
            settings.llm_fallback_model_analista if papel == "analista" else settings.llm_fallback_model_personas
        )
        variavel = "LLM_FALLBACK_MODEL_ANALISTA" if papel == "analista" else "LLM_FALLBACK_MODEL_PERSONAS"
        cadeia.append(criar_provider_unico(settings.llm_fallback_provider, modelo_reserva, variavel))

    if usar_mock and principal.nome != "mock":
        cadeia.append(MockProvider())

    return cadeia[0] if len(cadeia) == 1 else FallbackProvider(cadeia)


def _modelo_principal(papel: Papel) -> str:
    return settings.llm_model_analista if papel == "analista" else settings.llm_model_personas


def _var_principal(papel: Papel) -> str:
    return "LLM_MODEL_ANALISTA" if papel == "analista" else "LLM_MODEL_PERSONAS"
