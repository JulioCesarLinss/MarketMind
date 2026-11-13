import { simboloEspecialista } from '../personaIcones'
import { NOMES_VEREDITO, type MensagemParecer } from '../types'

interface ParecerCardProps {
  mensagem: MensagemParecer
  indice?: number
}

const PRECO: Record<MensagemParecer['parecer']['avaliacao_preco'], string> = {
  baixo: 'Preço baixo',
  adequado: 'Preço adequado',
  alto: 'Preço alto',
}

function reais(valor: number): string {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

// Parecer completo de um especialista (feed da análise e página de resultado)
export default function ParecerCard({ mensagem, indice = 0 }: ParecerCardProps) {
  const p = mensagem.parecer

  return (
    <article className="parecer-card" style={{ animationDelay: `${Math.min(indice * 45, 360)}ms` }}>
      <div className="parecer-topo">
        <span className="parecer-icone" aria-hidden="true">{simboloEspecialista(mensagem.especialista_id)}</span>
        <div className="parecer-identidade">
          <strong>{mensagem.especialista_nome}</strong>
          <span>{mensagem.area}</span>
        </div>
        <div className="parecer-nota" aria-label={`Nota ${p.nota} de 10`}>
          <strong>{p.nota}</strong><small>/10</small>
        </div>
      </div>

      <div className="parecer-selos">
        <span className={`veredito-pill veredito-${p.veredito}`}>{NOMES_VEREDITO[p.veredito]}</span>
        <span className="parecer-preco">
          {PRECO[p.avaliacao_preco]}
          {p.preco_sugerido !== null && <> · sugere <strong>{reais(p.preco_sugerido)}</strong></>}
        </span>
      </div>

      <p className="parecer-resumo">{p.resumo}</p>

      <div className="parecer-listas">
        {p.pontos_fortes.length > 0 && (
          <div><span className="parecer-rotulo positivo">+ Pontos fortes</span><ul>{p.pontos_fortes.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
        )}
        {p.riscos.length > 0 && (
          <div><span className="parecer-rotulo risco">− Riscos</span><ul>{p.riscos.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
        )}
        {p.recomendacoes.length > 0 && (
          <div><span className="parecer-rotulo acao">→ Recomendações</span><ul>{p.recomendacoes.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
        )}
      </div>
      <div className="message-origin">{mensagem.origem} · {mensagem.duracao_segundos.toFixed(1)}s</div>
    </article>
  )
}
