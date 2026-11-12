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
  relatorio?: Relatorio | null
}

// ---- Relatório do agente analista (ver docs/api.md) ----

export interface IndicadorPersona {
  persona_id: string
  persona_nome: string
  interesse_r1: number
  interesse_r2: number
  compraria_r1: Decisao
  compraria_r2: Decisao
  mudou: boolean
  preco_maximo: number | null
}

// Números calculados pelo backend (não pela IA)
export interface Indicadores {
  preco_ofertado: number
  interesse_medio_r1: number
  interesse_medio_r2: number
  decisoes_r2: { sim: number; talvez: number; nao: number }
  preco_maximo_medio: number | null
  mudaram_de_posicao: number
  por_persona: IndicadorPersona[]
}

// Texto escrito pela IA
export interface AnaliseDebate {
  resumo: string
  elogios: string[]
  objecoes: string[]
  fatores_de_decisao: string[]
  pontos_de_atencao: string[]
  recomendacoes: string[]
  experimentos: string[]
}

export interface Relatorio {
  indicadores: Indicadores
  analise: AnaliseDebate | null
  origem_analise: string | null
  erro_analise: string | null
  tokens_usados: number
  duracao_segundos: number
  aviso: string
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
