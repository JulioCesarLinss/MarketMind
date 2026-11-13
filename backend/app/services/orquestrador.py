"""Orquestrador (moderador) do debate entre as personas.

Fluxo:
    Rodada 1 — cada persona avalia o negócio sozinha.
    Rodada 2 — cada persona lê um resumo das falas dos OUTROS e reage.

Cada persona tem sua própria memória (histórico de mensagens): na rodada 2 ela
"lembra" o que disse na rodada 1. As chamadas à IA são limitadas por um semáforo
para não estourar o limite por minuto do plano grátis.
"""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable

from app.agents.debate import pedido_rodada_1, pedido_rodada_2
from app.agents.personas import Persona, escolher_personas
from app.config import settings
from app.llm.base import LLMProvider, Mensagens
from app.models.pesquisa import PesquisaMercado
from app.models.schemas import MensagemDebate, Opiniao, ResultadoSimulacao

# Função chamada a cada fala pronta (o script imprime; a API vai enviar ao feed ao vivo)
AoPublicar = Callable[[MensagemDebate], Awaitable[None]]


class Orquestrador:
    def __init__(
        self,
        provider: LLMProvider,
        personas: list[Persona] | None = None,
        concorrencia: int | None = None,
        ao_publicar: AoPublicar | None = None,
        semente: int | None = None,
    ):
        self.provider = provider
        self.personas = personas or escolher_personas()  # padrão: todas
        self.semaforo = asyncio.Semaphore(concorrencia or settings.llm_concorrencia)
        self.ao_publicar = ao_publicar
        # Embaralha a ordem das falas na rodada 2 (semente fixa = resultado reproduzível nos testes)
        self.rng = random.Random(semente)
        # Memória curta: histórico de conversa de cada persona, só durante esta simulação
        self.memoria: dict[str, Mensagens] = {p.id: [] for p in self.personas}

    async def executar(self, negocio: dict, pesquisa: PesquisaMercado | None = None) -> ResultadoSimulacao:
        inicio = time.perf_counter()
        tokens_antes = self.provider.total_tokens()

        rodada_1 = await self._rodada(1, lambda persona: pedido_rodada_1(negocio, pesquisa))
        rodada_2 = await self._rodada(
            2, lambda persona: pedido_rodada_2([m for m in rodada_1 if m.persona_id != persona.id], self.rng)
        )

        return ResultadoSimulacao(
            mensagens=rodada_1 + rodada_2,
            rodadas=2,
            pesquisa=pesquisa,
            provedor_principal=self._nome_principal(),
            tokens_usados=self.provider.total_tokens() - tokens_antes,
            duracao_segundos=round(time.perf_counter() - inicio, 1),
        )

    def _nome_principal(self) -> str:
        """Com reserva, o principal é o primeiro da cadeia; sem reserva, o próprio provedor."""
        provedores = getattr(self.provider, "provedores", None)
        return provedores[0].nome if provedores else self.provider.nome

    async def _rodada(self, numero: int, montar_pedido: Callable[[Persona], str]) -> list[MensagemDebate]:
        """Roda uma rodada com todas as personas (em paralelo, respeitando o semáforo)."""
        tarefas = [self._falar(persona, numero, montar_pedido(persona)) for persona in self.personas]
        mensagens = await asyncio.gather(*tarefas)
        return list(mensagens)

    async def _falar(self, persona: Persona, rodada: int, pedido: str) -> MensagemDebate:
        historico = self.memoria[persona.id]
        historico.append({"role": "user", "content": pedido})

        async with self.semaforo:
            inicio = time.perf_counter()
            opiniao, origem = await self.provider.gerar_com_origem(persona.prompt_sistema(), historico, Opiniao)
            duracao = time.perf_counter() - inicio

        # Guarda a própria resposta na memória da persona, para a próxima rodada
        historico.append({"role": "assistant", "content": opiniao.model_dump_json()})

        mensagem = MensagemDebate(
            persona_id=persona.id,
            persona_nome=persona.nome,
            rodada=rodada,
            opiniao=opiniao,
            origem=origem,
            duracao_segundos=round(duracao, 1),
        )
        if self.ao_publicar:
            await self.ao_publicar(mensagem)
        return mensagem
