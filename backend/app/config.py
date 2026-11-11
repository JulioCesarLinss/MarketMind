"""Configuração lida do arquivo .env na raiz do repositório."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ_REPO = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ_REPO / ".env")


def _env(nome: str, padrao: str = "") -> str:
    return os.getenv(nome, padrao).strip()


@dataclass(frozen=True)
class Settings:
    # Provedor principal
    llm_provider: str = _env("LLM_PROVIDER", "mock").lower()
    llm_model_personas: str = _env("LLM_MODEL_PERSONAS")
    llm_model_analista: str = _env("LLM_MODEL_ANALISTA")

    # Provedor de reserva (vazio = sem reserva)
    llm_fallback_provider: str = _env("LLM_FALLBACK_PROVIDER").lower()
    llm_fallback_model_personas: str = _env("LLM_FALLBACK_MODEL_PERSONAS")
    llm_fallback_model_analista: str = _env("LLM_FALLBACK_MODEL_ANALISTA")
    # Se tudo falhar, usa as respostas gravadas (demo_data) em vez de dar erro
    llm_mock_no_fim: bool = _env("LLM_MOCK_NO_FIM", "true").lower() in ("1", "true", "sim")

    # Chaves
    groq_api_key: str = _env("GROQ_API_KEY")
    gemini_api_key: str = _env("GEMINI_API_KEY")
    ollama_base_url: str = _env("OLLAMA_BASE_URL", "http://localhost:11434/v1")


settings = Settings()
