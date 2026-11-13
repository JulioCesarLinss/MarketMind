import type {
  EspecialistaPublico,
  MensagemDebate,
  MensagemParecer,
  NegocioPayload,
  PersonaPublica,
  PesquisaMercado,
  ResultadoSimulacao,
  SimulacaoCriada,
} from '../types'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function lerErro(resposta: Response): Promise<string> {
  try {
    const corpo = await resposta.json()

    if (Array.isArray(corpo.detail)) {
      return corpo.detail
        .map((erro: { loc?: string[]; msg?: string }) => {
          const campo = erro.loc?.at(-1)
          return `${campo ? `${campo}: ` : ''}${erro.msg || 'valor inválido'}`
        })
        .join(' · ')
    }

    if (typeof corpo.detail === 'string') return corpo.detail
    if (typeof corpo.message === 'string') return corpo.message
  } catch {
    // Se a API não devolver JSON, usa a mensagem genérica abaixo.
  }

  return `Não foi possível concluir a solicitação (HTTP ${resposta.status}).`
}

export async function buscarPersonas(): Promise<PersonaPublica[]> {
  const resposta = await fetch(`${API_URL}/personas`)
  if (!resposta.ok) throw new Error(await lerErro(resposta))
  return resposta.json() as Promise<PersonaPublica[]>
}

export async function buscarEspecialistas(): Promise<EspecialistaPublico[]> {
  const resposta = await fetch(`${API_URL}/especialistas`)
  if (!resposta.ok) throw new Error(await lerErro(resposta))
  return resposta.json() as Promise<EspecialistaPublico[]>
}

export async function criarSimulacao(
  negocio: NegocioPayload,
  demo: boolean,
  agentes: string[], // ids de consumidores e/ou especialistas
): Promise<SimulacaoCriada> {
  const parametros = new URLSearchParams()
  if (demo) parametros.set('demo', 'true')
  agentes.forEach((id) => parametros.append('agentes', id))
  const rota = `/simulacoes?${parametros}`
  const resposta = await fetch(`${API_URL}${rota}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(negocio),
  })

  if (!resposta.ok) throw new Error(await lerErro(resposta))
  return resposta.json() as Promise<SimulacaoCriada>
}

interface EventosFeed {
  aoReceberMensagem: (mensagem: MensagemDebate) => void
  aoReceberParecer?: (parecer: MensagemParecer) => void
  aoIniciarAnalise?: () => void
  aoIniciarPesquisa?: () => void
  aoReceberPesquisa?: (pesquisa: PesquisaMercado) => void
  aoFinalizar: (resultado: ResultadoSimulacao) => void
  aoFalhar: (mensagem: string) => void
  aoReconectar: () => void
}

export function conectarFeed(id: string, eventos: EventosFeed): EventSource {
  const fonte = new EventSource(`${API_URL}/simulacoes/${id}/stream`)

  fonte.addEventListener('mensagem', (evento) => {
    try {
      const dados = (evento as MessageEvent<string>).data
      eventos.aoReceberMensagem(JSON.parse(dados) as MensagemDebate)
    } catch {
      eventos.aoFalhar('A API enviou uma resposta que não pôde ser lida.')
      fonte.close()
    }
  })

  // Parecer de um especialista (chega junto com as opiniões dos consumidores)
  fonte.addEventListener('parecer', (evento) => {
    try {
      eventos.aoReceberParecer?.(JSON.parse((evento as MessageEvent<string>).data) as MensagemParecer)
    } catch {
      // um parecer ilegível não interrompe a avaliação
    }
  })

  // Mudança de etapa: {"etapa": "pesquisa"} no início e {"etapa": "analise"} depois do debate
  fonte.addEventListener('etapa', (evento) => {
    let etapa = 'analise'
    try {
      etapa = JSON.parse((evento as MessageEvent<string>).data).etapa
    } catch {
      // formato antigo do backend: sem dados = análise
    }
    if (etapa === 'pesquisa') eventos.aoIniciarPesquisa?.()
    else eventos.aoIniciarAnalise?.()
  })

  // Referência de mercado do agente pesquisador (chega antes da primeira fala)
  fonte.addEventListener('pesquisa', (evento) => {
    try {
      eventos.aoReceberPesquisa?.(JSON.parse((evento as MessageEvent<string>).data) as PesquisaMercado)
    } catch {
      // sem a pesquisa, a simulação continua normalmente
    }
  })

  fonte.addEventListener('fim', (evento) => {
    try {
      const dados = (evento as MessageEvent<string>).data
      eventos.aoFinalizar(JSON.parse(dados) as ResultadoSimulacao)
    } catch {
      eventos.aoFalhar('A API terminou a avaliação, mas não foi possível ler o resultado.')
    }
    fonte.close()
  })

  fonte.addEventListener('erro', (evento) => {
    const dados = (evento as MessageEvent<string>).data
    eventos.aoFalhar(dados || 'O backend encontrou um erro durante a avaliação.')
    fonte.close()
  })

  fonte.onerror = () => {
    if (fonte.readyState === EventSource.CLOSED) {
      eventos.aoFalhar('A conexão com o backend foi encerrada. Confira se a API continua ativa.')
    } else {
      eventos.aoReconectar()
    }
  }

  return fonte
}

