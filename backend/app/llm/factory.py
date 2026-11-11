"""Escolhe o provedor de LLM a partir do .env (LLM_PROVIDER)."""

from app.config import settings
from app.llm.base import LLMProvider

PROVEDORES = ("mock", "groq", "gemini", "ollama")


class ConfiguracaoLLMError(Exception):
    """Falta alguma variável no .env para o provedor escolhido."""


def _exigir(valor: str, variavel: str, dica: str) -> str:
    if not valor:
        raise ConfiguracaoLLMError(f"Defina {variavel} no arquivo .env. {dica}")
    return valor


def criar_provider(provider: str | None = None, modelo: str | None = None) -> LLMProvider:
    """Cria o provedor. Sem argumentos, usa LLM_PROVIDER e LLM_MODEL_PERSONAS do .env."""
    nome = (provider or settings.llm_provider).lower()
    modelo = modelo or settings.llm_model_personas

    if nome == "mock":
        from app.llm.mock import MockProvider

        return MockProvider()

    if nome == "groq":
        from app.llm.openai_compat import GROQ_BASE_URL, OpenAICompatProvider

        chave = _exigir(settings.groq_api_key, "GROQ_API_KEY", "Gere em https://console.groq.com/keys")
        modelo = _exigir(modelo, "LLM_MODEL_PERSONAS", "Veja os modelos em https://console.groq.com/docs/models")
        return OpenAICompatProvider("groq", GROQ_BASE_URL, chave, modelo)

    if nome == "ollama":
        from app.llm.openai_compat import OpenAICompatProvider

        modelo = _exigir(modelo, "LLM_MODEL_PERSONAS", "Use o nome do modelo baixado com `ollama pull`")
        return OpenAICompatProvider("ollama", settings.ollama_base_url, "ollama", modelo)

    if nome == "gemini":
        from app.llm.gemini import GeminiProvider

        chave = _exigir(settings.gemini_api_key, "GEMINI_API_KEY", "Gere em https://aistudio.google.com/apikey")
        modelo = _exigir(
            modelo, "LLM_MODEL_PERSONAS", "Veja os modelos em https://ai.google.dev/gemini-api/docs/models"
        )
        return GeminiProvider(chave, modelo)

    raise ConfiguracaoLLMError(f"LLM_PROVIDER inválido: '{nome}'. Use um de: {', '.join(PROVEDORES)}")
