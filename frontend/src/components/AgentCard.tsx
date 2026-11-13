import type { MensagemDebate, PersonaPublica } from '../types'

const icones: Record<string, string> = {
  economico: '₱',
  exigente: '✦',
  ocupado: '◷',
  critico: '⌕',
  fiel_regiao: '⌖',
  conectado: '✧',
  familia: '⌂',
  consciente: '❀',
}

interface AgentCardProps {
  persona: PersonaPublica
  mensagens: MensagemDebate[]
  rodadaAtual: 1 | 2
  finalizado: boolean
}

export default function AgentCard({ persona, mensagens, rodadaAtual, finalizado }: AgentCardProps) {
  const ultimaMensagem = mensagens[mensagens.length - 1]
  const respondeuPrimeira = mensagens.some((mensagem) => mensagem.rodada === 1)
  const respondeuSegunda = mensagens.some((mensagem) => mensagem.rodada === 2)
  const pensando = !finalizado && !respondeuSegunda

  let status = 'Analisando oferta'
  if (finalizado) status = 'Avaliação concluída'
  else if (respondeuSegunda) status = 'Participando do debate'
  else if (rodadaAtual === 2 && respondeuPrimeira) status = 'Aguardando resposta'
  else if (respondeuPrimeira) status = 'Primeira opinião enviada'

  return (
    <article className={`agent-card ${pensando ? 'agent-thinking' : 'agent-answered'}`}>
      <div className="agent-card-top">
        <div className={`agent-avatar avatar-${persona.id}`}>
          <span>{icones[persona.id] || '✳'}</span>
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
