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
  pesquisa?: PesquisaMercado | null
}

// ---- Pesquisa de mercado do agente pesquisador (internet + OpenStreetMap) ----

export type NomeFaixa = 'popular' | 'intermediaria' | 'premium'

export const NOMES_FAIXA: Record<NomeFaixa, string> = {
  popular: 'Popular',
  intermediaria: 'Intermediária',
  premium: 'Premium',
}

export interface ExemploMercado {
  faixa: NomeFaixa
  estabelecimento: string
  item: string
  preco: number
  fonte_url: string
}

export interface FaixaMercado {
  faixa: NomeFaixa
  quantidade: number
  media: number | null
  desvio_padrao: number | null
  minimo: number | null
  maximo: number | null
  dados_suficientes: boolean
  exemplos: ExemploMercado[]
}

export interface LojasRegiao {
  quantidade: number | null
  raio_metros: number
  categoria: string
  nivel_concorrencia: string // 'nenhum concorrente mapeado' | 'baixa' | 'media' | 'alta' | 'indeterminado'
  nomes: string[]
  fonte: string
  erro: string | null
  observacao: string
}

export interface PosicaoPreco {
  preco_usuario: number
  media_mercado: number | null
  desvio_padrao_mercado: number | null
  desvios_da_media: number | null
  faixa_mais_proxima: NomeFaixa | null
  resumo: string
}

export interface PesquisaMercado {
  consultas: string[]
  faixas: FaixaMercado[]
  total_precos: number
  media_geral: number | null
  desvio_padrao_geral: number | null
  posicao: PosicaoPreco | null
  lojas_regiao: LojasRegiao | null
  fontes: { titulo: string; url: string }[]
  provedor_busca: string | null
  tokens_usados: number
  duracao_segundos: number
  gerada_em: string
  erro: string | null
  aviso: string
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
  personas: string[] // ids das personas que participam
}

export const MIN_AGENTES = 2
export const MAX_AGENTES = 8
export const PADRAO_AGENTES = 5

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
  entrega: EntregaPayload | null
  concorrentes: ConcorrentePayload[]
}

export type ModeloEntrega = 'proprio' | 'app_delivery' | 'entregador_parceiro' | 'correios' | 'outro'

export const MODELOS_ENTREGA: Record<ModeloEntrega, string> = {
  proprio: 'Entregador próprio',
  app_delivery: 'App de delivery (iFood, 99Food...)',
  entregador_parceiro: 'Motoboy terceirizado / app de entregas (Lalamove, Uber Flash, Loggi...)',
  correios: 'Correios ou transportadora',
  outro: 'Outro',
}

export interface EntregaPayload {
  disponivel: boolean
  modelo: ModeloEntrega | null
  taxa: number | null
  prazo: string
  area: string
  garantias: string
}


// Mantém exatamente o critério usado pelo backend para identificar mudança de posição.
export function mudouDePosicao(antes: MensagemDebate, depois: MensagemDebate): boolean {
  return antes.opiniao.compraria !== depois.opiniao.compraria
    || Math.abs(antes.opiniao.interesse - depois.opiniao.interesse) >= 2
}
