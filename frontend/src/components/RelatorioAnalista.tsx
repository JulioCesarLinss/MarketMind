import type { Relatorio } from '../types'

interface RelatorioAnalistaProps {
  relatorio: Relatorio
  indiceSecao: string
}

const AREAS = ['Preço', 'Produto', 'Conveniência', 'Divulgação']

// O analista começa cada ponto de atenção com a área ("Preço: ..."); separa para virar etiqueta
function separarArea(texto: string): { area: string | null; resto: string } {
  const match = texto.match(/^\s*([^:]{3,20}):\s*(.+)$/s)
  if (match && AREAS.some((area) => area.toLowerCase() === match[1].trim().toLowerCase())) {
    return { area: match[1].trim(), resto: match[2] }
  }
  return { area: null, resto: texto }
}

export default function RelatorioAnalista({ relatorio, indiceSecao }: RelatorioAnalistaProps) {
  const { analise } = relatorio

  return (
    <section className="report-section">
      <div className="section-heading compact-heading">
        <div><span className="section-index">{indiceSecao} <span>/ RELATÓRIO</span></span><h2>O que o analista recomenda</h2></div>
        {relatorio.origem_analise && <span className="section-side-caption">Escrito por IA a partir do debate</span>}
      </div>

      {!analise ? (
        <div className="report-error">
          <span>!</span>
          <p>{relatorio.erro_analise || 'O relatório em texto não está disponível nesta simulação.'} Os números acima continuam válidos.</p>
        </div>
      ) : (
        <>
          <article className="report-summary">
            <span>RESUMO</span>
            <p>{analise.resumo}</p>
          </article>

          <div className="report-grid">
            <article className="insight-panel report-recommendations">
              <div className="insight-heading">
                <span className="insight-icon recommendation-icon">→</span>
                <div><span>RECOMENDAÇÕES</span><h3>O que ajustar, por prioridade</h3></div>
              </div>
              <ol>{analise.recomendacoes.map((item, i) => <li key={i}>{item}</li>)}</ol>
            </article>

            <article className="insight-panel">
              <div className="insight-heading">
                <span className="insight-icon factor-icon">◎</span>
                <div><span>FATORES DE DECISÃO</span><h3>O que pesou na escolha</h3></div>
              </div>
              <ul>{analise.fatores_de_decisao.map((item, i) => <li key={i}>{item}</li>)}</ul>
            </article>

            <article className="insight-panel">
              <div className="insight-heading">
                <span className="insight-icon objection-icon">!</span>
                <div><span>PONTOS DE ATENÇÃO</span><h3>Onde estão os riscos</h3></div>
              </div>
              <ul className="attention-list">
                {analise.pontos_de_atencao.map((item, i) => {
                  const { area, resto } = separarArea(item)
                  return <li key={i}>{area && <span className="area-tag">{area}</span>}{resto}</li>
                })}
              </ul>
            </article>
          </div>

          <article className="experiments-panel">
            <div className="insight-heading">
              <span className="insight-icon experiment-icon">⚗</span>
              <div><span>EXPERIMENTOS</span><h3>Valide com clientes reais</h3></div>
            </div>
            <div className="experiments-list">
              {analise.experimentos.map((item, i) => (
                <div className="experiment-card" key={i}>
                  <span>TESTE {String(i + 1).padStart(2, '0')}</span>
                  <p>{item}</p>
                </div>
              ))}
            </div>
          </article>
        </>
      )}
    </section>
  )
}
