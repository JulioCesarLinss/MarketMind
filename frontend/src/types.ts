export type Decisao = 'sim' | 'nao' | 'talvez'

export interface Opiniao {
  fala: string
  interesse: number
  compraria: Decisao
  pontos_positivos: string[]
  objecoes: string[]
  mudou_de_opiniao: boolean
  preco_maximo: number | null
  o_que_mudaria: string
}

export interface MensagemDebate {
  persona_id: string
  persona_nome: string
  rodada: 1 | 2
  opiniao: Opiniao
  origem: string
  duracao_segundos: number
}

export interface PersonaPublica {
  id: string
  nome: string
  descricao: string
  prioridades: string
}

export interface ResultadoSimulacao {
  mensagens: MensagemDebate[]
  rodadas: number
  provedor_principal: string
  tokens_usados: number
  duracao_segundos: number
}

export interface SimulacaoCriada {
  id: string
  status: string
}

export interface ConcorrentePayload {
  nome: string
  preco: number
  observacao: string
}

export interface NegocioPayload {
  tipo: string
  localizacao: string
  produto: string
  preco: number
  publico: string
  divulgacao: string
  custos: {
    custo_fixo_mensal: number
    custo_variavel_unitario: number
    taxa_plataforma_pct: number
  } | null
  concorrentes: ConcorrentePayload[]
}


// Mantém exatamente o critério usado pelo backend para identificar mudança de posição.
export function mudouDePosicao(antes: MensagemDebate, depois: MensagemDebate): boolean {
  return antes.opiniao.compraria !== depois.opiniao.compraria
    || Math.abs(antes.opiniao.interesse - depois.opiniao.interesse) >= 2
}
