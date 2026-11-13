"""Guarda as simulações em andamento e avisa quem está assistindo (feed ao vivo).

Ordem dos eventos de uma simulação:
    etapa {"etapa":"pesquisa"} → pesquisa (JSON) → mensagem (1 por consumidor) e parecer (1 por especialista),
    misturados, na ordem em que ficam prontos → etapa {"etapa":"analise"} → fim
(sem pesquisador configurado, os dois primeiros não aparecem)

MVP: tudo em memória. Se o servidor reiniciar, as simulações somem (o SQLite vem depois).
"""

import asyncio
import json
import logging
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from app.agents.analista import analisar
from app.agents.especialistas import Especialista
from app.agents.personas import Persona, escolher_personas
from app.llm.base import LLMProvider
from app.models.pesquisa import PesquisaMercado
from app.models.schemas import MensagemDebate, MensagemParecer, ResultadoSimulacao
from app.services.orquestrador import Orquestrador

log = logging.getLogger(__name__)

Status = Literal["rodando", "concluida", "erro"]
LIMITE_EM_MEMORIA = 50  # guarda só as últimas N simulações
ETAPA_PESQUISA = '{"etapa": "pesquisa"}'
ETAPA_ANALISE = '{"etapa": "analise"}'
DEMO_PESQUISA = Path(__file__).resolve().parents[2] / "demo_data" / "pesquisamercado.json"


class PesquisadorProtocolo(Protocol):
    async def executar(self, negocio: dict) -> PesquisaMercado: ...


class PesquisadorDemo:
    """Modo demo: devolve uma pesquisa gravada (sem internet, sem cota)."""

    async def executar(self, negocio: dict) -> PesquisaMercado:
        await asyncio.sleep(0.5)
        return PesquisaMercado.model_validate_json(DEMO_PESQUISA.read_text(encoding="utf-8"))


@dataclass
class Evento:
    tipo: Literal["mensagem", "parecer", "etapa", "pesquisa", "fim", "erro"]
    dados: str  # JSON pronto para enviar


@dataclass
class Simulacao:
    id: str
    negocio: dict
    status: Status = "rodando"
    etapa: Literal["pesquisa", "debate", "analise"] = "debate"
    pesquisa: PesquisaMercado | None = None
    mensagens: list[MensagemDebate] = field(default_factory=list)
    resultado: ResultadoSimulacao | None = None
    erro: str | None = None
    ouvintes: list[asyncio.Queue] = field(default_factory=list)
    tarefa: asyncio.Task | None = None
    teve_pesquisa: bool = False
    personas: list[str] = field(default_factory=list)  # ids dos consumidores que participam
    especialistas: list[str] = field(default_factory=list)  # ids dos especialistas que participam
    pareceres: list[MensagemParecer] = field(default_factory=list)

    def avisar(self, evento: Evento) -> None:
        for fila in self.ouvintes:
            fila.put_nowait(evento)

    def eventos_passados(self) -> list[Evento]:
        """O que já aconteceu, para quem conecta no meio (ou depois) da simulação."""
        eventos = []
        if self.teve_pesquisa:
            eventos.append(Evento("etapa", ETAPA_PESQUISA))
        if self.pesquisa is not None:
            eventos.append(Evento("pesquisa", self.pesquisa.model_dump_json()))
        eventos += [Evento("mensagem", m.model_dump_json()) for m in self.mensagens]
        eventos += [Evento("parecer", p.model_dump_json()) for p in self.pareceres]
        if self.etapa == "analise":
            eventos.append(Evento("etapa", ETAPA_ANALISE))
        if self.status == "concluida" and self.resultado:
            eventos.append(Evento("fim", self.resultado.model_dump_json()))
        elif self.status == "erro":
            eventos.append(Evento("erro", self.erro or "erro desconhecido"))
        return eventos


