"""Provedor com reserva: tenta cada provedor da lista, em ordem, até um responder.

Ordem padrão: provedor principal (Groq) → reserva (Gemini) → mock.
Qualquer falha passa para o próximo: limite estourado (429), servidor
sobrecarregado (503), falta de conexão ou resposta em formato inválido.
"""

import logging

from app.llm.base import LLMProvider, Mensagens, T

logger = logging.getLogger(__name__)


class TodosProvedoresFalharamError(Exception):
    """Nenhum provedor da lista conseguiu responder."""


class FallbackProvider(LLMProvider):
    nome = "reserva"

    def __init__(self, provedores: list[LLMProvider]):
        super().__init__(modelo=" → ".join(f"{p.nome}/{p.modelo}" for p in provedores))
        self.provedores = provedores

    async def gerar_com_origem(
        self, sistema: str, mensagens: Mensagens, schema: type[T], tentativas: int = 2
    ) -> tuple[T, str]:
        erros: list[str] = []
        for provedor in self.provedores:
            try:
                return await provedor.gerar_com_origem(sistema, mensagens, schema, tentativas)
            except Exception as erro:
                logger.warning(
                    "%s/%s falhou (%s) — passando para o próximo provedor",
                    provedor.nome, provedor.modelo, type(erro).__name__,
                )
                erros.append(f"{provedor.nome}: {type(erro).__name__}: {str(erro)[:200]}")
        raise TodosProvedoresFalharamError(" | ".join(erros))

    def total_tokens(self) -> int:
        return sum(p.total_tokens() for p in self.provedores)

    async def gerar(self, sistema: str, mensagens: Mensagens, schema: type[T], tentativas: int = 2) -> T:
        resultado, _ = await self.gerar_com_origem(sistema, mensagens, schema, tentativas)
        return resultado

    async def _completar(self, sistema: str, mensagens: Mensagens) -> str:  # não usado
        raise NotImplementedError
