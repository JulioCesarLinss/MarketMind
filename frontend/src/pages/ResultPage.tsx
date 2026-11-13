import AgentCard from '../components/AgentCard'
import MessageCard from '../components/MessageCard'
import MercadoRegiao from '../components/MercadoRegiao'
import RelatorioAnalista from '../components/RelatorioAnalista'
import { mudouDePosicao, type PersonaPublica, type ResultadoSimulacao } from '../types'

interface ResultPageProps {
  personas: PersonaPublica[]
  resultado: ResultadoSimulacao
  onNovaAvaliacao: () => void
}

function formatarReais(valor: number): string {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
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

  // Relatório do agente analista: números calculados pelo backend + texto escrito pela IA.
  // Se não vier (backend antigo), a tela continua funcionando com os cálculos locais.
  const relatorio = resultado.relatorio ?? null
  const indicadores = relatorio?.indicadores ?? null
  const analise = relatorio?.analise ?? null
  const interesseFinal = indicadores ? indicadores.interesse_medio_r2 : mediaInteresse
  const decisoes = indicadores ? indicadores.decisoes_r2 : contagem
  const totalAgentes = Math.max(decisoes.sim + decisoes.talvez + decisoes.nao, 1)
  const larguraDecisao = (n: number) => `${(n / totalAgentes) * 100}%`
  const precoMaximo = indicadores?.preco_maximo_medio ?? null

  // Numeração das seções: só conta as que existem nesta simulação
  const pesquisa = resultado.pesquisa ?? null
  const num = (n: number) => String(n).padStart(2, '0')
  const secaoMercado = 6
  const secaoRelatorio = secaoMercado + (pesquisa ? 1 : 0)
  const secaoPerfis = secaoRelatorio + (relatorio ? 1 : 0)
  const secaoHistorico = secaoPerfis + 1

  const objecoes = analise
    ? analise.objecoes
    : [...new Set(mensagensDeReferencia.flatMap((mensagem) => mensagem.opiniao.objecoes))].slice(0, 6)
  const pontosPositivos = analise
    ? analise.elogios
    : [...new Set(mensagensDeReferencia.flatMap((mensagem) => mensagem.opiniao.pontos_positivos))].slice(0, 6)

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
              <strong>{interesseFinal.toFixed(1).replace('.', ',')}<small>/10</small></strong>
              <p>
                {indicadores
                  ? `Antes do debate: ${indicadores.interesse_medio_r1.toFixed(1).replace('.', ',')} · depois: ${indicadores.interesse_medio_r2.toFixed(1).replace('.', ',')}`
                  : 'Média das opiniões após o debate'}
              </p>
              <div className="interest-meter"><span style={{ width: `${interesseFinal * 10}%` }} /></div>
            </article>
            {indicadores && precoMaximo !== null ? (
              <article className={`summary-card ${precoMaximo < indicadores.preco_ofertado ? 'price-below' : 'price-ok'}`}>
                <span>PREÇO QUE PAGARIAM</span>
                <strong>{formatarReais(precoMaximo)}</strong>
                <p>Média do máximo aceito · você cobra {formatarReais(indicadores.preco_ofertado)}</p>
                <div className="price-meter" aria-hidden="true">
                  <span style={{ width: `${Math.min(100, (precoMaximo / indicadores.preco_ofertado) * 100)}%` }} />
                </div>
              </article>
            ) : (
              <article className="summary-card">
                <span>OPINIÕES RECEBIDAS</span>
                <strong>{resultado.mensagens.length}<small> / {personas.length * 2}</small></strong>
                <p>{personas.length} consumidores em 2 rodadas</p>
              </article>
            )}
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
            <div className="decision-stat decision-yes"><span className="decision-dot" /><strong>{decisoes.sim}</strong><span>Comprariam</span></div>
            <div className="decision-stat decision-maybe"><span className="decision-dot" /><strong>{decisoes.talvez}</strong><span>Talvez</span></div>
            <div className="decision-stat decision-no"><span className="decision-dot" /><strong>{decisoes.nao}</strong><span>Não comprariam</span></div>
            <div className="decision-bar" aria-label={`${decisoes.sim} comprariam, ${decisoes.talvez} talvez, ${decisoes.nao} não comprariam`}>
              <span className="bar-yes" style={{ width: larguraDecisao(decisoes.sim) }} />
              <span className="bar-maybe" style={{ width: larguraDecisao(decisoes.talvez) }} />
              <span className="bar-no" style={{ width: larguraDecisao(decisoes.nao) }} />
            </div>
          </div>
        </section>

        <section className="insights-grid">
          <article className="insight-panel">
            <div className="insight-heading"><span className="insight-icon positive-icon">+</span><div><span>PONTOS POSITIVOS</span><h3>O que agradou</h3></div></div>
            {pontosPositivos.length ? <ul>{pontosPositivos.map((ponto, i) => <li key={i}>{ponto}</li>)}</ul> : <p className="no-insight">Nenhum ponto positivo foi listado nas respostas finais.</p>}
          </article>
          <article className="insight-panel">
            <div className="insight-heading"><span className="insight-icon objection-icon">−</span><div><span>OBJEÇÕES</span><h3>O que gerou objeção</h3></div></div>
            {objecoes.length ? <ul>{objecoes.map((objecao, i) => <li key={i}>{objecao}</li>)}</ul> : <p className="no-insight">Nenhuma objeção foi listada nas respostas finais.</p>}
          </article>
        </section>

        {pesquisa && <MercadoRegiao pesquisa={pesquisa} indiceSecao={num(secaoMercado)} />}

        {relatorio && <RelatorioAnalista relatorio={relatorio} indiceSecao={num(secaoRelatorio)} />}

        <section className="final-agents-section">
          <div className="section-heading">
            <div><span className="section-index">{num(secaoPerfis)} <span>/ PERFIS</span></span><h2>A percepção de cada agente</h2></div>
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
            <div><span className="section-index">{num(secaoHistorico)} <span>/ HISTÓRICO</span></span><h2>Debate completo</h2></div>
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
          <p><strong>Importante:</strong> {relatorio?.aviso || 'os resultados representam percepções de consumidores sintéticos, não uma amostra estatística nem uma previsão de vendas. Use os pontos levantados como hipóteses para testar com clientes reais.'}</p>
        </div>
        <button className="evaluate-button new-evaluation-button" onClick={onNovaAvaliacao}>Avaliar outra ideia <span>↗</span></button>
      </main>
    </div>
  )
}
