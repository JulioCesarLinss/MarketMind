
import { imagemPersona } from '../personaIcones'
import type { MensagemDebate } from '../types'


interface MessageCardProps {
  mensagem: MensagemDebate
  indice: number
  mudouDePosicao?: boolean
}

export default function MessageCard({ mensagem, indice }: MessageCardProps) {
  const decisao = mensagem.opiniao.compraria

  return (
    <article className="message-card" style={{ animationDelay: `${Math.min(indice * 45, 360)}ms` }}>
      <div className="message-avatar"><img src={imagemPersona(mensagem.persona_id)} alt="" /></div>
      <div className="message-content">
        <div className="message-heading">
          <div>
            <strong>{mensagem.persona_nome}</strong>
            <span>Consumidor · avaliação individual</span>
          </div>
          <span className={`decision-pill decision-${decisao}`}>
            {decisao === 'sim' ? 'Compraria' : decisao === 'nao' ? 'Não compraria' : 'Talvez'}
          </span>
        </div>
        <p className="message-speech">{mensagem.opiniao.fala}</p>
        <div className="message-meta">
          <span>Interesse <strong>{mensagem.opiniao.interesse}/10</strong></span>
          {mensagem.opiniao.preco_maximo !== null && (
            <span>Pagaria até <strong>{mensagem.opiniao.preco_maximo.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong></span>
          )}
        </div>
        {(mensagem.opiniao.pontos_positivos.length > 0 || mensagem.opiniao.objecoes.length > 0) && (
          <div className="message-tags">
            {mensagem.opiniao.pontos_positivos.slice(0, 2).map((ponto, i) => <span className="positive-tag" key={`p-${i}`}>+ {ponto}</span>)}
            {mensagem.opiniao.objecoes.slice(0, 2).map((objecao, i) => <span className="objection-tag" key={`o-${i}`}>− {objecao}</span>)}
          </div>
        )}
        {mensagem.opiniao.o_que_mudaria && (
          <div className="suggestion-line"><span>O que mudaria</span>{mensagem.opiniao.o_que_mudaria}</div>
        )}
        <div className="message-origin">{mensagem.origem} · {mensagem.duracao_segundos.toFixed(1)}s</div>
      </div>
    </article>
  )
}
