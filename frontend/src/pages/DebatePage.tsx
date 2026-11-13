import AgentCard from '../components/AgentCard'
import EspecialistaCard from '../components/EspecialistaCard'
import MessageCard from '../components/MessageCard'
import ParecerCard from '../components/ParecerCard'
import {
  NOMES_FAIXA,
  type EspecialistaPublico,
  type MensagemDebate,
  type MensagemParecer,
  type PersonaPublica,
  type PesquisaMercado,
} from '../types'

interface DebatePageProps {
  personas: PersonaPublica[]
  especialistas: EspecialistaPublico[]
  mensagens: MensagemDebate[]
  pareceres: MensagemParecer[]
  pesquisa?: PesquisaMercado | null
  statusTexto: string
  erro: string
  onVoltar: () => void
}

function reais(valor: number): string {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export default function DebatePage({ personas, especialistas, mensagens, pareceres, pesquisa, statusTexto, erro, onVoltar }: DebatePageProps) {
  // Cada agente responde uma vez só (não há mais debate entre eles)
  const totalAgentes = Math.max(personas.length + especialistas.length, 1)
  const responderam = mensagens.length + pareceres.length
  const progresso = Math.min((responderam / totalAgentes) * 100, 100)

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
            <h1>As perspectivas<br /><span>estão chegando.</span></h1>
            <p>Consumidores e especialistas avaliam sua oferta, cada um sozinho. Depois, o analista junta tudo, descarta o que for exagerado e escreve o relatório.</p>
          </div>
          <div className="round-indicator">
            <span>AGENTES</span>
            <strong>{String(responderam).padStart(2, '0')}<small> / {String(totalAgentes).padStart(2, '0')}</small></strong>
            <span className="round-caption">Avaliação individual</span>
          </div>
        </div>

        <section className="progress-panel">
          <div className="progress-copy">
            <div><strong>{responderam} <span>/ {totalAgentes}</span></strong><span>avaliações recebidas</span></div>
            <p>{statusTexto}</p>
          </div>
          <div className="progress-track"><div style={{ width: `${progresso}%` }} /></div>
          <div className="progress-labels"><span>Avaliações individuais</span><span>Relatório do analista</span></div>
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
              <p>{pesquisa.observacao || pesquisa.erro || 'Nenhum preço comparável encontrado na internet.'} Os agentes seguem com os dados do formulário.</p>
            )}
          </div>
        )}

        {erro && <div className="stream-error"><strong>Não foi possível concluir a avaliação.</strong><span>{erro}</span><button onClick={onVoltar}>Voltar ao formulário</button></div>}

        <section className="agents-section">
          <div className="section-heading">
            <div><span className="section-index">02 <span>/ OS AGENTES</span></span><h2>Quem está avaliando?</h2></div>
            <span className="live-label"><i /> FEED AO VIVO</span>
          </div>
          {especialistas.length > 0 && <h3 className="agents-group-title">Especialistas</h3>}
          <div className="agents-grid">
            {especialistas.map((especialista) => (
              <EspecialistaCard
                key={especialista.id}
                especialista={especialista}
                parecer={pareceres.find((p) => p.especialista_id === especialista.id)}
              />
            ))}
          </div>
          {personas.length > 0 && <h3 className="agents-group-title">Consumidores</h3>}
          <div className="agents-grid">
            {personas.map((persona) => (
              <AgentCard
                key={persona.id}
                persona={persona}
                mensagens={mensagens.filter((mensagem) => mensagem.persona_id === persona.id)}
                finalizado={false}
              />
            ))}
          </div>
        </section>

        <section className="feed-section">
          <div className="section-heading feed-heading">
            <div><span className="section-index">03 <span>/ AVALIAÇÕES</span></span><h2>O que estão dizendo</h2></div>
            <span className="feed-count">{responderam} avaliações</span>
          </div>
          {responderam === 0 ? (
            <div className="feed-empty"><span className="empty-orbit">✳</span><strong>Os agentes estão organizando suas ideias.</strong><p>As primeiras avaliações vão aparecer aqui assim que estiverem prontas.</p></div>
          ) : (
            <div className="message-list">
              {pareceres.map((parecer, indice) => <ParecerCard key={parecer.especialista_id} mensagem={parecer} indice={indice} />)}
              {mensagens.map((mensagem, indice) => <MessageCard key={mensagem.persona_id} mensagem={mensagem} indice={indice} />)}
            </div>
          )}
        </section>

        <p className="synthetic-note"><span>i</span> As avaliações são geradas por IA (consumidores e especialistas sintéticos) e devem ser tratadas como hipóteses a validar com pessoas reais.</p>
      </main>
    </div>
  )
}
