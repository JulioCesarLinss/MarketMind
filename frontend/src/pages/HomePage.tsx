import { useState, type FormEvent } from 'react'
import type { NegocioPayload } from '../types'

interface ConcorrenteRascunho {
  nome: string
  preco: string
  observacao: string
}

interface HomePageProps {
  carregando: boolean
  erro: string
  aoAvaliar: (negocio: NegocioPayload, demo: boolean) => void
}

const concorrenteVazio = (): ConcorrenteRascunho => ({ nome: '', preco: '', observacao: '' })

export default function HomePage({ carregando, erro, aoAvaliar }: HomePageProps) {
  const [nomeProduto, setNomeProduto] = useState('')
  const [descricao, setDescricao] = useState('')
  const [tipo, setTipo] = useState('')
  const [localizacao, setLocalizacao] = useState('')
  const [preco, setPreco] = useState('')
  const [publico, setPublico] = useState('')
  const [divulgacao, setDivulgacao] = useState('')
  const [incluirCustos, setIncluirCustos] = useState(false)
  const [custoFixo, setCustoFixo] = useState('0')
  const [custoVariavel, setCustoVariavel] = useState('0')
  const [taxa, setTaxa] = useState('0')
  const [concorrentes, setConcorrentes] = useState<ConcorrenteRascunho[]>([])
  const [demo, setDemo] = useState(true)

  function atualizarConcorrente(indice: number, campo: keyof ConcorrenteRascunho, valor: string) {
    setConcorrentes((atuais) => atuais.map((item, i) =>
      i === indice ? { ...item, [campo]: valor } : item,
    ))
  }

  function enviarFormulario(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()

    const negocio: NegocioPayload = {
      tipo: tipo.trim(),
      localizacao: localizacao.trim(),
      produto: `${nomeProduto.trim()} — ${descricao.trim()}`,
      preco: Number(preco),
      publico: publico.trim(),
      divulgacao: divulgacao.trim(),
      custos: incluirCustos
        ? {
            custo_fixo_mensal: Number(custoFixo),
            custo_variavel_unitario: Number(custoVariavel),
            taxa_plataforma_pct: Number(taxa),
          }
        : null,
      concorrentes: concorrentes
        .filter((item) => item.nome.trim() !== '')
        .map((item) => ({
          nome: item.nome.trim(),
          preco: Number(item.preco),
          observacao: item.observacao.trim(),
        })),
    }

    aoAvaliar(negocio, demo)
  }

  return (
    <div className="page-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" aria-label="MarketMind início">
          <span className="brand-mark"><span /></span>
          <span>market<span className="brand-light">mind</span></span>
        </a>
        <div className="topbar-right">
          <span className="topbar-caption">INTELIGÊNCIA DE MERCADO</span>
          <span className="topbar-dot" />
          <span className="topbar-caption">BETA</span>
        </div>
      </header>

      <main id="inicio">
        <section className="hero-section">
          <div className="hero-copy">
            <span className="eyebrow"><span className="eyebrow-line" /> SIMULE ANTES DE INVESTIR</span>
            <h1>Uma ideia.<br /><span>Cinco perspectivas.</span></h1>
            <p>
              Descubra como diferentes perfis de consumidores podem reagir ao seu produto,
              debater a oferta e apontar o que merece ser validado.
            </p>
            <div className="hero-proof">
              <div className="avatar-stack" aria-hidden="true">
                <span>₱</span><span>✦</span><span>◷</span><span>⌕</span><span>⌖</span>
              </div>
              <span><strong>5 agentes independentes</strong><br />2 rodadas de avaliação e debate</span>
            </div>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />

            {/* Camada externa: 3 agentes */}
            <div className="orbit-node node-one agent-orbit-motion outer-agent-one">₱</div>
            <div className="orbit-node node-two agent-orbit-motion outer-agent-two">✦</div>
            <div className="orbit-node node-five agent-orbit-motion outer-agent-three">⌖</div>

            {/* Camada interna: 2 agentes */}
            <div className="orbit-node node-three agent-orbit-motion inner-agent-one">◷</div>
            <div className="orbit-node node-four agent-orbit-motion inner-agent-two">⌕</div>

            {/* Núcleo do MarketMind */}
            <div className="orbit-core">
              <span className="core-spark">✳</span>
              <span>MM</span>
            </div>

            <div className="visual-caption">IDEIAS EM PERSPECTIVA</div>
          </div>
        </section>

        <section className="form-layout" aria-labelledby="form-title">
          <div className="form-intro">
            <div className="section-index">01 <span> / SUA IDEIA</span></div>
            <h2 id="form-title">Vamos conhecer<br />seu produto.</h2>
            <p>Conte o que você pretende oferecer. Os agentes vão avaliar a proposta a partir de realidades e prioridades diferentes.</p>
            <div className="form-side-note">
              <span className="note-icon">i</span>
              <p>Quanto mais contexto você informar, mais específicas serão as opiniões geradas.</p>
            </div>
          </div>

          <form className="product-form" onSubmit={enviarFormulario}>
            <div className="form-card-heading">
              <div>
                <span className="form-card-kicker">NOVA SIMULAÇÃO</span>
                <h3>Apresente sua oferta</h3>
              </div>
              <span className="required-note">* Campos obrigatórios</span>
            </div>

            <div className="field-group">
              <label htmlFor="nomeProduto">Nome do produto ou serviço <span>*</span></label>
              <input
                id="nomeProduto"
                value={nomeProduto}
                onChange={(e) => setNomeProduto(e.target.value)}
                placeholder="Ex.: Café Aurora, Marmita Fit..."
                maxLength={120}
                required
              />
            </div>

            <div className="field-group">
              <label htmlFor="descricao">Descrição da oferta <span>*</span></label>
              <textarea
                id="descricao"
                value={descricao}
                onChange={(e) => setDescricao(e.target.value)}
                placeholder="O que é o produto? Quais são suas características e diferenciais?"
                rows={4}
                maxLength={Math.max(0, 1000 - nomeProduto.trim().length - 3)}
                required
              />
              <span className="field-help">Descreva o que o cliente recebe e por que escolheria sua oferta. Nome + descrição: até 1000 caracteres.</span>
            </div>

            <div className="form-divider"><span>CONTEXTO DO NEGÓCIO</span></div>

            <div className="form-grid">
              <div className="field-group">
                <label htmlFor="tipo">Segmento e modelo de venda <span>*</span></label>
                <input id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} placeholder="Ex.: alimentação, delivery" maxLength={120} required />
              </div>
              <div className="field-group">
                <label htmlFor="localizacao">Localização <span>*</span></label>
                <input id="localizacao" value={localizacao} onChange={(e) => setLocalizacao(e.target.value)} placeholder="Bairro e cidade" maxLength={120} required />
              </div>
              <div className="field-group">
                <label htmlFor="preco">Preço de venda (R$) <span>*</span></label>
                <div className="input-prefix"><span>R$</span><input id="preco" type="number" min="0.01" step="0.01" value={preco} onChange={(e) => setPreco(e.target.value)} placeholder="0,00" required /></div>
              </div>
              <div className="field-group">
                <label htmlFor="publico">Público pretendido <span>*</span></label>
                <input id="publico" value={publico} onChange={(e) => setPublico(e.target.value)} placeholder="Quem você quer atingir?" maxLength={200} required />
              </div>
              <div className="field-group field-full">
                <label htmlFor="divulgacao">Como pretende divulgar? <span>*</span></label>
                <input id="divulgacao" value={divulgacao} onChange={(e) => setDivulgacao(e.target.value)} placeholder="Ex.: Instagram, indicação, anúncios, loja física..." maxLength={200} required />
              </div>
            </div>

            <details className="optional-section">
              <summary>
                <span className="optional-plus">＋</span>
                <span><strong>Adicionar dados complementares</strong><small>Custos e concorrentes (opcional)</small></span>
                <span className="optional-tag">OPCIONAL</span>
              </summary>
              <div className="optional-content">
                <label className="check-row">
                  <input type="checkbox" checked={incluirCustos} onChange={(e) => setIncluirCustos(e.target.checked)} />
                  <span>Informar custos para contextualizar a parte financeira</span>
                </label>
                {incluirCustos && (
                  <div className="form-grid cost-grid">
                    <div className="field-group">
                      <label htmlFor="custoFixo">Custo fixo mensal (R$)</label>
                      <input id="custoFixo" type="number" min="0" step="0.01" value={custoFixo} onChange={(e) => setCustoFixo(e.target.value)} />
                    </div>
                    <div className="field-group">
                      <label htmlFor="custoVariavel">Custo variável por unidade (R$)</label>
                      <input id="custoVariavel" type="number" min="0" step="0.01" value={custoVariavel} onChange={(e) => setCustoVariavel(e.target.value)} />
                    </div>
                    <div className="field-group">
                      <label htmlFor="taxa">Taxa de plataforma (%)</label>
                      <input id="taxa" type="number" min="0" max="100" step="0.1" value={taxa} onChange={(e) => setTaxa(e.target.value)} />
                    </div>
                  </div>
                )}

                <div className="competitor-heading">
                  <div><strong>Concorrentes</strong><small>Adicione até 3 alternativas que seu público já encontra.</small></div>
                  {concorrentes.length < 3 && <button className="text-button" type="button" onClick={() => setConcorrentes((atuais) => [...atuais, concorrenteVazio()])}>＋ Adicionar</button>}
                </div>
                {concorrentes.map((concorrente, indice) => (
                  <div className="competitor-row" key={indice}>
                    <div className="field-group">
                      <label htmlFor={`concorrente-${indice}`}>Nome</label>
                      <input id={`concorrente-${indice}`} value={concorrente.nome} onChange={(e) => atualizarConcorrente(indice, 'nome', e.target.value)} placeholder="Nome do concorrente" required />
                    </div>
                    <div className="field-group">
                      <label htmlFor={`preco-concorrente-${indice}`}>Preço (R$)</label>
                      <input id={`preco-concorrente-${indice}`} type="number" min="0" step="0.01" value={concorrente.preco} onChange={(e) => atualizarConcorrente(indice, 'preco', e.target.value)} placeholder="0,00" required />
                    </div>
                    <div className="field-group competitor-observation">
                      <label htmlFor={`obs-concorrente-${indice}`}>Observação</label>
                      <input id={`obs-concorrente-${indice}`} value={concorrente.observacao} onChange={(e) => atualizarConcorrente(indice, 'observacao', e.target.value)} placeholder="Diferencial ou característica" maxLength={300} />
                    </div>
                    <button className="remove-button" type="button" aria-label="Remover concorrente" onClick={() => setConcorrentes((atuais) => atuais.filter((_, i) => i !== indice))}>×</button>
                  </div>
                ))}
                {concorrentes.length === 0 && <p className="empty-competitors">Nenhum concorrente adicionado.</p>}
              </div>
            </details>

            <div className="form-footer">
              <label className="demo-switch">
                <input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} />
                <span className="switch-ui" />
                <span><strong>Modo demonstração</strong><small>Respostas de exemplo, sem chamadas de IA.</small></span>
              </label>
              <button className="evaluate-button" type="submit" disabled={carregando}>
                {carregando ? <><span className="button-spinner" /> Iniciando...</> : <>Avaliar produto <span>↗</span></>}
              </button>
            </div>
            {erro && <div className="form-error" role="alert">{erro}</div>}
            <p className="disclaimer">As opiniões são sintéticas e representam hipóteses para validação, não uma previsão de vendas.</p>
          </form>
        </section>
      </main>

      <footer className="site-footer">
        <a className="brand footer-brand" href="#inicio"><span className="brand-mark"><span /></span><span>market<span className="brand-light">mind</span></span></a>
        <span>Explore ideias com mais perspectiva.</span>
        <span>© 2026 MarketMind</span>
      </footer>
    </div>
  )
}
