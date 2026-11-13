"""Agente de contexto (função Python, sem LLM).

Transforma os dados do formulário (e, se houver, a pesquisa de mercado) em um texto
padronizado para as personas e o analista, deixando clara a ORIGEM de cada dado.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.pesquisa import PesquisaMercado

NOMES_FAIXA = {"popular": "Popular", "intermediaria": "Intermediária", "premium": "Premium"}


def _reais(v: float) -> str:
    return f"R$ {v:.2f}".replace(".", ",")


def formatar_pesquisa(pesquisa: "PesquisaMercado") -> str:
    """Seção com a referência de mercado (para as personas e o analista)."""
    linhas = ["## Referência de mercado (pesquisa automática na internet e no mapa — valores aproximados)"]
    if pesquisa.tem_precos():
        linhas.append(f"Preços comparáveis encontrados: {pesquisa.total_precos}.")
        for f in pesquisa.faixas:
            nome = NOMES_FAIXA[f.faixa]
            if f.media is None:
                linhas.append(f"- {nome}: sem preços encontrados")
                continue
            desvio = f" (desvio-padrão {_reais(f.desvio_padrao)})" if f.desvio_padrao is not None else ""
            exemplos = "; ".join(f"{e.estabelecimento}: {e.item} {_reais(e.preco)}" for e in f.exemplos[:3])
            pouco = "" if f.dados_suficientes else " [poucos dados]"
            linhas.append(f"- {nome}: média {_reais(f.media)}{desvio}, de {_reais(f.minimo)} a {_reais(f.maximo)}, "
                          f"{f.quantidade} preço(s){pouco}. Ex.: {exemplos}")
        if pesquisa.posicao:
            linhas.append(f"- Posição do preço da oferta: {pesquisa.posicao.resumo}")
    else:
        linhas.append("- Não foram encontrados preços comparáveis na internet para esta região.")
    if pesquisa.observacao:
        linhas.append(f"- Observação: {pesquisa.observacao}")
    lojas = pesquisa.lojas_regiao
    if lojas and lojas.abrangencia == "cidade":
        if lojas.quantidade:
            nomes = f" (ex.: {', '.join(lojas.nomes[:5])})" if lojas.nomes else ""
            linhas.append(f"- Lojas do mesmo ramo: nenhuma mapeada perto do endereço; na cidade ({lojas.area}) há pelo menos "
                          f"{lojas.quantidade}{nomes}, em outros bairros.")
        # sem nenhuma nem na cidade: não informa número (a observação já explica)
    elif lojas and lojas.quantidade is not None:
        nomes = f" (ex.: {', '.join(lojas.nomes[:5])})" if lojas.nomes else ""
        if lojas.nivel_concorrencia == "indeterminado":
            linhas.append(f"- Lojas do mesmo ramo na região: contagem incompleta{nomes}; o nível de concorrência não pôde ser medido.")
        else:
            linhas.append(f"- Lojas do mesmo ramo num raio de {lojas.raio_metros / 1000:.0f} km: pelo menos {lojas.quantidade}{nomes}. "
                          f"Concorrência: {lojas.nivel_concorrencia}. (O mapa não tem todas as lojas pequenas.)")
    return "\n".join(linhas)


def formatar_entrega(entrega: dict | None) -> str:
    """Linha sobre entrega. Sem a informação, as personas não devem supor nada."""
    from app.models.negocio import MODELOS_ENTREGA

    if not entrega:
        return "- Entrega: sem detalhes neste campo (se o tipo de negócio ou os canais citam delivery ou app, considere que entrega)"
    if not entrega.get("disponivel"):
        return "- Entrega: não faz entrega (atendimento presencial ou retirada no local)"
    partes = [f"faz entrega por {MODELOS_ENTREGA.get(entrega.get('modelo') or 'outro', 'modelo não informado')}"]
    taxa = entrega.get("taxa")
    if taxa is not None:
        partes.append("entrega grátis" if taxa == 0 else f"taxa de entrega R$ {taxa:.2f}")
    if entrega.get("prazo"):
        partes.append(f"prazo: {entrega['prazo']}")
    if entrega.get("area"):
        partes.append(f"área atendida: {entrega['area']}")
    if entrega.get("garantias"):
        partes.append(f"como garante a entrega: {entrega['garantias']}")
    return "- Entrega: " + "; ".join(partes)


def formatar_negocio(negocio: dict, pesquisa: "PesquisaMercado | None" = None) -> str:
    linhas = [
        "## Oferta a avaliar (dados informados pelo empreendedor)",
        f"- Tipo de negócio: {negocio.get('tipo', '-')}",
        f"- Localização: {negocio.get('localizacao', '-')}",
        f"- Produto principal: {negocio.get('produto', '-')}",
        f"- Preço: R$ {negocio.get('preco', 0):.2f}",
        f"- Público pretendido: {negocio.get('publico', '-')}",
        f"- Divulgação e canais: {negocio.get('divulgacao', '-')}",
        formatar_entrega(negocio.get("entrega")),
    ]
    concorrentes = negocio.get("concorrentes") or []
    if concorrentes:
        linhas.append("\n## Concorrentes (cadastrados manualmente pelo empreendedor)")
        for c in concorrentes:
            linhas.append(f"- {c.get('nome', '-')}: R$ {c.get('preco', 0):.2f} — {c.get('observacao', '')}")
    else:
        linhas.append("\n## Concorrentes\n- Nenhum concorrente foi informado pelo empreendedor.")
    if pesquisa is not None and pesquisa.tem_dados():
        linhas.append("\n" + formatar_pesquisa(pesquisa))
    return "\n".join(linhas)
