"""Calculadora financeira (sem IA): contas determinísticas sobre os custos informados.

Responde às perguntas do pequeno empreendedor:
    - O preço cobre o custo? Quanto sobra por venda? Bate com o lucro que eu espero?
    - "Com 10 clientes por dia, quanto lucro por dia e por mês?"
    - Se informei o investimento: em quanto tempo o negócio se paga?

Fórmulas:
    receita líquida por venda = preço × (1 − taxa da plataforma)
    lucro por venda           = receita líquida − custo de produção por unidade   (margem de contribuição)
    margem                    = lucro por venda ÷ preço
    lucro do mês              = vendas no mês × lucro por venda − custo fixo mensal
    tempo para se pagar       = investimento ÷ lucro do mês
    preço para o lucro esperado = custo ÷ (1 − taxa − lucro esperado)

Premissa simples (sempre mostrada): 1 cliente = 1 venda; mês com DIAS_POR_MES dias de funcionamento.
"""

import math

from app.models.schemas import CenarioPreco, CenarioVendas, Financeiro, Indicadores

DIAS_POR_MES = 26  # segunda a sábado
OPCOES_CLIENTES_DIA = [5, 10, 15, 20, 30, 50, 80, 100, 150, 200, 300, 500]
NAO_CONSIDERADO = [
    "Impostos (ex.: Simples Nacional, MEI)",
    "Pagamento de funcionários (salários e encargos)",
    "Pró-labore (o seu salário)",
    "Perdas, desperdício e trocas",
    "Meses iniciais com menos vendas (o movimento costuma crescer aos poucos)",
    "Sazonalidade (meses fortes e fracos)",
]


def _reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def texto_meses(meses: float) -> str:
    """8.2 → 'cerca de 9 meses' · 30 → 'cerca de 2 anos e 6 meses' (arredonda para cima: é melhor não prometer antes)."""
    m = math.ceil(meses)
    if m <= 1:
        return "cerca de 1 mês"
    anos, resto = divmod(m, 12)
    if anos == 0:
        return f"cerca de {m} meses"
    ano_txt = "1 ano" if anos == 1 else f"{anos} anos"
    return f"cerca de {ano_txt}" + (f" e {resto} {'mês' if resto == 1 else 'meses'}" if resto else "")


def _resultado(valor: float) -> str:
    return f"lucro de {_reais(valor)}" if valor >= 0 else f"prejuízo de {_reais(-valor)}"


def lucro_por_venda(preco: float, custo_unitario: float, taxa_pct: float) -> float:
    return preco * (1 - taxa_pct / 100) - custo_unitario


def ponto_equilibrio_mes(custo_fixo: float, lucro_venda: float) -> int | None:
    """Vendas por mês para empatar. None = impossível (cada venda não dá lucro).
    Uso interno: não aparece no relatório, só serve para escolher cenários com prejuízo e com lucro."""
    if lucro_venda <= 0:
        return None
    return math.ceil(custo_fixo / lucro_venda) if custo_fixo > 0 else 0


def preco_para_margem(custo_unitario: float, taxa_pct: float, margem_pct: float) -> float | None:
    """Preço que deixa `margem_pct`% do preço como lucro por venda. None se a taxa + margem ≥ 100%."""
    sobra = 1 - taxa_pct / 100 - margem_pct / 100
    if sobra <= 0:
        return None
    return round(custo_unitario / sobra, 2)


def cenario(clientes_dia: int, lucro_venda: float, preco: float, custo_fixo: float,
            investimento: float | None) -> CenarioVendas:
    vendas_mes = clientes_dia * DIAS_POR_MES
    lucro_mes = round(vendas_mes * lucro_venda - custo_fixo, 2)
    meses = round(investimento / lucro_mes, 1) if investimento and lucro_mes > 0 else None
    return CenarioVendas(
        clientes_dia=clientes_dia,
        vendas_mes=vendas_mes,
        faturamento_mes=round(vendas_mes * preco, 2),
        lucro_dia=round(lucro_mes / DIAS_POR_MES, 2),
        lucro_mes=lucro_mes,
        meses_para_pagar=meses,
    )


