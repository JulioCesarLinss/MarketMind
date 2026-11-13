"""Rotas da simulação.

Fluxo para o frontend:
    1. POST /simulacoes            → recebe {"id": ...} na hora
    2. GET  /simulacoes/{id}/stream → feed ao vivo (Server-Sent Events): cada fala chega assim que fica pronta
    3. GET  /simulacoes/{id}        → estado/resultado completo (ex.: ao recarregar a página)
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.personas import MAX_AGENTES, MIN_AGENTES, PADRAO_AGENTES, PERSONAS, escolher_personas
from app.agents.pesquisador import Pesquisador
from app.config import settings
from app.llm import criar_provider
from app.llm.factory import ConfiguracaoLLMError
from app.models.negocio import NegocioEntrada
from app.models.schemas import MensagemDebate, ResultadoSimulacao
from app.services.busca import criar_busca
from app.services.simulacoes import Evento, PesquisadorDemo, Simulacao, gerenciador

router = APIRouter()

INTERVALO_PING = 15  # segundos: mantém a conexão do feed aberta em proxies (ex.: Render)


class SimulacaoCriada(BaseModel):
    id: str
    status: str
    personas: list[str]  # ids das personas que participam, na ordem


class SimulacaoEstado(BaseModel):
    id: str
    status: Literal["rodando", "concluida", "erro"]
    negocio: dict
    mensagens: list[MensagemDebate]
    resultado: ResultadoSimulacao | None
    erro: str | None
    personas: list[str]


class PersonaPublica(BaseModel):
    id: str
    nome: str
    descricao: str
    prioridades: str


@router.get("/personas", response_model=list[PersonaPublica], tags=["personas"])
def listar_personas():
    """Todas as personas disponíveis (até 8), na ordem em que entram na simulação."""
    return [PersonaPublica(id=p.id, nome=p.nome, descricao=p.descricao, prioridades=p.prioridades)
            for p in PERSONAS.values()]


@router.post("/simulacoes", response_model=SimulacaoCriada, status_code=201, tags=["simulacoes"])
async def criar_simulacao(
    negocio: NegocioEntrada,
    demo: bool = Query(False, description="true = respostas gravadas (sem IA, sem gastar cota). Bom para desenvolver o front."),
    agentes: int = Query(PADRAO_AGENTES, ge=MIN_AGENTES, le=MAX_AGENTES,
                         description="Quantos consumidores participam (as N primeiras personas de GET /personas)"),
):
    try:
        provider = criar_provider("mock" if demo else None)
    except ConfiguracaoLLMError as erro:
        raise HTTPException(status_code=503, detail=f"IA não configurada no servidor: {erro}") from erro
    try:
        # Sem mock no fim: um relatório gravado de outro negócio seria enganoso
        analista = criar_provider("mock") if demo else criar_provider(papel="analista", mock_no_fim=False)
    except ConfiguracaoLLMError:
        analista = None  # o resultado vem só com os números do relatório
    pesquisador = PesquisadorDemo() if demo else _pesquisador_real()
    sim = gerenciador.iniciar(negocio.model_dump(), provider, analista, pesquisador, escolher_personas(agentes))
    return SimulacaoCriada(id=sim.id, status=sim.status, personas=sim.personas)


_PESQUISADOR: Pesquisador | None = None


def _pesquisador_real() -> Pesquisador | None:
    """Um pesquisador só para o servidor todo (mantém o cache de 24 h entre simulações)."""
    global _PESQUISADOR
    if not settings.pesquisa_mercado:
        return None
    if _PESQUISADOR is None:
        try:
            _PESQUISADOR = Pesquisador(
                ia_rapida=criar_provider(papel="personas", mock_no_fim=False),
                ia_extracao=criar_provider(papel="analista", mock_no_fim=False),
                busca=criar_busca(),
            )
        except ConfiguracaoLLMError:
            return None  # sem IA configurada não há como pesquisar; a simulação segue sem referência
    return _PESQUISADOR


def _buscar(id_: str) -> Simulacao:
    sim = gerenciador.obter(id_)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulação não encontrada")
    return sim


@router.get("/simulacoes/{id_}", response_model=SimulacaoEstado, tags=["simulacoes"])
def obter_simulacao(id_: str):
    sim = _buscar(id_)
    return SimulacaoEstado(id=sim.id, status=sim.status, negocio=sim.negocio, mensagens=sim.mensagens,
                           resultado=sim.resultado, erro=sim.erro, personas=sim.personas)


def _sse(evento: Evento) -> str:
    return f"event: {evento.tipo}\ndata: {evento.dados}\n\n"


@router.get("/simulacoes/{id_}/stream", tags=["simulacoes"])
async def acompanhar_simulacao(id_: str):
    """Feed ao vivo (SSE). Eventos:
    - `etapa`: {"etapa": "pesquisa"} no início, enquanto o agente pesquisador busca preços e lojas
    - `pesquisa`: a referência de mercado (PesquisaMercado), antes da primeira fala
    - `mensagem`: uma fala (MensagemDebate)
    - `etapa`: {"etapa": "analise"} quando o debate acaba e o analista começa a escrever o relatório
    - `fim`: resultado completo (ResultadoSimulacao, com `relatorio`); depois a conexão fecha
    - `erro`: texto do erro; depois a conexão fecha

    Quem conecta atrasado recebe primeiro as falas que já aconteceram.
    """
    sim = _buscar(id_)
    # Registrar a fila e copiar o passado sem `await` no meio: nenhuma fala se perde
    fila: asyncio.Queue[Evento] = asyncio.Queue()
    sim.ouvintes.append(fila)
    passados = sim.eventos_passados()

    async def gerar() -> AsyncIterator[str]:
        try:
            for evento in passados:
                yield _sse(evento)
                if evento.tipo in ("fim", "erro"):
                    return
            while True:
                try:
                    evento = await asyncio.wait_for(fila.get(), timeout=INTERVALO_PING)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"  # comentário SSE, o navegador ignora
                    continue
                yield _sse(evento)
                if evento.tipo in ("fim", "erro"):
                    return
        finally:
            sim.ouvintes.remove(fila)

    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
