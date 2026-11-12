"""Monta o serviço de busca a partir do .env (BUSCA_PROVIDER e BUSCA_RESERVA)."""

import logging

from app.config import settings
from app.services.busca.base import BuscaComReserva, BuscaWeb
from app.services.busca.servicos import OllamaBusca, TavilyBusca

log = logging.getLogger(__name__)


def _criar(nome: str) -> BuscaWeb | None:
    if nome == "tavily" and settings.tavily_api_key:
        return TavilyBusca(settings.tavily_api_key)
    if nome == "ollama" and settings.ollama_api_key:
        return OllamaBusca(settings.ollama_api_key)
    if nome:
        log.warning("Busca '%s' sem chave configurada (ou nome inválido) — ignorada", nome)
    return None


def criar_busca() -> BuscaWeb | None:
    """Principal → reserva. Devolve None se nenhuma estiver configurada (a pesquisa de preços é pulada)."""
    servicos = [s for s in (_criar(settings.busca_provider), _criar(settings.busca_reserva)) if s]
    if not servicos:
        return None
    return servicos[0] if len(servicos) == 1 else BuscaComReserva(servicos)
