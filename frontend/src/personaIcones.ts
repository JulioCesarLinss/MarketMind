
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
