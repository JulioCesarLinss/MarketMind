"""Configuração lida do arquivo .env na raiz do repositório."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ_REPO = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ_REPO / ".env")


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    llm_model_personas: str = os.getenv("LLM_MODEL_PERSONAS", "").strip()
    llm_model_analista: str = os.getenv("LLM_MODEL_ANALISTA", "").strip()
    groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip()


settings = Settings()
