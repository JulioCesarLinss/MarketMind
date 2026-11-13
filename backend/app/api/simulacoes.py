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

from app.agents.especialistas import ESPECIALISTAS, escolher_especialistas
from app.agents.personas import PERSONAS, escolher_personas
from app.agents.pesquisador import Pesquisador
from app.config import settings
from app.llm import criar_provider
from app.llm.factory import ConfiguracaoLLMError, criar_provider_especialistas
from app.models.negocio import NegocioEntrada
from app.models.schemas import MensagemDebate, MensagemParecer, ResultadoSimulacao
from app.services.busca import criar_busca
from app.services.simulacoes import Evento, PesquisadorDemo, Simulacao, gerenciador

router = APIRouter()

INTERVALO_PING = 15  # segundos: mantém a conexão do feed aberta em proxies (ex.: Render)


class SimulacaoCriada(BaseModel):
    id: str
    status: str
    personas: list[str]  # ids dos consumidores que participam, na ordem
    especialistas: list[str] = []  # ids dos especialistas que participam, na ordem


class SimulacaoEstado(BaseModel):
    id: str
    status: Literal["rodando", "concluida", "erro"]
    negocio: dict
    mensagens: list[MensagemDebate]
    resultado: ResultadoSimulacao | None
    erro: str | None
    personas: list[str]
    especialistas: list[str] = []
    pareceres: list[MensagemParecer] = []


class PersonaPublica(BaseModel):
    id: str
    nome: str
    descricao: str
    prioridades: str


@router.get("/personas", response_model=list[PersonaPublica], tags=["personas"])
def listar_personas():
    """As 5 personas, para o frontend montar a escolha e os cards do feed."""
    return [PersonaPublica(id=p.id, nome=p.nome, descricao=p.descricao, prioridades=p.prioridades)
            for p in PERSONAS.values()]


class EspecialistaPublico(BaseModel):
    id: str
    nome: str
    area: str
    foco: str


@router.get("/especialistas", response_model=list[EspecialistaPublico], tags=["personas"])
def listar_especialistas():
    """Os 6 especialistas (cada um escreve um parecer na sua área)."""
    return [EspecialistaPublico(id=e.id, nome=e.nome, area=e.area, foco=e.foco) for e in ESPECIALISTAS.values()]


MIN_AGENTES = 2  # o analista precisa de pelo menos 2 opiniões para comparar


def separar_agentes(agentes: list[str] | None, personas: list[str] | None):
    """Devolve (consumidores, especialistas) escolhidos.

    - `agentes`: ids de qualquer grupo (consumidores e especialistas). Mínimo 2 no total.
    - Sem `agentes`: consumidores pelo parâmetro antigo `personas` (ou todos) + todos os especialistas."""
    if agentes:
        desconhecidos = [a for a in agentes if a not in PERSONAS and a not in ESPECIALISTAS]
        if desconhecidos:
            raise ValueError(f"agente inexistente: {', '.join(desconhecidos)}")
        consumidores = [p for p in PERSONAS.values() if p.id in set(agentes)]
        especialistas = escolher_especialistas([a for a in agentes if a in ESPECIALISTAS])
        if len(consumidores) + len(especialistas) < MIN_AGENTES:
            raise ValueError(f"escolha pelo menos {MIN_AGENTES} agentes")
        return consumidores, especialistas
    return escolher_personas(personas), escolher_especialistas()


@router.post("/simulacoes", response_model=SimulacaoCriada, status_code=201, tags=["simulacoes"])
async def criar_simulacao(
    negocio: NegocioEntrada,
    demo: bool = Query(False, description="true = respostas gravadas (sem IA, sem gastar cota). Bom para desenvolver o front."),
    agentes: list[str] | None = Query(
        None, description="Ids dos agentes que participam, consumidores e/ou especialistas (repita o parâmetro: "
                          "?agentes=economico&agentes=precificacao). Mínimo 2. Sem o parâmetro, participam todos."),
    personas: list[str] | None = Query(
        None, description="(Antigo) só os consumidores; os especialistas participam todos. Prefira `agentes`."),
):
    try:
        escolhidas, especialistas = separar_agentes(agentes, personas)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    try:
        provider = criar_provider("mock" if demo else None)
    except ConfiguracaoLLMError as erro:
        raise HTTPException(status_code=503, detail=f"IA não configurada no servidor: {erro}") from erro
    try:
        # Sem mock no fim: um relatório gravado de outro negócio seria enganoso
        analista = criar_provider("mock") if demo else criar_provider(papel="analista", mock_no_fim=False)
    except ConfiguracaoLLMError:
        analista = None  # o resultado vem só com os números do relatório
    # Especialistas no Gemini (reserva no Groq), para não disputar o limite por minuto com os consumidores
    provider_especialistas = provider if demo or not especialistas else criar_provider_especialistas()
    pesquisador = PesquisadorDemo() if demo else _pesquisador_real()
    sim = gerenciador.iniciar(negocio.model_dump(), provider, analista, pesquisador, escolhidas,
                              especialistas, provider_especialistas)
    return SimulacaoCriada(id=sim.id, status=sim.status, personas=sim.personas, especialistas=sim.especialistas)


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
                           resultado=sim.resultado, erro=sim.erro, personas=sim.personas,
                           especialistas=sim.especialistas, pareceres=sim.pareceres)


def _sse(evento: Evento) -> str:
    return f"event: {evento.tipo}\ndata: {evento.dados}\n\n"


@router.get("/simulacoes/{id_}/stream", tags=["simulacoes"])
async def acompanhar_simulacao(id_: str):
    """Feed ao vivo (SSE). Eventos:
    - `etapa`: {"etapa": "pesquisa"} no início, enquanto o agente pesquisador busca preços e lojas
    - `pesquisa`: a referência de mercado (PesquisaMercado), antes da primeira fala
    - `mensagem`: a opinião de um consumidor (MensagemDebate)
    - `parecer`: o parecer de um especialista (MensagemParecer)
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
