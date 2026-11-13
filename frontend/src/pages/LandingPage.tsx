
import { imagemPersona } from '../personaIcones'
import { useEffect } from 'react'

interface LandingPageProps {
  onComecar: () => void
}

const etapas = [
  {
    numero: '01',
    titulo: 'Apresente sua ideia',
    descricao:
      'Informe o que pretende vender, o preço, o público que deseja alcançar e como planeja divulgar seu negócio.',
    icone: 'ideia.svg',
  },
  {
    numero: '02',
    titulo: 'Acompanhe as perspectivas',
    descricao:
      'Diferentes perfis de consumidores avaliam sua oferta individualmente e depois debatem suas opiniões.',
    icone: 'perspectiva.svg',
  },
  {
    numero: '03',
    titulo: 'Explore os resultados',
    descricao:
      'Receba um panorama com interesses, intenções de compra, objeções e sugestões do que merece ser validado.',
    icone: '/grafico.svg'
  },
]

const perfis = [
  {
    id: 'economico',
    nome: 'Econômico',
    descricao: 'Analisa preços e custo-benefício.',
    classe: 'economico',
  },
  {
    id: 'exigente',
    nome: 'Exigente',
    descricao: 'Valoriza qualidade e experiência.',
    classe: 'exigente',
  },
  {
    id: 'ocupado',
    nome: 'Ocupado',
    descricao: 'Prioriza praticidade e conveniência.',
    classe: 'ocupado',
  },
  {
    id: 'critico',
    nome: 'Crítico',
    descricao: 'Questiona diferenciais e concorrentes.',
    classe: 'critico',
  },
  {
    id: 'fiel_regiao',
    nome: 'Fiel à região',
    descricao: 'Valoriza proximidade e confiança.',
    classe: 'fiel',
  },
]

export default function LandingPage({ onComecar }: LandingPageProps) {

  useEffect(() => {
    const elementos = document.querySelectorAll<HTMLElement>('[data-reveal]')

    const movimentoReduzido = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches

    if (movimentoReduzido || !('IntersectionObserver' in window)) {
      elementos.forEach((elemento) => {
        elemento.classList.add('is-visible')
      })
      return
    }

    const observer = new IntersectionObserver((entradas) => {
      entradas.forEach((entrada) => {
        if (entrada.isIntersecting) {
          entrada.target.classList.add('is-visible')
          observer.unobserve(entrada.target)
        }
      })
    }, {
      threshold: 0.12,
      rootMargin: '0px 0px -40px 0px',
    })

    elementos.forEach((elemento) => observer.observe(elemento))

    return () => observer.disconnect()
  }, [])

  return (
    <div className="landing-page">
      <header className="landing-header" data-reveal="down">
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
          Começar agora
        </button>
      </header>

      <main>
        {/* HERO */}
        <section className="landing-hero" id="apresentacao">
          <div className="landing-hero-content" data-reveal="left">
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
                Avaliar minha ideia <span>➤</span>
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
          <div className="landing-visual" aria-hidden="true" data-reveal="fade">
            <div className="landing-orbit landing-orbit-wide" />
            <div className="landing-orbit landing-orbit-tall" />

            <div className="landing-electron landing-outer outer-one">
              <img src={imagemPersona('fiel_regiao')} alt="Fiel" />
            </div>

            <div className="landing-electron landing-outer outer-two">
              <img src={imagemPersona('critico')} alt="Crítico" />
            </div>

            <div className="landing-electron landing-outer outer-three">
              <img src={imagemPersona('ocupado')} alt="Ocupado" />
            </div>

            <div className="landing-electron landing-inner inner-one">
              <img src={imagemPersona('economico')} alt="Economico" />
            </div>

            <div className="landing-electron landing-inner inner-two">
              <img src={imagemPersona('exigente')} alt="Exigente" />
            </div>

            <div className="landing-nucleus">
              <img
                src="/favicon2.svg"
                alt="MarketMind"
                className="landing-nucleus-logo"
              />
            </div>

            <div className="landing-visual-caption">
              CINCO PERSPECTIVAS. UMA IDEIA.
            </div>
          </div>
        </section>

        {/* PROBLEMA E PROPOSTA */}
        <section className="landing-proposal" id="proposta">
          <div className="landing-section-label" data-reveal="down">
            <span>01</span> / O CENÁRIO
          </div>

          <div className="landing-proposal-grid" data-reveal>
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
                <span><img src="/exclamacao.svg" alt="" /></span>

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
          <div className="landing-section-heading" data-reveal>
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
              <article
                className="landing-step"
                key={etapa.numero}
                data-reveal
              >
                <div className="landing-step-top">
                  <span>{etapa.numero}</span>
                  <div>
                    <img src={etapa.icone} alt="" />
                  </div>
                </div>

                <h3>{etapa.titulo}</h3>
                <p>{etapa.descricao}</p>
              </article>
            ))}
          </div>
        </section>

        {/* PERSONAS */}
        <section className="landing-personas" id="perspectivas">
          <div className="landing-section-label" data-reveal="down">
            <span>03</span> / DIFERENTES PERSPECTIVAS
          </div>

          <div className="landing-personas-heading" data-reveal>
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
                data-reveal
              >
                <div className="landing-persona-icon">
                  <img src={imagemPersona(perfil.id)} alt="" />
                </div>

                <h3>{perfil.nome}</h3>
                <p>{perfil.descricao}</p>
              </article>
            ))}
          </div>

          <div className="landing-debate-note" data-reveal>
            <span>i</span>
            Os agentes não se limitam a avaliações isoladas: eles também
            conhecem as opiniões uns dos outros e podem manter ou mudar
            suas posições durante o debate.
          </div>
        </section>

        {/* TRANSPARÊNCIA */}
        <section className="landing-trust">
          <div className="landing-trust-symbol" data-reveal="scale">✳</div>

          <div data-reveal>
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
          <span data-reveal="down">
            MARKETMIND / SUA IDEIA EM PERSPECTIVA
          </span>

          <h2 data-reveal>
            Toda decisão começa
            <br />
            com uma pergunta.
          </h2>

          <p data-reveal>
            Apresente sua ideia e descubra diferentes formas de enxergá-la.
          </p>

          <button
            className="landing-primary-button"
            onClick={onComecar}
            data-reveal="scale"
          >
            Começar minha avaliação
          </button>
        </section>
      </main>

      <footer className="landing-footer" data-reveal>
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
