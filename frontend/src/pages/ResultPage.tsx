import AgentCard from '../components/AgentCard'
import MessageCard from '../components/MessageCard'
import { mudouDePosicao, type PersonaPublica, type ResultadoSimulacao } from '../types'

interface ResultPageProps {
  personas: PersonaPublica[]
  resultado: ResultadoSimulacao
  onNovaAvaliacao: () => void
}

function formatarDuracao(segundos: number): string {
  if (segundos < 60) return `${segundos.toFixed(1)}s`
  const minutos = Math.floor(segundos / 60)
  const resto = Math.round(segundos % 60)
  return `${minutos}min ${resto}s`
}

export default function ResultPage({ personas, resultado, onNovaAvaliacao }: ResultPageProps) {
  const mensagensFinais = resultado.mensagens.filter((mensagem) => mensagem.rodada === 2)
  const mensagensDeReferencia = mensagensFinais.length > 0 ? mensagensFinais : resultado.mensagens
  const mediaInteresse = mensagensDeReferencia.length > 0
    ? mensagensDeReferencia.reduce((soma, mensagem) => soma + mensagem.opiniao.interesse, 0) / mensagensDeReferencia.length
    : 0

  const contagem = {
    sim: mensagensDeReferencia.filter((mensagem) => mensagem.opiniao.compraria === 'sim').length,
    talvez: mensagensDeReferencia.filter((mensagem) => mensagem.opiniao.compraria === 'talvez').length,
    nao: mensagensDeReferencia.filter((mensagem) => mensagem.opiniao.compraria === 'nao').length,
  }

  const objecoes = [...new Set(mensagensDeReferencia.flatMap((mensagem) => mensagem.opiniao.objecoes))].slice(0, 6)
  const pontosPositivos = [...new Set(mensagensDeReferencia.flatMap((mensagem) => mensagem.opiniao.pontos_positivos))].slice(0, 6)

  return (
    <div className="page-shell result-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" onClick={(e) => { e.preventDefault(); onNovaAvaliacao() }}>
          <span className="brand-mark"><span /></span>
          <span>market<span className="brand-light">mind</span></span>
        </a>
        <button className="back-button" onClick={onNovaAvaliacao}>＋ Nova avaliação</button>
      </header>

      <main className="result-main">
        <section className="result-hero">
          <div>
            <span className="eyebrow"><span className="eyebrow-line" /> SIMULAÇÃO CONCLUÍDA</span>
            <h1>Sua ideia foi<br /><span>vista por outros ângulos.</span></h1>
            <p>Veja o que chamou atenção, quais dúvidas apareceram e onde vale aprofundar a validação.</p>
          </div>
          <div className="result-stamp"><span>MM</span><strong>DEBATE<br />FINALIZADO</strong><i>✳</i></div>
        </section>

        <section className="summary-section">
          <div className="section-heading">
            <div><span className="section-index">04 <span>/ VISÃO GERAL</span></span><h2>Panorama da avaliação</h2></div>
            <span className="final-status"><i /> CONCLUÍDA</span>
          </div>
          <div className="summary-grid">
            <article className="summary-card summary-highlight">
              <span>INTERESSE SIMULADO</span>
              <strong>{mediaInteresse.toFixed(1).replace('.', ',')}<small>/10</small></strong>
              <p>Média das opiniões após o debate</p>
              <div className="interest-meter"><span style={{ width: `${mediaInteresse * 10}%` }} /></div>
            </article>
            <article className="summary-card">
              <span>OPINIÕES RECEBIDAS</span>
              <strong>{resultado.mensagens.length}<small> / 10</small></strong>
              <p>5 consumidores em 2 rodadas</p>
            </article>
            <article className="summary-card">
              <span>TEMPO DE SIMULAÇÃO</span>
              <strong>{formatarDuracao(resultado.duracao_segundos)}</strong>
              <p>Tempo informado pelo backend</p>
            </article>
            <article className="summary-card">
              <span>PROVEDOR PRINCIPAL</span>
              <strong className="provider-value">{resultado.provedor_principal || '—'}</strong>
              <p>{resultado.tokens_usados.toLocaleString('pt-BR')} tokens informados</p>
            </article>
          </div>
        </section>

        <section className="decision-section">
          <div className="section-heading compact-heading">
            <div><span className="section-index">05 <span>/ DECISÃO DE COMPRA</span></span><h2>Como reagiram à oferta?</h2></div>
            <span className="section-side-caption">Com base na 2ª rodada</span>
          </div>
          <div className="decision-overview">
            <div className="decision-stat decision-yes"><span className="decision-dot" /><strong>{contagem.sim}</strong><span>Comprariam</span></div>
            <div className="decision-stat decision-maybe"><span className="decision-dot" /><strong>{contagem.talvez}</strong><span>Talvez</span></div>
            <div className="decision-stat decision-no"><span className="decision-dot" /><strong>{contagem.nao}</strong><span>Não comprariam</span></div>
            <div className="decision-bar" aria-label={`${contagem.sim} comprariam, ${contagem.talvez} talvez, ${contagem.nao} não comprariam`}>
              <span className="bar-yes" style={{ width: `${contagem.sim * 20}%` }} />
              <span className="bar-maybe" style={{ width: `${contagem.talvez * 20}%` }} />
              <span className="bar-no" style={{ width: `${contagem.nao * 20}%` }} />
            </div>
          </div>
        </section>

        <section className="insights-grid">
          <article className="insight-panel">
            <div className="insight-heading"><span className="insight-icon positive-icon">+</span><div><span>PONTOS POSITIVOS</span><h3>O que agradou</h3></div></div>
            {pontosPositivos.length ? <ul>{pontosPositivos.map((ponto, i) => <li key={i}>{ponto}</li>)}</ul> : <p className="no-insight">Nenhum ponto positivo foi listado nas respostas finais.</p>}
          </article>
          <article className="insight-panel">
            <div className="insight-heading"><span className="insight-icon objection-icon">−</span><div><span>PONTOS DE ATENÇÃO</span><h3>O que gerou objeção</h3></div></div>
            {objecoes.length ? <ul>{objecoes.map((objecao, i) => <li key={i}>{objecao}</li>)}</ul> : <p className="no-insight">Nenhuma objeção foi listada nas respostas finais.</p>}
          </article>
        </section>

        <section className="final-agents-section">
          <div className="section-heading">
            <div><span className="section-index">06 <span>/ PERFIS</span></span><h2>A percepção de cada agente</h2></div>
          </div>
          <div className="agents-grid result-agents-grid">
            {personas.map((persona) => (
              <AgentCard
                key={persona.id}
                persona={persona}
                mensagens={mensagensDeReferencia.filter((mensagem) => mensagem.persona_id === persona.id)}
                rodadaAtual={2}
                finalizado
              />
            ))}
          </div>
        </section>

        <section className="full-feed-section">
          <div className="section-heading feed-heading">
            <div><span className="section-index">07 <span>/ HISTÓRICO</span></span><h2>Debate completo</h2></div>
            <span className="feed-count">{resultado.mensagens.length} mensagens</span>
          </div>
          <div className="message-list">
            {resultado.mensagens.map((mensagem, indice) => {
              const primeira = resultado.mensagens.find((item) => item.persona_id === mensagem.persona_id && item.rodada === 1)
              const mudou = mensagem.rodada === 2 && primeira ? mudouDePosicao(primeira, mensagem) : false
              return <MessageCard key={`${mensagem.persona_id}-${mensagem.rodada}`} mensagem={mensagem} indice={indice} mudouDePosicao={mudou} />
            })}
          </div>
        </section>

        <div className="result-disclaimer">
          <span>i</span>
          <p><strong>Importante:</strong> os resultados representam percepções de consumidores sintéticos, não uma amostra estatística nem uma previsão de vendas. Use os pontos levantados como hipóteses para testar com clientes reais.</p>
        </div>
        <button className="evaluate-button new-evaluation-button" onClick={onNovaAvaliacao}>Avaliar outra ideia <span>↗</span></button>
      </main>
    </div>
  )
}
