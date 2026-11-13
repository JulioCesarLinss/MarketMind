"""Orquestrador da avaliação: consumidores e especialistas opinam SEM conversar entre si.

Fluxo (uma rodada só):
    - Cada consumidor (Groq) dá a sua opinião sobre o negócio, sozinho.
    - Cada especialista (Gemini) escreve o seu parecer, sozinho.
    Os dois grupos rodam AO MESMO TEMPO, cada um com o seu limite de chamadas simultâneas
    (são provedores diferentes, então um não atrasa o outro).
    Quem junta tudo, descarta o que for extrapolado e escreve o relatório é o agente analista.

O debate em 2 rodadas foi retirado: as personas reagindo umas às outras não acrescentava
informação útil e deixava as opiniões mais duras e repetitivas.
"""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable

from app.agents.contexto import formatar_negocio
from app.agents.debate import pedido_rodada_1
from app.agents.especialistas import Especialista, pedido_parecer
from app.agents.personas import Persona, escolher_personas
from app.config import settings
from app.llm.base import LLMProvider
from app.models.pesquisa import PesquisaMercado
from app.models.schemas import MensagemDebate, MensagemParecer, Opiniao, ParecerEspecialista, ResultadoSimulacao

log = logging.getLogger(__name__)

# Funções chamadas a cada resposta pronta (o script imprime; a API envia ao feed ao vivo)
AoPublicar = Callable[[MensagemDebate], Awaitable[None]]
AoPublicarParecer = Callable[[MensagemParecer], Awaitable[None]]


class Orquestrador:
    def __init__(
        self,
        provider: LLMProvider,
        personas: list[Persona] | None = None,
        concorrencia: int | None = None,
        ao_publicar: AoPublicar | None = None,
        semente: int | None = None,
        especialistas: list[Especialista] | None = None,
        provider_especialistas: LLMProvider | None = None,
        ao_publicar_parecer: AoPublicarParecer | None = None,
    ):
        self.provider = provider
        # None = as 5 personas; lista vazia = nenhum consumidor (só especialistas)
        self.personas = escolher_personas() if personas is None else personas
        self.especialistas = especialistas or []
        self.provider_especialistas = provider_especialistas or provider
        limite = concorrencia or settings.llm_concorrencia
        self.semaforo = asyncio.Semaphore(limite)
        # Provedor diferente = limite próprio; mesmo provedor = divide o mesmo limite
        self.semaforo_especialistas = (
            asyncio.Semaphore(limite) if self.provider_especialistas is not provider else self.semaforo
        )
        self.ao_publicar = ao_publicar
        self.ao_publicar_parecer = ao_publicar_parecer
        self.rng = random.Random(semente)  # mantido para compatibilidade (não há mais embaralhamento de rodada 2)

    async def executar(self, negocio: dict, pesquisa: PesquisaMercado | None = None) -> ResultadoSimulacao:
        inicio = time.perf_counter()
        tokens_antes = self._tokens()
        texto_negocio = formatar_negocio(negocio, pesquisa)

        tarefas_consumidores = [self._falar(p, pedido_rodada_1(negocio, pesquisa)) for p in self.personas]
        tarefas_especialistas = [self._parecer(e, pedido_parecer(texto_negocio)) for e in self.especialistas]
        mensagens, pareceres = await asyncio.gather(
            asyncio.gather(*tarefas_consumidores), asyncio.gather(*tarefas_especialistas)
        )

        return ResultadoSimulacao(
            mensagens=list(mensagens),
            pareceres=[p for p in pareceres if p is not None],
            rodadas=1,
            pesquisa=pesquisa,
            provedor_principal=self._nome_principal(),
            tokens_usados=self._tokens() - tokens_antes,
            duracao_segundos=round(time.perf_counter() - inicio, 1),
        )

    def _tokens(self) -> int:
        total = self.provider.total_tokens()
        if self.provider_especialistas is not self.provider:
            total += self.provider_especialistas.total_tokens()
        return total

    def _nome_principal(self) -> str:
        """Com reserva, o principal é o primeiro da cadeia; sem reserva, o próprio provedor."""
        provedores = getattr(self.provider, "provedores", None)
        return provedores[0].nome if provedores else self.provider.nome

    async def _falar(self, persona: Persona, pedido: str) -> MensagemDebate:
        async with self.semaforo:
            inicio = time.perf_counter()
            opiniao, origem = await self.provider.gerar_com_origem(
                persona.prompt_sistema(), [{"role": "user", "content": pedido}], Opiniao
            )
            duracao = time.perf_counter() - inicio
        mensagem = MensagemDebate(persona_id=persona.id, persona_nome=persona.nome, rodada=1, opiniao=opiniao,
                                  origem=origem, duracao_segundos=round(duracao, 1))
        if self.ao_publicar:
            await self.ao_publicar(mensagem)
        return mensagem

    async def _parecer(self, especialista: Especialista, pedido: str) -> MensagemParecer | None:
        """Se o parecer falhar em todos os provedores, ele fica de fora (a avaliação continua)."""
        try:
            async with self.semaforo_especialistas:
                inicio = time.perf_counter()
                parecer, origem = await self.provider_especialistas.gerar_com_origem(
                    especialista.prompt_sistema(), [{"role": "user", "content": pedido}], ParecerEspecialista
                )
                duracao = time.perf_counter() - inicio
        except Exception:  # noqa: BLE001
            log.exception("Parecer do especialista %s falhou", especialista.id)
            return None
        mensagem = MensagemParecer(especialista_id=especialista.id, especialista_nome=especialista.nome,
                                   area=especialista.area, parecer=parecer, origem=origem,
                                   duracao_segundos=round(duracao, 1))
        if self.ao_publicar_parecer:
            await self.ao_publicar_parecer(mensagem)
        return mensagem
