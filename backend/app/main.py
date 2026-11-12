"""Aplicação FastAPI.

Rodar (dentro de backend/, com o ambiente virtual ativado):
    uvicorn app.main:app --reload
Documentação interativa: http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.simulacoes import router as router_simulacoes
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="MarketMind API",
    description="Simulador de mercado com múltiplos agentes de IA. As opiniões são sintéticas: hipóteses a validar.",
    version="0.1.0",
)

# Libera o frontend (Vite em localhost:5173 e a URL publicada) a chamar a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_urls,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_simulacoes)


@app.get("/health", tags=["status"])
def health():
    """Para o Render (e para você) saber se a API está de pé."""
    return {"status": "ok", "llm": settings.llm_provider}
