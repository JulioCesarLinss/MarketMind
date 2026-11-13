import AgentCard from '../components/AgentCard'
import MessageCard from '../components/MessageCard'
import MercadoRegiao from '../components/MercadoRegiao'
import ParecerCard from '../components/ParecerCard'
import RelatorioAnalista from '../components/RelatorioAnalista'
import ViabilidadeFinanceira from '../components/ViabilidadeFinanceira'
import type { EspecialistaPublico, PersonaPublica, ResultadoSimulacao } from '../types'

interface ResultPageProps {
  personas: PersonaPublica[]
  especialistas?: EspecialistaPublico[]
  resultado: ResultadoSimulacao
  onNovaAvaliacao: () => void
}

function formatarReais(valor: number): string {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatarDuracao(segundos: number): string {
  if (segundos < 60) return `${segundos.toFixed(1)}s`
  const minutos = Math.floor(segundos / 60)
  const resto = Math.round(segundos % 60)
  return `${minutos}min ${resto}s`
}

export default function ResultPage({ personas, resultado, onNovaAvaliacao }: ResultPageProps) {
  // Sem debate: cada consumidor tem uma opinião só (se vier um resultado antigo, usa a última rodada)
  const mensagensFinais = resultado.mensagens.filter((mensagem) => mensagem.rodada === 2)
  const mensagensDeReferencia = mensagensFinais.length > 0 ? mensagensFinais : resultado.mensagens
  const pareceres = resultado.pareceres ?? []
  const temConsumidores = mensagensDeReferencia.length > 0
  const mediaInteresse = temConsumidores
    ? mensagensDeReferencia.reduce((soma, mensagem) => soma + mensagem.opiniao.interesse, 0) / mensagensDeReferencia.length
    : 0

  const contagem = {
    sim: mensagensDeReferencia.filter((mensagem) => mensagem.opiniao.compraria === 'sim').length,
    talvez: mensagensDeReferencia.filter((mensagem) => mensagem.opiniao.compraria === 'talvez').length,
    nao: mensagensDeReferencia.filter((mensagem) => mensagem.opiniao.compraria === 'nao').length,
  }

  // Relatório do agente analista: números calculados pelo backend + texto escrito pela IA.
  const relatorio = resultado.relatorio ?? null
  const indicadores = relatorio?.indicadores ?? null
  const analise = relatorio?.analise ?? null
  const interesseFinal = indicadores ? indicadores.interesse_medio_r2 : mediaInteresse
  const decisoes = indicadores ? indicadores.decisoes_r2 : contagem
  const totalAgentes = Math.max(decisoes.sim + decisoes.talvez + decisoes.nao, 1)
  const larguraDecisao = (n: number) => `${(n / totalAgentes) * 100}%`
  const precoMaximo = indicadores?.preco_maximo_medio ?? null
  // Veredito do preço calculado pelo backend: se a maioria pagaria o preço cobrado, ele é o "preço ideal"
  const avaliacaoPreco = indicadores?.avaliacao_preco ?? (precoMaximo !== null ? 'antigo' : 'sem_dados')
  const precoReferencia = indicadores?.preco_referencia ?? precoMaximo
  const totalPersonas = indicadores?.por_persona.length ?? 0

  // Especialistas: nota média e vereditos (calculados pelo backend; se faltar, calcula aqui)
  const notaEspecialistas = indicadores?.nota_media_especialistas
    ?? (pareceres.length ? pareceres.reduce((soma, p) => soma + p.parecer.nota, 0) / pareceres.length : null)
  const favoraveis = pareceres.filter((p) => p.parecer.veredito === 'favoravel').length
  const comAjustes = pareceres.filter((p) => p.parecer.veredito === 'favoravel_com_ajustes').length

  // Numeração das seções: só conta as que existem nesta avaliação
  const pesquisa = resultado.pesquisa ?? null
  const financeiro = relatorio?.financeiro ?? null
  const num = (n: number) => String(n).padStart(2, '0')
  let proxima = 5
  const secaoDecisao = temConsumidores ? proxima++ : 0
  const secaoEspecialistas = pareceres.length ? proxima++ : 0
  const secaoMercado = pesquisa ? proxima++ : 0
  const secaoFinanceiro = financeiro ? proxima++ : 0
  const secaoRelatorio = relatorio ? proxima++ : 0
  const secaoPerfis = temConsumidores ? proxima++ : 0
  const secaoHistorico = temConsumidores ? proxima++ : 0

  const objecoes = analise
    ? analise.objecoes
    : [...new Set(mensagensDeReferencia.flatMap((mensagem) => mensagem.opiniao.objecoes))].slice(0, 6)
  const pontosPositivos = analise
    ? analise.elogios
    : [...new Set(mensagensDeReferencia.flatMap((mensagem) => mensagem.opiniao.pontos_positivos))].slice(0, 6)

  return (
    <div className="page-shell result-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" onClick={(e) => { e.preventDefault(); onNovaAvaliacao() }}>
          <span className="brand-mark"><span /></span>
          <span>market<span className="brand-light">mind</span></span>
        </a>
        <button className="back-button" onClick={onNovaAvaliacao}>＋ Nova avaliação</button>
      </header>

      <main className="result-main">
        <section className="result-hero">
          <div>
            <span className="eyebrow"><span className="eyebrow-line" /> AVALIAÇÃO CONCLUÍDA</span>
            <h1>Sua ideia foi<br /><span>vista por outros ângulos.</span></h1>
            <p>Veja o que chamou atenção, quais dúvidas apareceram e onde vale aprofundar a validação.</p>
          </div>
          <div className="result-stamp"><span><img src="/favicon2.svg" alt="Favicon"/></span><strong>AVALIAÇÃO<br />FINALIZADA</strong><i>✳</i></div>
        </section>

        <section className="summary-section">
          <div className="section-heading">
            <div><span className="section-index">04 <span>/ VISÃO GERAL</span></span><h2>Panorama da avaliação</h2></div>
            <span className="final-status"><i /> CONCLUÍDA</span>
          </div>
          <div className="summary-grid">
            {notaEspecialistas !== null && (
              <article className="summary-card summary-highlight">
                <span>NOTA DOS ESPECIALISTAS</span>
                <strong>{notaEspecialistas.toFixed(1).replace('.', ',')}<small>/10</small></strong>
                <p>{favoraveis} favoráveis · {comAjustes} com ajustes · {pareceres.length - favoraveis - comAjustes} desfavoráveis</p>
                <div className="interest-meter"><span style={{ width: `${notaEspecialistas * 10}%` }} /></div>
              </article>
            )}
            {temConsumidores && (
              <article className={`summary-card${notaEspecialistas === null ? ' summary-highlight' : ''}`}>
                <span>INTERESSE DOS CONSUMIDORES</span>
                <strong>{interesseFinal.toFixed(1).replace('.', ',')}<small>/10</small></strong>
                <p>Média de {mensagensDeReferencia.length} consumidores sintéticos</p>
                <div className="interest-meter"><span style={{ width: `${interesseFinal * 10}%` }} /></div>
              </article>
            )}
            {temConsumidores && indicadores && precoReferencia !== null && avaliacaoPreco !== 'sem_dados' && (
              avaliacaoPreco === 'ideal' || avaliacaoPreco === 'espaco_para_subir' ? (
                <article className="summary-card price-ok">
                  <span>PREÇO IDEAL</span>
                  <strong>{formatarReais(indicadores.preco_ofertado)}</strong>
                  <p>
                    {indicadores.aceitam_preco} de {totalPersonas} pagariam o seu preço
                    {avaliacaoPreco === 'espaco_para_subir' && indicadores.preco_maximo_mediano
                      ? ` · aceitariam até ${formatarReais(indicadores.preco_maximo_mediano)}: há espaço para subir`
                      : ''}
                  </p>
                  <div className="price-meter" aria-hidden="true">
                    <span style={{ width: `${(Number(indicadores.aceitam_preco) / Math.max(totalPersonas, 1)) * 100}%` }} />
                  </div>
                </article>
              ) : (
                <article className={`summary-card ${precoReferencia < indicadores.preco_ofertado ? 'price-below' : 'price-ok'}`}>
                  <span>PREÇO QUE PAGARIAM</span>
                  <strong>{formatarReais(precoReferencia)}</strong>
                  <p>
                    {avaliacaoPreco === 'acima_do_aceito'
                      ? `Só ${indicadores.aceitam_preco} de ${totalPersonas} pagariam ${formatarReais(indicadores.preco_ofertado)}`
                      : `Média do máximo aceito · você cobra ${formatarReais(indicadores.preco_ofertado)}`}
                  </p>
                  <div className="price-meter" aria-hidden="true">
                    <span style={{ width: `${Math.min(100, (precoReferencia / indicadores.preco_ofertado) * 100)}%` }} />
                  </div>
                </article>
              )
            )}
            <article className="summary-card">
              <span>TEMPO DE AVALIAÇÃO</span>
              <strong>{formatarDuracao(resultado.duracao_segundos)}</strong>
              <p>{resultado.tokens_usados.toLocaleString('pt-BR')} tokens · {pareceres.length} especialistas e {mensagensDeReferencia.length} consumidores</p>
            </article>
          </div>
        </section>

        {temConsumidores && (
          <section className="decision-section">
            <div className="section-heading compact-heading">
              <div><span className="section-index">{num(secaoDecisao)} <span>/ DECISÃO DE COMPRA</span></span><h2>Como os consumidores reagiram?</h2></div>
              <span className="section-side-caption">Opinião individual de cada consumidor</span>
            </div>
            <div className="decision-overview">
              <div className="decision-stat decision-yes"><span className="decision-dot" /><strong>{decisoes.sim}</strong><span>Comprariam</span></div>
              <div className="decision-stat decision-maybe"><span className="decision-dot" /><strong>{decisoes.talvez}</strong><span>Talvez</span></div>
              <div className="decision-stat decision-no"><span className="decision-dot" /><strong>{decisoes.nao}</strong><span>Não comprariam</span></div>
              <div className="decision-bar" aria-label={`${decisoes.sim} comprariam, ${decisoes.talvez} talvez, ${decisoes.nao} não comprariam`}>
                <span className="bar-yes" style={{ width: larguraDecisao(decisoes.sim) }} />
                <span className="bar-maybe" style={{ width: larguraDecisao(decisoes.talvez) }} />
                <span className="bar-no" style={{ width: larguraDecisao(decisoes.nao) }} />
              </div>
            </div>
          </section>
        )}

        <section className="insights-grid">
          <article className="insight-panel">
            <div className="insight-heading"><span className="insight-icon positive-icon">+</span><div><span>PONTOS POSITIVOS</span><h3>O que agradou</h3></div></div>
            {pontosPositivos.length ? <ul>{pontosPositivos.map((ponto, i) => <li key={i}>{ponto}</li>)}</ul> : <p className="no-insight">Nenhum ponto positivo foi listado.</p>}
          </article>
          <article className="insight-panel">
            <div className="insight-heading"><span className="insight-icon objection-icon">−</span><div><span>OBJEÇÕES</span><h3>O que gerou objeção</h3></div></div>
            {objecoes.length ? <ul>{objecoes.map((objecao, i) => <li key={i}>{objecao}</li>)}</ul> : <p className="no-insight">Nenhuma objeção foi listada.</p>}
          </article>
        </section>

        {pareceres.length > 0 && (
          <section className="especialistas-section">
            <div className="section-heading compact-heading">
              <div><span className="section-index">{num(secaoEspecialistas)} <span>/ ESPECIALISTAS</span></span><h2>O que dizem os especialistas</h2></div>
              <span className="section-side-caption">Cada um avaliou sozinho, na sua área</span>
            </div>
            <div className="pareceres-grid">
              {pareceres.map((parecer, indice) => <ParecerCard key={parecer.especialista_id} mensagem={parecer} indice={indice} />)}
            </div>
          </section>
        )}

        {pesquisa && <MercadoRegiao pesquisa={pesquisa} indiceSecao={num(secaoMercado)} />}

        {financeiro && <ViabilidadeFinanceira financeiro={financeiro} indiceSecao={num(secaoFinanceiro)} />}

        {relatorio && <RelatorioAnalista relatorio={relatorio} indiceSecao={num(secaoRelatorio)} />}

        {temConsumidores && (
          <section className="final-agents-section">
            <div className="section-heading">
              <div><span className="section-index">{num(secaoPerfis)} <span>/ CONSUMIDORES</span></span><h2>A percepção de cada consumidor</h2></div>
            </div>
            <div className="agents-grid result-agents-grid">
              {personas.map((persona) => (
                <AgentCard
                  key={persona.id}
                  persona={persona}
                  mensagens={mensagensDeReferencia.filter((mensagem) => mensagem.persona_id === persona.id)}
                  finalizado
                />
              ))}
            </div>
          </section>
        )}

        {temConsumidores && (
          <section className="full-feed-section">
            <div className="section-heading feed-heading">
              <div><span className="section-index">{num(secaoHistorico)} <span>/ HISTÓRICO</span></span><h2>Opiniões completas dos consumidores</h2></div>
              <span className="feed-count">{mensagensDeReferencia.length} opiniões</span>
            </div>
            <div className="message-list">
              {mensagensDeReferencia.map((mensagem, indice) => (
                <MessageCard key={mensagem.persona_id} mensagem={mensagem} indice={indice} />
              ))}
            </div>
          </section>
        )}

        <div className="result-disclaimer">
          <span>i</span>
          <p><strong>Importante:</strong> {relatorio?.aviso || 'os resultados representam percepções de consumidores e especialistas sintéticos, não uma amostra estatística nem uma previsão de vendas. Use os pontos levantados como hipóteses para testar com clientes reais.'}</p>
        </div>
        <button className="evaluate-button new-evaluation-button" onClick={onNovaAvaliacao}>Avaliar outra ideia</button>
      </main>
    </div>
  )
}