class GerenciadorSimulacoes:
    def __init__(self) -> None:
        self._simulacoes: OrderedDict[str, Simulacao] = OrderedDict()

    def obter(self, id_: str) -> Simulacao | None:
        return self._simulacoes.get(id_)

    def iniciar(
        self,
        negocio: dict,
        provider: LLMProvider,
        provider_analista: LLMProvider | None,
        pesquisador: PesquisadorProtocolo | None = None,
        personas: list[Persona] | None = None,
        especialistas: list[Especialista] | None = None,
        provider_especialistas: LLMProvider | None = None,
    ) -> Simulacao:
        personas = escolher_personas() if personas is None else personas
        especialistas = especialistas or []
        sim = Simulacao(id=uuid.uuid4().hex[:12], negocio=negocio, personas=[p.id for p in personas],
                        especialistas=[e.id for e in especialistas])
        self._simulacoes[sim.id] = sim
        while len(self._simulacoes) > LIMITE_EM_MEMORIA:
            self._simulacoes.popitem(last=False)
        # Roda em segundo plano: a API responde na hora com o id
        sim.tarefa = asyncio.create_task(self._executar(sim, provider, provider_analista, pesquisador, personas,
                                                        especialistas, provider_especialistas))
        return sim

    async def _pesquisar(self, sim: Simulacao, pesquisador: PesquisadorProtocolo) -> PesquisaMercado | None:
        sim.etapa, sim.teve_pesquisa = "pesquisa", True
        sim.avisar(Evento("etapa", ETAPA_PESQUISA))
        try:
            pesquisa = await pesquisador.executar(sim.negocio)
        except Exception as erro:  # noqa: BLE001 — sem pesquisa, o debate segue como antes
            log.exception("Pesquisa de mercado falhou na simulação %s", sim.id)
            pesquisa = PesquisaMercado(erro=f"A pesquisa de mercado falhou ({type(erro).__name__}).")
        sim.pesquisa = pesquisa
        sim.avisar(Evento("pesquisa", pesquisa.model_dump_json()))
        sim.etapa = "debate"
        return pesquisa

    async def _executar(
        self,
        sim: Simulacao,
        provider: LLMProvider,
        provider_analista: LLMProvider | None,
        pesquisador: PesquisadorProtocolo | None,
        personas: list[Persona],
        especialistas: list[Especialista] | None = None,
        provider_especialistas: LLMProvider | None = None,
    ) -> None:
        async def ao_publicar(m: MensagemDebate) -> None:
            sim.mensagens.append(m)
            sim.avisar(Evento("mensagem", m.model_dump_json()))

        async def ao_publicar_parecer(p: MensagemParecer) -> None:
            sim.pareceres.append(p)
            sim.avisar(Evento("parecer", p.model_dump_json()))

        try:
            # Pesquisa de mercado (só entra no contexto das personas se trouxe dados: ver formatar_negocio)
            pesquisa = await self._pesquisar(sim, pesquisador) if pesquisador else None
            resultado = await Orquestrador(
                provider, personas=personas, ao_publicar=ao_publicar,
                especialistas=especialistas, provider_especialistas=provider_especialistas,
                ao_publicar_parecer=ao_publicar_parecer,
            ).executar(sim.negocio, pesquisa)

            # Todos opinaram: o analista junta, filtra o que foi extrapolado e escreve o relatório
            sim.etapa = "analise"
            sim.avisar(Evento("etapa", ETAPA_ANALISE))
            resultado.relatorio = await analisar(provider_analista, sim.negocio, resultado)
            resultado.tokens_usados += resultado.relatorio.tokens_usados + (pesquisa.tokens_usados if pesquisa else 0)

            sim.resultado = resultado
            sim.status = "concluida"
            sim.avisar(Evento("fim", sim.resultado.model_dump_json()))
        except Exception as erro:  # noqa: BLE001 — qualquer falha vira evento de erro no feed
            log.exception("Simulação %s falhou", sim.id)
            sim.status = "erro"
            # Mensagem genérica para o público; o detalhe fica só no log do servidor
            sim.erro = f"A simulação falhou ({type(erro).__name__}). Tente novamente em instantes."
            sim.avisar(Evento("erro", sim.erro))


gerenciador = GerenciadorSimulacoes()
