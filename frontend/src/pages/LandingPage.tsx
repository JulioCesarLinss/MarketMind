
interface LandingPageProps {
  onComecar: () => void
}

const etapas = [
  {
    numero: '01',
    titulo: 'Apresente sua ideia',
    descricao:
      'Informe o que pretende vender, o preço, o público que deseja alcançar e como planeja divulgar seu negócio.',
    icone: '✳',
  },
  {
    numero: '02',
    titulo: 'Acompanhe as perspectivas',
    descricao:
      'Diferentes perfis de consumidores avaliam sua oferta individualmente e depois debatem suas opiniões.',
    icone: '◉',
  },
  {
    numero: '03',
    titulo: 'Explore os resultados',
    descricao:
      'Receba um panorama com interesses, intenções de compra, objeções e sugestões do que merece ser validado.',
    icone: '↗',
  },
]

const perfis = [
  {
    icone: '₱',
    nome: 'Econômico',
    descricao: 'Analisa preços e custo-benefício.',
    classe: 'economico',
  },
  {
    icone: '✦',
    nome: 'Exigente',
    descricao: 'Valoriza qualidade e experiência.',
    classe: 'exigente',
  },
  {
    icone: '◷',
    nome: 'Ocupado',
    descricao: 'Prioriza praticidade e conveniência.',
    classe: 'ocupado',
  },
  {
    icone: '⌕',
    nome: 'Crítico',
    descricao: 'Questiona diferenciais e concorrentes.',
    classe: 'critico',
  },
  {
    icone: '⌖',
    nome: 'Fiel à região',
    descricao: 'Valoriza proximidade e confiança.',
    classe: 'fiel',
  },
]

