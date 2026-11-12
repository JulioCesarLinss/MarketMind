import AgentCard from '../components/AgentCard'
import MessageCard from '../components/MessageCard'
import { mudouDePosicao, NOMES_FAIXA, type MensagemDebate, type PersonaPublica, type PesquisaMercado } from '../types'

interface DebatePageProps {
  personas: PersonaPublica[]
  mensagens: MensagemDebate[]
  rodadaAtual: 1 | 2
  pesquisa?: PesquisaMercado | null
  statusTexto: string
  erro: string
  onVoltar: () => void
}

function reais(valor: number): string {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export default function DebatePage({ personas, mensagens, rodadaAtual, pesquisa, statusTexto, erro, onVoltar }: DebatePageProps) {
  const progresso = Math.min((mensagens.length / 10) * 100, 100)

  return (
    <div className="page-shell debate-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" onClick={(e) => { e.preventDefault(); onVoltar() }}>
          <span className="brand-mark"><span /></span>
          <span>market<span className="brand-light">mind</span></span>
        </a>
        <button className="back-button" onClick={onVoltar}>← Nova avaliação</button>
      </header>

      <main className="debate-main">
        <div className="debate-title-row">
          <div>
            <span className="eyebrow"><span className="eyebrow-line" /> SIMULAÇÃO EM ANDAMENTO</span>
            <h1>As perspectivas<br /><span>estão se encontrando.</span></h1>
            <p>Os agentes estão avaliando sua oferta e, em seguida, vão reagir às opiniões uns dos outros.</p>
          </div>
          <div className="round-indicator">
            <span>RODADA ATUAL</span>
            <strong>0{rodadaAtual}<small> / 02</small></strong>
            <span className="round-caption">{rodadaAtual === 1 ? 'Avaliação individual' : 'Debate entre perfis'}</span>
          </div>
        </div>

        <section className="progress-panel">
          <div className="progress-copy">
            <div><strong>{mensagens.length} <span>/ 10</span></strong><span>opiniões recebidas</span></div>
            <p>{statusTexto}</p>
          </div>
          <div className="progress-track"><div style={{ width: `${progresso}%` }} /></div>
          <div className="progress-labels"><span>Primeira avaliação</span><span>Debate concluído</span></div>
        </section>

        {pesquisa && (
          <div className="market-strip">
            <span className="market-strip-label">REFERÊNCIA DE MERCADO</span>
            {pesquisa.total_precos > 0 && pesquisa.media_geral !== null ? (
              <p>
                <strong>{pesquisa.total_precos} preços</strong> encontrados na internet · média <strong>{reais(pesquisa.media_geral)}</strong>
                {pesquisa.posicao?.faixa_mais_proxima && <> · seu preço está mais perto da faixa <strong>{NOMES_FAIXA[pesquisa.posicao.faixa_mais_proxima]}</strong></>}
              </p>
            ) : (
              <p>{pesquisa.erro || 'Nenhum preço comparável encontrado na internet.'} Os agentes seguem com os dados do formulário.</p>
            )}
          </div>
        )}

        {erro && <div className="stream-error"><strong>Não foi possível concluir a avaliação.</strong><span>{erro}</span><button onClick={onVoltar}>Voltar ao formulário</button></div>}

        <section className="agents-section">
          <div className="section-heading">
            <div><span className="section-index">02 <span>/ OS AGENTES</span></span><h2>Quem está pensando?</h2></div>
            <span className="live-label"><i /> FEED AO VIVO</span>
          </div>
          <div className="agents-grid">
            {personas.map((persona) => (
              <AgentCard
                key={persona.id}
                persona={persona}
                mensagens={mensagens.filter((mensagem) => mensagem.persona_id === persona.id)}
                rodadaAtual={rodadaAtual}
                finalizado={false}
              />
            ))}
          </div>
        </section>

        <section className="feed-section">
          <div className="section-heading feed-heading">
            <div><span className="section-index">03 <span>/ O DEBATE</span></span><h2>O que estão dizendo</h2></div>
            <span className="feed-count">{mensagens.length} mensagens</span>
          </div>
          {mensagens.length === 0 ? (
            <div className="feed-empty"><span className="empty-orbit">✳</span><strong>Os agentes estão organizando suas ideias.</strong><p>As primeiras opiniões vão aparecer aqui assim que estiverem prontas.</p></div>
          ) : (
            <div className="message-list">
              {mensagens.map((mensagem, indice) => {
                const primeira = mensagens.find((item) => item.persona_id === mensagem.persona_id && item.rodada === 1)
                const mudou = mensagem.rodada === 2 && primeira ? mudouDePosicao(primeira, mensagem) : false
                return <MessageCard key={`${mensagem.persona_id}-${mensagem.rodada}`} mensagem={mensagem} indice={indice} mudouDePosicao={mudou} />
              })}
            </div>
          )}
        </section>

        <p className="synthetic-note"><span>i</span> As opiniões são de consumidores sintéticos e devem ser tratadas como hipóteses a validar com pessoas reais.</p>
      </main>
    </div>
  )
}
