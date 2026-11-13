
import { imagemPersona } from '../personaIcones'
import type { MensagemDebate, PersonaPublica } from '../types'


interface AgentCardProps {
  persona: PersonaPublica
  mensagens: MensagemDebate[]
  rodadaAtual?: 1 | 2 // não é mais usado (não há debate); mantido para compatibilidade
  finalizado: boolean
}

export default function AgentCard({ persona, mensagens, finalizado }: AgentCardProps) {
  const ultimaMensagem = mensagens[mensagens.length - 1]
  const respondeu = mensagens.length > 0
  const pensando = !finalizado && !respondeu

  let status = 'Analisando oferta'
  if (finalizado) status = 'Avaliação concluída'
  else if (respondeu) status = 'Opinião enviada'

  return (
    <article className={`agent-card ${pensando ? 'agent-thinking' : 'agent-answered'}`}>
      <div className="agent-card-top">
        <div className={`agent-avatar avatar-${persona.id}`}>
          <img src={imagemPersona(persona.id)} alt="" />
          {pensando && <i className="avatar-pulse" />}
        </div>
        <div className="agent-identity">
          <strong>{persona.nome}</strong>
          <span>{persona.descricao}</span>
        </div>
        <span className={`agent-status ${pensando ? 'status-thinking' : 'status-done'}`}>
          {pensando && <i />}
          {status}
        </span>
      </div>
      {ultimaMensagem ? (
        <div className="agent-card-opinion">
          <p>{ultimaMensagem.opiniao.fala}</p>
          <div className="agent-opinion-bottom">
            <span>Interesse <strong>{ultimaMensagem.opiniao.interesse}/10</strong></span>
            <span className={`decision-pill decision-${ultimaMensagem.opiniao.compraria}`}>
              {ultimaMensagem.opiniao.compraria === 'sim' ? 'Compraria' : ultimaMensagem.opiniao.compraria === 'nao' ? 'Não compraria' : 'Talvez'}
            </span>
          </div>
        </div>
      ) : (
        <div className="agent-thinking-line">
          <span className="thinking-dots"><i /><i /><i /></span>
          <span>Considerando preço, contexto e prioridades...</span>
        </div>
      )}
    </article>
  )
}
