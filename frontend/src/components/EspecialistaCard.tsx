import { simboloEspecialista } from '../personaIcones'
import { NOMES_VEREDITO, type EspecialistaPublico, type MensagemParecer } from '../types'

interface EspecialistaCardProps {
  especialista: EspecialistaPublico
  parecer?: MensagemParecer
}

// Card de status de um especialista durante a análise (mesmo visual do card dos consumidores)
export default function EspecialistaCard({ especialista, parecer }: EspecialistaCardProps) {
  const pensando = !parecer

  return (
    <article className={`agent-card ${pensando ? 'agent-thinking' : 'agent-answered'}`}>
      <div className="agent-card-top">
        <div className="agent-avatar especialista-avatar">
          <span>{simboloEspecialista(especialista.id)}</span>
          {pensando && <i className="avatar-pulse" />}
        </div>
        <div className="agent-identity">
          <strong>{especialista.nome}</strong>
          <span>{especialista.foco}</span>
        </div>
        <span className={`agent-status ${pensando ? 'status-thinking' : 'status-done'}`}>
          {pensando && <i />}
          {pensando ? 'Escrevendo parecer' : 'Parecer enviado'}
        </span>
      </div>
      {parecer ? (
        <div className="agent-card-opinion">
          <p>{parecer.parecer.resumo}</p>
          <div className="agent-opinion-bottom">
            <span>Nota <strong>{parecer.parecer.nota}/10</strong></span>
            <span className={`veredito-pill veredito-${parecer.parecer.veredito}`}>{NOMES_VEREDITO[parecer.parecer.veredito]}</span>
          </div>
        </div>
      ) : (
        <div className="agent-thinking-line">
          <span className="thinking-dots"><i /><i /><i /></span>
          <span>Analisando {especialista.area}...</span>
        </div>
      )}
    </article>
  )
}