def escolher_clientes(equilibrio_dia: int | None) -> list[int]:
    """4 cenários de clientes por dia em números redondos: 2 que ainda dão prejuízo e 2 que dão lucro
    (escolhidos em volta do ponto de equilíbrio, que não é mostrado)."""
    if not equilibrio_dia:
        return [5, 10, 20, 30]
    abaixo = [c for c in OPCOES_CLIENTES_DIA if c < equilibrio_dia][-2:]
    acima = [c for c in OPCOES_CLIENTES_DIA if c > equilibrio_dia][:2]
    return abaixo + acima or [equilibrio_dia * 2]


def _aceitam(preco: float, indicadores: Indicadores | None) -> int | None:
    """Quantos agentes pagariam este preço (pelo preço máximo que cada um declarou)."""
    if not indicadores:
        return None
    com_preco = [p for p in indicadores.por_persona if p.preco_maximo is not None]
    if not com_preco:
        return None
    return sum(p.preco_maximo >= preco * 0.97 for p in com_preco)


def calcular_financeiro(negocio: dict, indicadores: Indicadores | None = None, pesquisa=None) -> Financeiro | None:
    """Relatório financeiro. None se o usuário não informou os custos (a seção é opcional)."""
    custos = negocio.get("custos")
    preco = float(negocio.get("preco") or 0)
    if not custos or preco <= 0:
        return None
    custo_unit = float(custos.get("custo_variavel_unitario") or 0)
    custo_fixo = float(custos.get("custo_fixo_mensal") or 0)
    taxa = float(custos.get("taxa_plataforma_pct") or 0)
    meta = custos.get("lucro_esperado_pct")
    investimento = custos.get("investimento_inicial") or None

    receita = round(preco * (1 - taxa / 100), 2)
    lucro_venda = round(lucro_por_venda(preco, custo_unit, taxa), 2)
    margem = round(lucro_venda / preco * 100, 1)
    eq_mes = ponto_equilibrio_mes(custo_fixo, lucro_venda)
    eq_dia = math.ceil(eq_mes / DIAS_POR_MES) if eq_mes else (0 if eq_mes == 0 else None)
    preco_meta = preco_para_margem(custo_unit, taxa, meta) if meta is not None else None

    # O preço faz sentido?
    if lucro_venda <= 0:
        avaliacao = "prejuizo"
        resumo = (f"Cada venda dá prejuízo: depois da taxa, sobram {_reais(receita)} e a produção custa "
                  f"{_reais(custo_unit)}. O preço precisa subir ou o custo precisa cair.")
    elif meta is None:
        avaliacao = "sem_meta"
        resumo = f"Cada venda deixa {_reais(lucro_venda)} de lucro ({margem:.0f}% do preço)."
    elif margem >= meta:
        avaliacao = "dentro_do_esperado"
        resumo = f"O preço faz sentido: cada venda deixa {_reais(lucro_venda)} ({margem:.0f}%), acima dos {meta:.0f}% que você espera."
    else:
        avaliacao = "abaixo_do_esperado"
        resumo = (f"Cada venda deixa {_reais(lucro_venda)} ({margem:.0f}%), abaixo dos {meta:.0f}% que você espera"
                  + (f": para chegar lá, o preço seria {_reais(preco_meta)}." if preco_meta else "."))

    # Cenários de clientes por dia (+ a linha do ponto de equilíbrio)
    cenarios: list[CenarioVendas] = []
    if lucro_venda > 0:
        for c in escolher_clientes(eq_dia):
            cenarios.append(cenario(c, lucro_venda, preco, custo_fixo, investimento))

    # Outros preços: o que os agentes pagariam e o mercado da região
    cenarios_preco = [CenarioPreco(rotulo="Seu preço", preco=preco, lucro_por_venda=lucro_venda, margem_pct=margem,
                                   aceitam=_aceitam(preco, indicadores))]
    alternativas: list[tuple[str, float | None]] = []
    if indicadores and indicadores.avaliacao_preco == "acima_do_aceito":
        alternativas.append(("O que os agentes pagariam", indicadores.preco_referencia))
    if preco_meta and avaliacao == "abaixo_do_esperado":
        alternativas.append((f"Preço para {meta:.0f}% de lucro", preco_meta))
    if pesquisa is not None and getattr(pesquisa, "media_geral", None):
        alternativas.append(("Média do mercado na região", pesquisa.media_geral))
        for f in pesquisa.faixas:
            if f.faixa == "premium" and f.media:
                alternativas.append(("Faixa premium do mercado", f.media))
    for rotulo, p in alternativas:
        if not p or abs(p - preco) < 0.01:
            continue
        lv = round(lucro_por_venda(p, custo_unit, taxa), 2)
        cenarios_preco.append(CenarioPreco(rotulo=rotulo, preco=round(p, 2), lucro_por_venda=lv,
                                           margem_pct=round(lv / p * 100, 1), aceitam=_aceitam(p, indicadores)))

    # Alertas que dependem dos dados informados
    alertas: list[str] = []
    entrega = negocio.get("entrega") or {}
    if entrega.get("disponivel") and entrega.get("modelo") == "app_delivery" and taxa == 0:
        alertas.append("Você vende por app de delivery, mas a taxa da plataforma está 0%: esses apps costumam cobrar de 12% a 30% por pedido.")
    if entrega.get("disponivel") and entrega.get("modelo") in ("proprio", "entregador_parceiro"):
        alertas.append("Entrega própria ou por motoboy: inclua o custo da entrega no custo de produção por unidade.")
    if custo_fixo == 0:
        alertas.append("Custo fixo mensal igual a zero: aluguel, energia e internet costumam existir mesmo em negócios pequenos.")
    if investimento and cenarios and not any(c.meses_para_pagar and c.meses_para_pagar <= 24 for c in cenarios):
        alertas.append("Em nenhum dos cenários o investimento se paga em até 2 anos: reveja preço, custos ou o tamanho do investimento.")

    return Financeiro(
        preco=preco, custo_unitario=custo_unit, taxa_plataforma_pct=taxa, custo_fixo_mensal=custo_fixo,
        receita_liquida_venda=receita, lucro_por_venda=lucro_venda, margem_pct=margem,
        lucro_esperado_pct=meta, preco_para_lucro_esperado=preco_meta,
        avaliacao_preco=avaliacao, resumo_preco=resumo,
        dias_por_mes=DIAS_POR_MES,
        investimento_inicial=investimento, cenarios=cenarios, cenarios_preco=cenarios_preco,
        alertas=alertas, nao_considerado=NAO_CONSIDERADO,
    )


def formatar_financeiro(f: Financeiro) -> str:
    """Texto para o analista (números prontos, ele não recalcula)."""
    linhas = [
        f"- Preço {_reais(f.preco)}; custo de produção {_reais(f.custo_unitario)}; taxa da plataforma {f.taxa_plataforma_pct:.0f}%; "
        f"custo fixo {_reais(f.custo_fixo_mensal)}/mês",
        f"- {f.resumo_preco}",
    ]
    for c in f.cenarios:
        pagar = f", investimento se paga em {texto_meses(c.meses_para_pagar)}" if c.meses_para_pagar else ""
        linhas.append(f"- {c.clientes_dia} clientes/dia: {_resultado(c.lucro_dia)}/dia e {_resultado(c.lucro_mes)}/mês{pagar}")
    if f.investimento_inicial:
        linhas.append(f"- Investimento inicial informado: {_reais(f.investimento_inicial)}")
    linhas += [f"- Alerta: {a}" for a in f.alertas]
    linhas.append(f"- {f.aviso_custos}")
    return "\n".join(linhas)