export default function LandingPage({ onComecar }: LandingPageProps) {
  return (
    <div className="landing-page">
      <header className="landing-header">
        <a className="brand" href="#apresentacao" aria-label="MarketMind início">
          <span className="brand-mark"><span /></span>
          <span>
            market<span className="brand-light">mind</span>
          </span>
        </a>

        <nav className="landing-nav">
          <a href="#proposta">Nossa proposta</a>
          <a href="#como-funciona">Como funciona</a>
          <a href="#perspectivas">Os consumidores</a>
        </nav>

        <button
          className="landing-header-button"
          onClick={onComecar}
        >
          Começar agora <span>↗</span>
        </button>
      </header>

      <main>
        {/* HERO */}
        <section className="landing-hero" id="apresentacao">
          <div className="landing-hero-content">
            <span className="landing-eyebrow">
              <span />
              INTELIGÊNCIA DE MERCADO
            </span>

            <h1>
              Sua ideia merece
              <br />
              mais perspectivas
              <br />
              <span>antes de sair do papel.</span>
            </h1>

            <p className="landing-hero-description">
              Tomar decisões sobre um negócio nem sempre é simples.
              O MarketMind utiliza múltiplos agentes de inteligência
              artificial para simular diferentes perfis de consumidores,
              avaliar sua oferta e revelar pontos que merecem atenção
              antes de investir.
            </p>

            <div className="landing-hero-actions">
              <button
                className="landing-primary-button"
                onClick={onComecar}
              >
                Avaliar minha ideia <span>↗</span>
              </button>

              <a href="#proposta" className="landing-secondary-button">
                Conhecer a proposta ↓
              </a>
            </div>

            <div className="landing-metrics">
              <div>
                <strong>05</strong>
                <span>Perfis de consumidores</span>
              </div>
              <div>
                <strong>02</strong>
                <span>Rodadas de debate</span>
              </div>
              <div>
                <strong>01</strong>
                <span>Relatório consolidado</span>
              </div>
            </div>
          </div>

          {/* ÁTOMO DOS AGENTES */}
          <div className="landing-visual" aria-hidden="true">
            <div className="landing-orbit landing-orbit-wide" />
            <div className="landing-orbit landing-orbit-tall" />

            <div className="landing-electron landing-outer outer-one">₱</div>
            <div className="landing-electron landing-outer outer-two">✦</div>
            <div className="landing-electron landing-outer outer-three">⌖</div>

            <div className="landing-electron landing-inner inner-one">◷</div>
            <div className="landing-electron landing-inner inner-two">⌕</div>

            <div className="landing-nucleus">
              <span>✳</span>
              <strong>MM</strong>
            </div>

            <div className="landing-visual-caption">
              CINCO PERSPECTIVAS. UMA IDEIA.
            </div>
          </div>
        </section>

        {/* PROBLEMA E PROPOSTA */}
        <section className="landing-proposal" id="proposta">
          <div className="landing-section-label">
            <span>01</span> / O CENÁRIO
          </div>

          <div className="landing-proposal-grid">
            <div>
              <h2>
                Empreender envolve
                <br />
                decisões. Nem sempre
                <br />
                <span>existem informações.</span>
              </h2>
            </div>

            <div className="landing-proposal-text">
              <p>
                Quem deseja abrir ou expandir um negócio precisa
                decidir o que vender, quanto cobrar, para quem vender e
                como apresentar sua oferta.
              </p>

              <p>
                Muitas dessas decisões são tomadas com poucas referências
                de mercado, tornando difícil identificar possíveis
                problemas antes de investir tempo e dinheiro.
              </p>

              <div className="landing-proposal-highlight">
                <span>✳</span>
                <p>
                  É nesse cenário que surge o MarketMind: uma ferramenta
                  para explorar diferentes perspectivas sobre uma ideia
                  de negócio e ajudar a identificar hipóteses que merecem
                  ser testadas.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* COMO FUNCIONA */}
        <section className="landing-how" id="como-funciona">
          <div className="landing-section-heading">
            <div>
              <div className="landing-section-label">
                <span>02</span> / A EXPERIÊNCIA
              </div>
              <h2>
                Da ideia à análise.
                <br />
                <span>Em três etapas.</span>
              </h2>
            </div>

            <p>
              O MarketMind transforma as informações do seu negócio
              em uma simulação estruturada de avaliação e debate.
            </p>
          </div>

          <div className="landing-steps">
            {etapas.map((etapa) => (
              <article className="landing-step" key={etapa.numero}>
                <div className="landing-step-top">
                  <span>{etapa.numero}</span>
                  <div>{etapa.icone}</div>
                </div>

                <h3>{etapa.titulo}</h3>
                <p>{etapa.descricao}</p>
              </article>
            ))}
          </div>
        </section>

        {/* PERSONAS */}
        <section className="landing-personas" id="perspectivas">
          <div className="landing-section-label">
            <span>03</span> / DIFERENTES PERSPECTIVAS
          </div>

          <div className="landing-personas-heading">
            <h2>
              Cinco consumidores.
              <br />
              <span>Cinco formas de pensar.</span>
            </h2>

            <p>
              Cada agente possui características, prioridades e
              comportamentos próprios. Assim, a mesma oferta pode
              despertar reações diferentes.
            </p>
          </div>

          <div className="landing-persona-grid">
            {perfis.map((perfil) => (
              <article
                className={`landing-persona-card persona-${perfil.classe}`}
                key={perfil.nome}
              >
                <div className="landing-persona-icon">
                  {perfil.icone}
                </div>

                <h3>{perfil.nome}</h3>
                <p>{perfil.descricao}</p>
              </article>
            ))}
          </div>

          <div className="landing-debate-note">
            <span>i</span>
            Os agentes não se limitam a avaliações isoladas: eles também
            conhecem as opiniões uns dos outros e podem manter ou mudar
            suas posições durante o debate.
          </div>
        </section>

        {/* TRANSPARÊNCIA */}
        <section className="landing-trust">
          <div className="landing-trust-symbol">✳</div>

          <div>
            <span className="landing-section-label">
              UMA FERRAMENTA DE APOIO À DECISÃO
            </span>

            <h2>
              Mais clareza para decidir.
              <br />
              Mais perguntas para validar.
            </h2>

            <p>
              As opiniões são geradas
              por consumidores sintéticos e ajudam a serem interpretadas como
              hipóteses para orientar decisões e experimentos.
            </p>
          </div>
        </section>

        {/* CHAMADA FINAL */}
        <section className="landing-final-cta">
          <span>MARKETMIND / SUA IDEIA EM PERSPECTIVA</span>

          <h2>
            Toda decisão começa
            <br />
            com uma pergunta.
          </h2>

          <p>
            Apresente sua ideia e descubra diferentes formas de enxergá-la.
          </p>

          <button
            className="landing-primary-button"
            onClick={onComecar}
          >
            Começar minha avaliação <span>↗</span>
          </button>
        </section>
      </main>

      <footer className="landing-footer">
        <a className="brand" href="#apresentacao">
          <span className="brand-mark"><span /></span>
          <span>
            market<span className="brand-light">mind</span>
          </span>
        </a>

        <span>Explore ideias com mais perspectiva.</span>
        <span>© 2026 MarketMind</span>
      </footer>
    </div>
  )
}