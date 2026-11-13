
const IMAGENS_PERSONA: Record<string, string> = {
  economico: '/economico.svg',
  exigente: '/exigente.svg',
  ocupado: '/ocupado.svg',
  critico: '/critico.svg',
  fiel_regiao: '/fiel.svg',
}

export function imagemPersona(id: string): string {
  return IMAGENS_PERSONA[id] || '/favicon.svg'
}

// Especialistas: símbolo em texto (não há desenho próprio para eles)
const SIMBOLOS_ESPECIALISTA: Record<string, string> = {
  precificacao: 'R$',
  marketing: '◎',
  operacoes: '⚙',
  mercado: '▦',
  experiencia: '♥',
  consultor: '★',
}

export function simboloEspecialista(id: string): string {
  return SIMBOLOS_ESPECIALISTA[id] || '✳'
}
