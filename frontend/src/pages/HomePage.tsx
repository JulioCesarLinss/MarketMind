
import { useState, type FormEvent } from 'react'
import { imagemPersona } from '../personaIcones'
import {
  MIN_AGENTES,
  MODELOS_ENTREGA,
  type ModeloEntrega,
  type NegocioPayload,
  type PersonaPublica,
} from '../types'

interface ConcorrenteRascunho {
  nome: string
  preco: string
  observacao: string
}

interface HomePageProps {
  personas: PersonaPublica[]
  carregando: boolean
  erro: string
  aoAvaliar: (negocio: NegocioPayload, demo: boolean, personas: string[]) => void
}

const concorrenteVazio = (): ConcorrenteRascunho => ({ nome: '', preco: '', observacao: '' })

export default function HomePage({ personas, carregando, erro, aoAvaliar }: HomePageProps) {
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
  const [lucroEsperado, setLucroEsperado] = useState('')
  const [investimento, setInvestimento] = useState('')
  const [concorrentes, setConcorrentes] = useState<ConcorrenteRascunho[]>([])
  const [demo, setDemo] = useState(true)
  // Personas que o usuário DESMARCOU (começa com todas marcadas, mesmo antes de a lista chegar da API)
  const [desmarcadas, setDesmarcadas] = useState<string[]>([])
  const [entrega, setEntrega] = useState(false)
  const [modeloEntrega, setModeloEntrega] = useState<ModeloEntrega>('proprio')
  const [taxaEntrega, setTaxaEntrega] = useState('')
  const [prazoEntrega, setPrazoEntrega] = useState('')
  const [areaEntrega, setAreaEntrega] = useState('')
  const [garantiasEntrega, setGarantiasEntrega] = useState('')
  const escolhidas = personas.filter((p) => !desmarcadas.includes(p.id)).map((p) => p.id)

  function alternarPersona(id: string) {
    if (desmarcadas.includes(id)) {
      setDesmarcadas((atuais) => atuais.filter((item) => item !== id))
    } else if (escolhidas.length > MIN_AGENTES) {
      setDesmarcadas((atuais) => [...atuais, id])
    }
  }

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
            lucro_esperado_pct: lucroEsperado.trim() === '' ? null : Number(lucroEsperado),
            investimento_inicial: investimento.trim() === '' ? null : Number(investimento),
          }
        : null,
      entrega: entrega
        ? {
            disponivel: true,
            modelo: modeloEntrega,
            taxa: taxaEntrega.trim() === '' ? null : Number(taxaEntrega),
            prazo: prazoEntrega.trim(),
            area: areaEntrega.trim(),
            garantias: garantiasEntrega.trim(),
          }
        : { disponivel: false, modelo: null, taxa: null, prazo: '', area: '', garantias: '' },
      concorrentes: concorrentes
        .filter((item) => item.nome.trim() !== '')
        .map((item) => ({
          nome: item.nome.trim(),
          preco: Number(item.preco),
          observacao: item.observacao.trim(),
        })),
    }

    aoAvaliar(negocio, demo, escolhidas)
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
            <span className="eyebrow"><span className="eyebrow-line" /> SIMULAÇÃO ANTES DE INVESTER</span>
            <h1>Uma ideia.<br /><span>Cinco perspectivas.</span></h1>
            <p>
              Descubra como diferentes perfis de consumidores podem reagir ao seu produto,
              debater a oferta e apontar o que merece ser validado.
            </p>
            <div className="hero-proof">
              <div className="avatar-stack" aria-hidden="true">
                <span><img src={imagemPersona('fiel_regiao')} alt="Fiel" /></span>
                <span><img src={imagemPersona('critico')} alt="Crítico" /></span>
                <span><img src={imagemPersona('ocupado')} alt="Ocupado" /></span>
                <span><img src={imagemPersona('exigente')} alt="Exigente" /></span>
                <span><img src={imagemPersona('economico')} alt="Economico" /></span>
              </div>
              <span><strong>5 agentes independentes</strong><br />2 rodadas de avaliação e debate</span>
            </div>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />

            {/* Camada externa: 3 agentes */}
            <div className="orbit-node node-one agent-orbit-motion outer-agent-one">
              <img src={imagemPersona('fiel_regiao')} alt="Fiel" />
            </div>
            <div className="orbit-node node-two agent-orbit-motion outer-agent-two">
              <img src={imagemPersona('critico')} alt="Crítico" />
            </div>
            <div className="orbit-node node-five agent-orbit-motion outer-agent-three">
              <img src={imagemPersona('exigente')} alt="Exigente" />
            </div>

            {/* Camada interna: 2 agentes */}
            <div className="orbit-node node-three agent-orbit-motion inner-agent-one">
              <img src={imagemPersona('ocupado')} alt="Ocupado" />
            </div>
            <div className="orbit-node node-four agent-orbit-motion inner-agent-two">
              <img src={imagemPersona('economico')} alt="Economico" />
            </div>

            {/* Núcleo do MarketMind */}
            <div className="landing-nucleus">
              <img
                src="/favicon2.svg"
                alt="MarketMind"
                className="landing-nucleus-logo"
              />
            </div>

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
                <input id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} placeholder="Ex.: alimentação, venda de serviço" maxLength={120} required />
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
                <label htmlFor="publico">Público alvo<span>*</span></label>
                <input id="publico" value={publico} onChange={(e) => setPublico(e.target.value)} placeholder="Quem você quer atingir?" maxLength={200} required />
              </div>
              <div className="field-group field-full">
                <label htmlFor="divulgacao">Como pretende divulgar? <span>*</span></label>
                <input id="divulgacao" value={divulgacao} onChange={(e) => setDivulgacao(e.target.value)} placeholder="Ex.: Instagram, indicação, anúncios, loja física..." maxLength={200} required />
              </div>
            </div>

            <div className="delivery-box">
              <label className="check-row">
                <input type="checkbox" checked={entrega} onChange={(e) => setEntrega(e.target.checked)} />
                <span><strong>O produto pode ser entregue?</strong> Marque se você faz entrega ao cliente.</span>
              </label>
              {entrega && (
                <div className="form-grid delivery-grid">
                  <div className="field-group field-full">
                    <label htmlFor="modeloEntrega">Modelo de entrega</label>
                    <select id="modeloEntrega" value={modeloEntrega} onChange={(e) => setModeloEntrega(e.target.value as ModeloEntrega)}>
                      {(Object.keys(MODELOS_ENTREGA) as ModeloEntrega[]).map((chave) => (
                        <option key={chave} value={chave}>{MODELOS_ENTREGA[chave]}</option>
                      ))}
                    </select>
                  </div>
                  <div className="field-group">
                    <label htmlFor="taxaEntrega">Taxa de entrega (R$)</label>
                    <input id="taxaEntrega" type="number" min="0" step="0.01" value={taxaEntrega} onChange={(e) => setTaxaEntrega(e.target.value)} placeholder="0 = grátis" />
                  </div>
                  <div className="field-group">
                    <label htmlFor="prazoEntrega">Prazo de entrega</label>
                    <input id="prazoEntrega" value={prazoEntrega} onChange={(e) => setPrazoEntrega(e.target.value)} placeholder="Ex.: 40 minutos, 2 dias úteis" maxLength={80} />
                  </div>
                  <div className="field-group field-full">
                    <label htmlFor="areaEntrega">Área atendida</label>
                    <input id="areaEntrega" value={areaEntrega} onChange={(e) => setAreaEntrega(e.target.value)} placeholder="Ex.: até 5 km, toda a cidade, Brasil todo" maxLength={120} />
                  </div>
                  <div className="field-group field-full">
                    <label htmlFor="garantiasEntrega">O que torna a entrega confiável?</label>
                    <input id="garantiasEntrega" value={garantiasEntrega} onChange={(e) => setGarantiasEntrega(e.target.value)} placeholder="Ex.: rastreio pelo WhatsApp, embalagem lacrada, troca se chegar errado" maxLength={300} />
                    <span className="field-help">Os agentes vão avaliar se esse modelo de entrega passa confiança para o seu produto.</span>
                  </div>
                </div>
              )}
            </div>

            <div className="form-divider"><span>QUEM VAI AVALIAR</span></div>

            <fieldset className="persona-picker">
              <legend>
                <strong>Escolha os consumidores</strong>
                <small>{escolhidas.length} de {personas.length} selecionados · mínimo {MIN_AGENTES}</small>
              </legend>
              <div className="persona-options">
                {personas.map((persona) => {
                  const marcada = escolhidas.includes(persona.id)
                  const travada = marcada && escolhidas.length <= MIN_AGENTES
                  return (
                    <button
                      key={persona.id}
                      type="button"
                      className={`persona-option${marcada ? ' is-selected' : ''}`}
                      aria-pressed={marcada}
                      title={travada ? `Mantenha pelo menos ${MIN_AGENTES} consumidores` : persona.prioridades}
                      onClick={() => alternarPersona(persona.id)}
                    >
                      <span className={`persona-option-icon avatar-${persona.id}`}><img src={imagemPersona(persona.id)} alt="" /></span>
                      <span className="persona-option-name">{persona.nome.replace(/^Consumidor /, '')}</span>
                      <span className="persona-option-check" aria-hidden="true">{marcada ? '✓' : ''}</span>
                    </button>
                  )
                })}
              </div>
            </fieldset>

            <details className="optional-section">
              <summary>
                <span className="optional-plus">＋</span>
                <span><strong>Adicionar dados complementares</strong><small>Custos, lucro esperado, investimento e concorrentes (opcional)</small></span>
                <span className="optional-tag">OPCIONAL</span>
              </summary>
              <div className="optional-content">
                <label className="check-row">
                  <input type="checkbox" checked={incluirCustos} onChange={(e) => setIncluirCustos(e.target.checked)} />
                  <span>Informar custos para ver se o negócio se paga (lucro, ponto de equilíbrio e retorno do investimento)</span>
                </label>
                {incluirCustos && (
                  <div className="form-grid cost-grid">
                    <div className="field-group">
                      <label htmlFor="custoFixo">Custo fixo mensal (R$)</label>
                      <input id="custoFixo" type="number" min="0" step="0.01" value={custoFixo} onChange={(e) => setCustoFixo(e.target.value)} />
                    </div>
                    <div className="field-group">
                      <label htmlFor="custoVariavel">Custo médio de produção por unidade (R$)</label>
                      <input id="custoVariavel" type="number" min="0" step="0.01" value={custoVariavel} onChange={(e) => setCustoVariavel(e.target.value)} />
                    </div>
                    <div className="field-group">
                      <label htmlFor="taxa">Taxa de plataforma (%)</label>
                      <input id="taxa" type="number" min="0" max="100" step="0.1" value={taxa} onChange={(e) => setTaxa(e.target.value)} />
                    </div>
                    <div className="field-group">
                      <label htmlFor="lucroEsperado">Lucro esperado por venda (%)</label>
                      <input id="lucroEsperado" type="number" min="0" max="99" step="1" value={lucroEsperado} onChange={(e) => setLucroEsperado(e.target.value)} placeholder="Opcional · ex.: 30" />
                    </div>
                    <div className="field-group">
                      <label htmlFor="investimento">Investimento inicial (R$)</label>
                      <input id="investimento" type="number" min="0" step="0.01" value={investimento} onChange={(e) => setInvestimento(e.target.value)} placeholder="Opcional · ex.: 20000" />
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
                {carregando ? <><span className="button-spinner" /> Iniciando...</> : <>Avaliar produto</>}
              </button>
            </div>
            {erro && <div className="form-error" role="alert">{erro}</div>}
            <p className="disclaimer">As opiniões são sintéticas e representam hipóteses para validação, ajudando a guiar decisões de negócios.</p>
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