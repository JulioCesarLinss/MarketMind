import { useState, type ReactElement } from 'react'
import type { Financeiro } from '../types'

interface ViabilidadeFinanceiraProps {
  financeiro: Financeiro
  indiceSecao: string
}

function reais(valor: number): string {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

// Lucro positivo em verde; prejuízo com sinal de menos em vermelho
function resultado(valor: number): ReactElement {
  return valor >= 0
    ? <span className="fin-positivo">{reais(valor)}</span>
    : <span className="fin-negativo">− {reais(-valor)}</span>
}

// Mesma regra do backend (services/financeiro.py → texto_meses): arredonda para cima
function textoMeses(meses: number | null): string {
  if (meses === null) return 'não se paga'
  const m = Math.ceil(meses)
  if (m <= 1) return '~1 mês'
  const anos = Math.floor(m / 12)
  const resto = m % 12
  if (anos === 0) return `~${m} meses`
  const anoTxt = anos === 1 ? '1 ano' : `${anos} anos`
  return `~${anoTxt}${resto ? ` e ${resto} ${resto === 1 ? 'mês' : 'meses'}` : ''}`
}

const AVALIACAO: Record<Financeiro['avaliacao_preco'], { rotulo: string; classe: string }> = {
  dentro_do_esperado: { rotulo: 'O PREÇO FAZ SENTIDO', classe: 'fin-ok' },
  sem_meta: { rotulo: 'O PREÇO COBRE O CUSTO', classe: 'fin-ok' },
  abaixo_do_esperado: { rotulo: 'LUCRO ABAIXO DO ESPERADO', classe: 'fin-atencao' },
  prejuizo: { rotulo: 'CADA VENDA DÁ PREJUÍZO', classe: 'fin-ruim' },
}

export default function ViabilidadeFinanceira({ financeiro: f, indiceSecao }: ViabilidadeFinanceiraProps) {
  // Simulador "e se?": a mesma conta do backend, feita no navegador
  // Escala da barra a partir dos cenários do backend; começa no primeiro cenário que dá lucro
  const maiorCenario = f.cenarios.length ? f.cenarios[f.cenarios.length - 1].clientes_dia : 30
  const maxClientes = Math.max(50, maiorCenario * 2)
  const inicial = f.cenarios.find((c) => c.lucro_mes > 0)?.clientes_dia ?? 10
  const [clientes, setClientes] = useState(inicial)
  const lucroMes = clientes * f.dias_por_mes * f.lucro_por_venda - f.custo_fixo_mensal
  const lucroDia = lucroMes / f.dias_por_mes
  const mesesPagar = f.investimento_inicial && lucroMes > 0 ? f.investimento_inicial / lucroMes : null
  const avaliacao = AVALIACAO[f.avaliacao_preco]
  const [emFoco, setEmFoco] = useState<number | null>(null)

  // Gráfico: lucro (ou prejuízo) do mês para 12 quantidades de clientes por dia
  const lucroDoMes = (c: number) => c * f.dias_por_mes * f.lucro_por_venda - f.custo_fixo_mensal
  const passo = Math.max(1, Math.ceil(maxClientes / 12))
  const pontos = Array.from({ length: 12 }, (_, i) => (i + 1) * passo)
  const valores = pontos.map(lucroDoMes)
  const maiorLucro = Math.max(0, ...valores, lucroMes)
  const maiorPrejuizo = Math.max(0, ...valores.map((v) => -v), -lucroMes)
  const amplitude = maiorLucro + maiorPrejuizo || 1
  const alturaLucro = (maiorLucro / amplitude) * 100 // % da área acima da linha do R$ 0
  const selecionado = pontos.reduce((perto, c) => (Math.abs(c - clientes) < Math.abs(perto - clientes) ? c : perto), pontos[0])
  const focado = emFoco ?? clientes

  return (
    <section className="fin-section">
      <div className="section-heading compact-heading">
        <div><span className="section-index">{indiceSecao} <span>/ FINANCEIRO</span></span><h2>Seu negócio se paga?</h2></div>
        <span className="section-side-caption">Calculado com os custos que você informou</span>
      </div>

      <article className={`fin-verdict ${avaliacao.classe}`}>
        <span>{avaliacao.rotulo}</span>
        <p>{f.resumo_preco}</p>
      </article>

      <div className="fin-aviso-custos"><span>!</span><p>{f.aviso_custos}</p></div>

      <div className="fin-cards">
        <article className="summary-card">
          <span>LUCRO POR VENDA</span>
          <strong>{resultado(f.lucro_por_venda)}</strong>
          <p>{f.margem_pct.toLocaleString('pt-BR')}% do preço · preço {reais(f.preco)} − {f.taxa_plataforma_pct > 0 ? `taxa ${f.taxa_plataforma_pct}% − ` : ''}custo {reais(f.custo_unitario)}</p>
        </article>
        <article className="summary-card">
          <span>CUSTO FIXO MENSAL</span>
          <strong>{reais(f.custo_fixo_mensal)}</strong>
          <p>Descontado do lucro de todos os cenários abaixo</p>
        </article>
        <article className="summary-card">
          <span>INVESTIMENTO</span>
          {f.investimento_inicial ? (
            <>
              <strong>{reais(f.investimento_inicial)}</strong>
              <p>Use o simulador abaixo para ver em quanto tempo ele se paga</p>
            </>
          ) : (
            <>
              <strong className="fin-vazio">—</strong>
              <p>Informe o investimento para ver em quanto tempo o negócio se paga</p>
            </>
          )}
        </article>
      </div>

      {(
        <div className="fin-simulador">
          <div className="fin-simulador-topo">
            <label htmlFor="clientesDia">Considerando <strong>{clientes} clientes por dia</strong> ({clientes * f.dias_por_mes} no mês)</label>
            <input id="clientesDia" type="range" min={1} max={maxClientes} value={clientes} onChange={(e) => setClientes(Number(e.target.value))} />
          </div>
          <div className="fin-simulador-numeros">
            <div><span>Lucro por dia</span><strong>{resultado(lucroDia)}</strong></div>
            <div><span>Lucro por mês</span><strong>{resultado(lucroMes)}</strong></div>
            <div><span>Faturamento por mês</span><strong>{reais(clientes * f.dias_por_mes * f.preco)}</strong></div>
            {f.investimento_inicial ? (
              <div><span>Investimento se paga em</span><strong className={mesesPagar === null ? 'fin-negativo' : ''}>{textoMeses(mesesPagar)}</strong></div>
            ) : null}
          </div>

          <div className="fin-grafico" role="img" aria-label="Lucro ou prejuízo do mês conforme a quantidade de clientes por dia">
            <div className="fin-grafico-legenda">
              <span><i className="fin-cor-lucro" /> Lucro no mês</span>
              <span><i className="fin-cor-prejuizo" /> Prejuízo no mês</span>
              <span className="fin-grafico-foco">
                {focado} clientes/dia: {lucroDoMes(focado) >= 0 ? 'lucro' : 'prejuízo'} de {reais(Math.abs(lucroDoMes(focado)))}/mês
              </span>
            </div>
            <div className="fin-grafico-area" onMouseLeave={() => setEmFoco(null)}>
              <div className="fin-grafico-zero" style={{ top: `${alturaLucro}%` }}><span>R$ 0</span></div>
              {pontos.map((c, i) => {
                const v = valores[i]
                const altura = (Math.abs(v) / amplitude) * 100
                return (
                  <button
                    key={c}
                    type="button"
                    className={`fin-coluna${c === selecionado ? ' is-atual' : ''}`}
                    onMouseEnter={() => setEmFoco(c)}
                    onFocus={() => setEmFoco(c)}
                    onClick={() => setClientes(c)}
                    aria-label={`${c} clientes por dia: ${v >= 0 ? 'lucro' : 'prejuízo'} de ${reais(Math.abs(v))} por mês`}
                  >
                    <span
                      className={v >= 0 ? 'fin-barra-lucro' : 'fin-barra-prejuizo'}
                      style={v >= 0
                        ? { bottom: `${100 - alturaLucro}%`, height: `${altura}%` }
                        : { top: `${alturaLucro}%`, height: `${altura}%` }}
                    />
                  </button>
                )
              })}
            </div>
            <div className="fin-grafico-eixo">
              {pontos.map((c) => <span key={c}>{c}</span>)}
            </div>
            <p className="fin-grafico-legenda-eixo">Clientes por dia · clique numa coluna para simular</p>
          </div>

          <p className="fin-premissa">Lucro já descontado o custo fixo · 1 cliente = 1 venda · {f.dias_por_mes} dias de funcionamento por mês</p>
        </div>
      )}

      {f.cenarios.length > 0 && (
        <div className="fin-tabela-wrap">
          <table className="fin-tabela">
            <thead>
              <tr><th>Clientes por dia</th><th>Faturamento/mês</th><th>Lucro/dia</th><th>Lucro/mês</th>{f.investimento_inicial ? <th>Investimento se paga em</th> : null}</tr>
            </thead>
            <tbody>
              {f.cenarios.map((c) => (
                <tr key={c.clientes_dia}>
                  <td>{c.clientes_dia}</td>
                  <td>{reais(c.faturamento_mes)}</td>
                  <td>{resultado(c.lucro_dia)}</td>
                  <td>{resultado(c.lucro_mes)}</td>
                  {f.investimento_inicial ? <td>{textoMeses(c.meses_para_pagar)}</td> : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {f.cenarios_preco.length > 1 && (
        <div className="fin-tabela-wrap">
          <table className="fin-tabela">
            <thead>
              <tr><th>E com outro preço?</th><th>Preço</th><th>Lucro por venda</th><th>Agentes que pagariam</th></tr>
            </thead>
            <tbody>
              {f.cenarios_preco.map((c) => (
                <tr key={c.rotulo}>
                  <td>{c.rotulo}</td>
                  <td>{reais(c.preco)}</td>
                  <td>{resultado(c.lucro_por_venda)} <small>({c.margem_pct.toLocaleString('pt-BR')}%)</small></td>
                  <td>{c.aceitam !== null ? c.aceitam : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {f.alertas.length > 0 && (
        <ul className="fin-alertas">
          {f.alertas.map((a, i) => <li key={i}><span>!</span>{a}</li>)}
        </ul>
      )}

      <div className="fin-nao-considerado">
        <span>NÃO ENTROU NA CONTA</span>
        <p>{f.nao_considerado.join(' · ')}</p>
      </div>
      <p className="market-disclaimer">{f.aviso}</p>
    </section>
  )
}
