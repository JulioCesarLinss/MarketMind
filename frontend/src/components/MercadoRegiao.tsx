import { NOMES_FAIXA, type PesquisaMercado } from '../types'

interface MercadoRegiaoProps {
  pesquisa: PesquisaMercado
  indiceSecao: string
}

function reais(valor: number): string {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

const NIVEL: Record<string, { rotulo: string; classe: string }> = {
  'nenhum concorrente mapeado': { rotulo: 'Sem concorrente mapeado', classe: 'nivel-baixo' },
  baixa: { rotulo: 'Concorrência baixa', classe: 'nivel-baixo' },
  media: { rotulo: 'Concorrência média', classe: 'nivel-medio' },
  alta: { rotulo: 'Concorrência alta', classe: 'nivel-alto' },
  indeterminado: { rotulo: 'Não foi possível medir', classe: 'nivel-indeterminado' },
}

export default function MercadoRegiao({ pesquisa, indiceSecao }: MercadoRegiaoProps) {
  const faixasComDados = pesquisa.faixas.filter((f) => f.media !== null && f.minimo !== null && f.maximo !== null)
  const precoUsuario = pesquisa.posicao?.preco_usuario ?? null
  const lojas = pesquisa.lojas_regiao
  const nivel = NIVEL[lojas?.nivel_concorrencia ?? 'indeterminado'] ?? NIVEL.indeterminado

  // Escala da régua: do menor ao maior valor (incluindo o preço do usuário), com folga
  const valores = faixasComDados.flatMap((f) => [f.minimo as number, f.maximo as number])
  if (precoUsuario !== null) valores.push(precoUsuario)
  const menor = valores.length ? Math.min(...valores) : 0
  const maior = valores.length ? Math.max(...valores) : 1
  const folga = (maior - menor) * 0.08 || 1
  const inicio = Math.max(0, menor - folga)
  const fim = maior + folga
  const pct = (v: number) => `${((v - inicio) / (fim - inicio)) * 100}%`

  return (
    <section className="market-section">
      <div className="section-heading compact-heading">
        <div><span className="section-index">{indiceSecao} <span>/ MERCADO</span></span><h2>Como seu preço se compara na região</h2></div>
        <span className="section-side-caption">Pesquisa automática na internet e no mapa</span>
      </div>

      <div className="market-top">
        <article className="market-card market-position">
          <span>SEU PREÇO NO MERCADO</span>
          {pesquisa.total_precos > 0 && pesquisa.media_geral !== null ? (
            <>
              <strong>{precoUsuario !== null ? reais(precoUsuario) : '—'} <small>vs. média {reais(pesquisa.media_geral)}</small></strong>
              <p>{pesquisa.posicao?.resumo}</p>
              <p className="market-meta">
                {pesquisa.total_precos} preços confirmados
                {pesquisa.desvio_padrao_geral !== null && <> · desvio-padrão {reais(pesquisa.desvio_padrao_geral)}</>}
              </p>
            </>
          ) : (
            <p className="market-empty">{pesquisa.erro || 'Nenhum preço comparável foi encontrado na internet para esta região.'}</p>
          )}
        </article>

        <article className="market-card">
          <span>LOJAS DO MESMO RAMO NA REGIÃO</span>
          {lojas && lojas.quantidade !== null && lojas.nivel_concorrencia !== 'indeterminado' ? (
            <strong>{lojas.quantidade}<small> no mínimo · raio de {(lojas.raio_metros / 1000).toLocaleString('pt-BR')} km</small></strong>
          ) : (
            <strong className="market-unknown">—</strong>
          )}
          <span className={`nivel-pill ${nivel.classe}`}>{nivel.rotulo}</span>
          {lojas?.nomes && lojas.nomes.length > 0 && <p className="market-meta">Ex.: {lojas.nomes.slice(0, 4).join(', ')}</p>}
          <p className="market-meta">{lojas?.erro || lojas?.observacao}</p>
        </article>
      </div>

      {faixasComDados.length > 0 && (
        <>
          <div className="price-ruler" aria-label="Faixas de preço do mercado e o preço da oferta">
            <div className="ruler-body">
            {pesquisa.faixas.map((f) => (
              <div className="ruler-row" key={f.faixa}>
                <span className="ruler-label">{NOMES_FAIXA[f.faixa]}</span>
                <div className="ruler-track">
                  {f.media !== null && f.minimo !== null && f.maximo !== null ? (
                    <>
                      <span className={`ruler-range faixa-${f.faixa}`} style={{ left: pct(f.minimo), width: `calc(${pct(f.maximo)} - ${pct(f.minimo)} + 4px)` }} />
                      <span className={`ruler-mean faixa-${f.faixa}`} style={{ left: pct(f.media) }} title={`Média ${reais(f.media)}`} />
                    </>
                  ) : (
                    <span className="ruler-nodata">sem dados</span>
                  )}
                </div>
              </div>
            ))}
            {precoUsuario !== null && (
              <div className="ruler-user" style={{ left: `calc(84px + (100% - 84px) * ${(precoUsuario - inicio) / (fim - inicio)})` }}>
                <span>Seu preço {reais(precoUsuario)}</span>
              </div>
            )}
            </div>
          </div>

          <div className="tiers-grid">
            {pesquisa.faixas.map((f) => (
              <article className={`tier-card faixa-${f.faixa}`} key={f.faixa}>
                <span className="tier-name">{NOMES_FAIXA[f.faixa].toUpperCase()}</span>
                {f.media !== null ? (
                  <>
                    <strong>{reais(f.media)}</strong>
                    <p className="tier-stats">
                      {f.desvio_padrao !== null && <>± {reais(f.desvio_padrao)} · </>}
                      {f.minimo !== null && f.maximo !== null && <>{reais(f.minimo)} a {reais(f.maximo)} · </>}
                      {f.quantidade} {f.quantidade === 1 ? 'preço' : 'preços'}
                    </p>
                    {!f.dados_suficientes && <p className="tier-warning">Poucos dados nesta faixa</p>}
                    <ul>
                      {f.exemplos.slice(0, 3).map((e, i) => (
                        <li key={i}><span>{e.estabelecimento}</span> {e.item} — <strong>{reais(e.preco)}</strong></li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p className="tier-warning">Nenhum preço encontrado nesta faixa</p>
                )}
              </article>
            ))}
          </div>
        </>
      )}

      {pesquisa.fontes.length > 0 && (
        <div className="market-sources">
          <span>FONTES</span>
          <ul>
            {pesquisa.fontes.map((f) => (
              <li key={f.url}><a href={f.url} target="_blank" rel="noopener noreferrer">{f.titulo || f.url}</a></li>
            ))}
          </ul>
        </div>
      )}
      <p className="market-disclaimer">{pesquisa.aviso}</p>
    </section>
  )
}
