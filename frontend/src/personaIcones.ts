// Ícone de cada persona (usado no formulário, nos cards dos agentes e no feed)
export const ICONES_PERSONA: Record<string, string> = {
  economico: '₱',
  exigente: '✦',
  ocupado: '◷',
  critico: '⌕',
  fiel_regiao: '⌖',
}

export function iconePersona(id: string): string {
  return ICONES_PERSONA[id] || '✳'
}
