"""Busca na internet para o agente pesquisador.

Mesmo padrão da camada de LLM: uma interface (`BuscaWeb`), um adaptador por serviço
(Tavily, Ollama) e uma reserva automática. O resto do sistema só chama `criar_busca()`.
"""

from app.services.busca.base import BuscaIndisponivelError, BuscaWeb, ResultadoBusca
from app.services.busca.factory import criar_busca

__all__ = ["BuscaIndisponivelError", "BuscaWeb", "ResultadoBusca", "criar_busca"]
