"""Agente analista: junta as opiniões dos consumidores e os pareceres dos especialistas,
DESCARTA o que foi extrapolado e escreve o relatório final para o empreendedor.

Divisão de trabalho:
    - NÚMEROS (interesse médio, decisões, preço máximo, notas dos especialistas): calculados pelo código,
      em `calcular_indicadores`. A IA recebe esses números prontos e não pode inventar outros.
    - TEXTO (resumo, elogios, objeções, recomendações, experimentos, opiniões descartadas): escrito pela IA,
      com base SOMENTE no que os agentes disseram e que resistiu ao filtro.
"""

import logging
import time
from statistics import mean, median

from app.agents.contexto import formatar_negocio
from app.services.financeiro import calcular_financeiro, formatar_financeiro
from app.llm.base import LLMProvider
from app.models.schemas import (
    AnaliseDebate,
    IndicadorPersona,
    Indicadores,
    MensagemDebate,
    MensagemParecer,
    Relatorio,
    ResultadoSimulacao,
)

log = logging.getLogger(__name__)

SISTEMA_ANALISTA = """Você é o analista-chefe que entrega o relatório final a um pequeno empreendedor.
Você recebe: os dados do negócio, os FATOS CALCULADOS pelo sistema, as opiniões individuais de consumidores sintéticos,
os pareceres individuais de especialistas e indicadores já calculados. Ninguém conversou com ninguém: cada um opinou sozinho.

Seu trabalho tem 3 etapas:
1. COMPILAR: junte o que consumidores e especialistas disseram, agrupando os pontos repetidos.
2. FILTRAR (seja crítico com as opiniões, não com o negócio): DESCARTE e liste em "opinioes_descartadas" toda opinião que:
   - contradiz os fatos calculados (ex.: chamar de caro um preço que está abaixo da média dos concorrentes ou da região;
     falar em prejuízo quando a margem é positiva);
   - exige provas que um negócio novo não tem (fotos, certificados, avaliações, "qualidade comprovada");
   - faz afirmação técnica sem base nos dados (ex.: como um alimento esquenta no micro-ondas);
   - critica algo que FOI informado como se não tivesse sido (ex.: "não tem entrega" quando os canais citam delivery);
   - inventa números ou características que ninguém informou.
   Formato: "Quem: o que disse — por que foi descartada". Não use as opiniões descartadas no resto do relatório.
3. RELATAR: escreva o relatório só com o que resistiu ao filtro. Seja equilibrado: nem duro por padrão, nem otimista sem base.
   Dê mais peso a um ponto quando ele aparece em consumidores E especialistas.

Regras do relatório:
- Cada elogio e objeção indica entre parênteses quem disse (ex.: "(Econômico, Especialista em Marketing)").
- Os números já estão calculados: use-os como estão. Não recalcule nem invente números, percentuais ou estatísticas.
- Preço: use os fatos calculados e a "Avaliação do preço" dos indicadores. Se o preço está abaixo da média ou a maioria pagaria
  o preço cobrado, NÃO diga que é caro nem recomende baixar.
- Se houver referência de mercado, compare o preço com as faixas (popular, intermediária, premium) e com a concorrência na região,
  deixando claro que são valores aproximados da internet.
- Se houver "Viabilidade financeira", use os números como estão: diga se o preço cobre o custo, se o lucro bate com o esperado,
  quanto lucraria nos cenários de clientes por dia e, se houver investimento, em quanto tempo se paga.
  NÃO fale em ponto de equilíbrio. Lembre que a conta não inclui impostos nem salários de funcionários e que negócios novos
  costumam levar meses para lucrar. Sem essa seção, não fale de lucro.
- Se a oferta tiver entrega, avalie se o modelo informado é confiável para este produto.
- Recomendações: concretas, baratas e viáveis para um pequeno negócio DESTE ramo, cada uma ligada a um ponto do relatório.
  Aproveite as boas recomendações dos especialistas e as sugestões dos consumidores.
- Experimentos: testes rápidos com clientes reais, dizendo o que fazer e o que medir, ADEQUADOS A ESTE RAMO.
  Amostra grátis, degustação e brinde NÃO são o padrão (no máximo UM, e só se fizer sentido no ramo). Prefira testes em que o
  cliente paga: combo de lançamento, plano semanal, cupom para a 2ª compra, pacote, pré-venda, programa de indicação,
  comparar duas versões do anúncio ou do cardápio. Diga o que medir (vendas, recompra em X dias, ticket médio...).
- Linguagem responsável: fale em "interesse simulado" e "hipóteses a validar". NUNCA fale em chance de sucesso, garantia ou previsão de vendas.
- Português do Brasil, direto, para quem não é especialista."""


# ---------- Filtro pelo CÓDIGO (antes da IA): opiniões extrapoladas que sempre são descartadas ----------
# Só nas opiniões dos consumidores: nos especialistas, recomendar "fotos reais" na divulgação é conselho legítimo.
PADROES_EXTRAPOLADOS = [
    (r"\bprovas?\b|\bprovar (a|que|qualidade)|comprov|evid[eê]nci|garantia de qualidade",
     "exige prova de qualidade que um negócio novo ainda não tem"),
    (r"\bfotos?\b|imagens? (reais|do produto)", "cobra fotos, mas a avaliação é feita sobre uma descrição em texto"),
    (r"certifica|\bselos?\b|\blaudos?\b", "exige certificação que não foi pedida para este ramo"),
    (r"avalia[cç](ão|ões) (online|de clientes|no ifood|na internet)|\breviews?\b|depoimentos",
     "exige avaliações de clientes que um negócio novo ainda não tem"),
]
PADRAO_CARO = r"\bcaro\b|pre[cç]o (alto|elevado|salgado)|pesa no bolso"
ABAIXO_PARA_FILTRAR_CARO = 0.85  # preço 15%+ abaixo da referência: chamar de caro contradiz os fatos


def _referencia_de_preco(negocio: dict, pesquisa) -> float | None:
    """Menor referência entre a média dos concorrentes informados e a média do mercado (a mais conservadora)."""
    refs = []
    precos_conc = [float(c.get("preco") or 0) for c in (negocio.get("concorrentes") or []) if c.get("preco")]
    if precos_conc:
        refs.append(sum(precos_conc) / len(precos_conc))
    if pesquisa is not None and getattr(pesquisa, "media_geral", None):
        refs.append(pesquisa.media_geral)
    return min(refs) if refs else None


def _motivo(texto: str, preco_abaixo: bool) -> str | None:
    import re

    t = texto.lower()
    for padrao, motivo in PADROES_EXTRAPOLADOS:
        if re.search(padrao, t):
            return motivo
    if preco_abaixo and re.search(PADRAO_CARO, t):
        return "chama o preço de caro, mas ele está bem abaixo da média dos concorrentes/região (fato calculado)"
    return None


def filtrar_extrapoladas(resultado: ResultadoSimulacao, negocio: dict) -> tuple[ResultadoSimulacao, list[str]]:
    """Devolve (cópia do resultado SEM os trechos extrapolados dos consumidores, lista do que foi descartado).
    A cópia é o que o analista lê; o resultado original (e o feed) não muda."""
    import re

    preco = float(negocio.get("preco") or 0)
    ref = _referencia_de_preco(negocio, resultado.pesquisa)
    preco_abaixo = bool(ref and preco and preco <= ref * ABAIXO_PARA_FILTRAR_CARO)
    descartadas: list[str] = []
    limpas = []
    for m in resultado.mensagens:
        o = m.opiniao
        nome = m.persona_nome.replace("Consumidor ", "")

        def manter(texto: str) -> bool:
            motivo = _motivo(texto, preco_abaixo)
            if motivo:
                descartadas.append(f"{nome}: \"{texto.strip()}\" — {motivo}")
            return motivo is None

        frases = [f for f in re.split(r"(?<=[.!?])\s+", o.fala) if f.strip()]
        nova = o.model_copy(update={
            "fala": " ".join(f for f in frases if manter(f)) or "(sem argumentos válidos)",
            "objecoes": [x for x in o.objecoes if manter(x)],
            "o_que_mudaria": o.o_que_mudaria if not o.o_que_mudaria or manter(o.o_que_mudaria) else "",
        })
        limpas.append(m.model_copy(update={"opiniao": nova}))
    return resultado.model_copy(update={"mensagens": limpas}), list(dict.fromkeys(descartadas))


TOLERANCIA_PRECO = 0.97  # 118,30 para um preço de 119 conta como "pagaria" (a IA costuma tirar uns centavos)
MARGEM_PARA_SUBIR = 1.10  # mediana do máximo 10% acima do preço = há espaço para subir


def aceita_preco(preco_maximo: float | None, compraria: str, preco_ofertado: float) -> bool:
    """A persona pagaria o preço cobrado? Sim se disse que compraria ou se o máximo dela chega ao preço."""
    if compraria == "sim":
        return True
    return preco_maximo is not None and preco_maximo >= preco_ofertado * TOLERANCIA_PRECO


def avaliar_preco(por_persona: list[IndicadorPersona], preco_ofertado: float) -> tuple[int, str, float | None, float | None]:
    """Devolve (quantos aceitam, avaliação, preço de referência, mediana do máximo).

    Se a MAIORIA pagaria o preço cobrado, ele é o preço de referência ("preço ideal"): não faz sentido
    mostrar uma média alguns centavos abaixo. Se a maioria não pagaria, mostra a mediana do que pagariam."""
    if not por_persona or preco_ofertado <= 0:
        return 0, "sem_dados", None, None
    aceitam = sum(aceita_preco(p.preco_maximo, p.compraria_r2, preco_ofertado) for p in por_persona)
    precos = [p.preco_maximo for p in por_persona if p.preco_maximo is not None]
    mediana = round(median(precos), 2) if precos else None
    if aceitam > len(por_persona) / 2:
        if mediana is not None and mediana >= preco_ofertado * MARGEM_PARA_SUBIR:
            return aceitam, "espaco_para_subir", preco_ofertado, mediana
        return aceitam, "ideal", preco_ofertado, mediana
    if mediana is None:
        return aceitam, "sem_dados", None, None
    return aceitam, "acima_do_aceito", mediana, mediana


def calcular_indicadores(resultado: ResultadoSimulacao, preco_ofertado: float) -> Indicadores:
    por_persona = [
        IndicadorPersona(
            persona_id=m2.persona_id,
            persona_nome=m2.persona_nome,
            interesse_r1=m1.opiniao.interesse,
            interesse_r2=m2.opiniao.interesse,
            compraria_r1=m1.opiniao.compraria,
            compraria_r2=m2.opiniao.compraria,
            mudou=mudou,
            preco_maximo=m2.opiniao.preco_maximo,
        )
        for m1, m2, mudou in resultado.comparar_rodadas()
    ]
    r1 = resultado.da_rodada(1)
    r2 = resultado.da_rodada(2) or r1  # sem debate (padrão agora), a opinião final é a única que existe
    precos = [p.preco_maximo for p in por_persona if p.preco_maximo is not None]
    aceitam, avaliacao, referencia, mediana = avaliar_preco(por_persona, preco_ofertado)
    notas = [m.parecer.nota for m in resultado.pareceres]
    return Indicadores(
        preco_ofertado=preco_ofertado,
        nota_media_especialistas=round(mean(notas), 1) if notas else None,
        vereditos_especialistas={v: sum(m.parecer.veredito == v for m in resultado.pareceres)
                                 for v in ("favoravel", "favoravel_com_ajustes", "desfavoravel")} if notas else {},
        interesse_medio_r1=round(mean(m.opiniao.interesse for m in r1), 1) if r1 else 0,
        interesse_medio_r2=round(mean(m.opiniao.interesse for m in r2), 1) if r2 else 0,
        decisoes_r2={d: sum(m.opiniao.compraria == d for m in r2) for d in ("sim", "talvez", "nao")},
        preco_maximo_medio=round(mean(precos), 2) if precos else None,
        preco_maximo_mediano=mediana,
        aceitam_preco=aceitam,
        avaliacao_preco=avaliacao,
        preco_referencia=referencia,
        mudaram_de_posicao=sum(p.mudou for p in por_persona),
        por_persona=por_persona,
    )


def _transcrever(m: MensagemDebate) -> str:
    o = m.opiniao
    linhas = [
        f"### {m.persona_nome} (interesse {o.interesse}/10, compraria: {o.compraria}"
        + (f", pagaria até R$ {o.preco_maximo:.2f}" if o.preco_maximo is not None else "") + ")",
        f'Fala: "{o.fala}"',
    ]
    if o.pontos_positivos:
        linhas.append("Gostou de: " + "; ".join(o.pontos_positivos))
    if o.objecoes:
        linhas.append("Objeções: " + "; ".join(o.objecoes))
    if o.o_que_mudaria:
        linhas.append("Sugestão ao dono: " + o.o_que_mudaria)
    return "\n".join(linhas)


VEREDITOS = {"favoravel": "favorável", "favoravel_com_ajustes": "favorável com ajustes", "desfavoravel": "desfavorável"}
PRECO_ESPECIALISTA = {"baixo": "baixo", "adequado": "adequado", "alto": "alto"}


def _transcrever_parecer(m: MensagemParecer) -> str:
    p = m.parecer
    linhas = [
        f"### {m.especialista_nome} — {m.area} (nota {p.nota}/10, {VEREDITOS[p.veredito]}, preço {PRECO_ESPECIALISTA[p.avaliacao_preco]}"
        + (f", sugere R$ {p.preco_sugerido:.2f}" if p.preco_sugerido is not None else "") + ")",
        f'Resumo: "{p.resumo}"',
    ]
    if p.pontos_fortes:
        linhas.append("Pontos fortes: " + "; ".join(p.pontos_fortes))
    if p.riscos:
        linhas.append("Riscos: " + "; ".join(p.riscos))
    if p.recomendacoes:
        linhas.append("Recomendações: " + "; ".join(p.recomendacoes))
    return "\n".join(linhas)


def _formatar_indicadores(ind: Indicadores) -> str:
    linhas = [f"- Preço ofertado: R$ {ind.preco_ofertado:.2f}"]
    if ind.por_persona:
        linhas += [
            f"- Interesse médio dos consumidores: {ind.interesse_medio_r2} (escala 0 a 10)",
            f"- Decisões dos consumidores: {ind.decisoes_r2['sim']} sim, {ind.decisoes_r2['talvez']} talvez, {ind.decisoes_r2['nao']} não",
        ]
    if ind.nota_media_especialistas is not None:
        v = ind.vereditos_especialistas
        linhas.append(f"- Nota média dos especialistas: {ind.nota_media_especialistas}/10 "
                      f"({v.get('favoravel', 0)} favoráveis, {v.get('favoravel_com_ajustes', 0)} com ajustes, "
                      f"{v.get('desfavoravel', 0)} desfavoráveis)")
    if ind.preco_maximo_medio is not None:
        linhas.append(f"- Preço máximo médio que pagariam: R$ {ind.preco_maximo_medio:.2f}")
    total = len(ind.por_persona)
    textos_preco = {
        "ideal": f"a maioria ({ind.aceitam_preco} de {total}) pagaria o preço cobrado: trate o preço como adequado",
        "espaco_para_subir": (f"a maioria ({ind.aceitam_preco} de {total}) pagaria o preço cobrado e a mediana do máximo "
                              f"(R$ {ind.preco_maximo_mediano or 0:.2f}) sugere espaço para subir com cuidado"),
        "acima_do_aceito": (f"só {ind.aceitam_preco} de {total} pagariam o preço cobrado; a mediana do que pagariam é "
                            f"R$ {ind.preco_referencia or 0:.2f}"),
        "sem_dados": "sem dados suficientes sobre preço",
    }
    if ind.por_persona:
        linhas.append(f"- Avaliação do preço pelos consumidores: {textos_preco[ind.avaliacao_preco]}")
    return "\n".join(linhas)


def montar_pedido(negocio: dict, resultado: ResultadoSimulacao, indicadores: Indicadores, financeiro=None) -> str:
    consumidores = "\n\n".join(_transcrever(m) for m in resultado.da_rodada(1)) or "(nenhum consumidor participou)"
    especialistas = "\n\n".join(_transcrever_parecer(m) for m in resultado.pareceres) or "(nenhum especialista participou)"
    return (
        f"{formatar_negocio(negocio, resultado.pesquisa)}\n\n"
        f"# Opiniões individuais dos consumidores sintéticos\n{consumidores}\n\n"
        f"# Pareceres individuais dos especialistas\n{especialistas}\n\n"
        f"# Indicadores (já calculados, use como estão)\n{_formatar_indicadores(indicadores)}\n\n"
        + (f"# Viabilidade financeira (já calculada, use como está)\n{formatar_financeiro(financeiro)}\n\n" if financeiro else "")
        +
        "Escreva o relatório para o empreendedor."
    )


async def analisar(provider: LLMProvider | None, negocio: dict, resultado: ResultadoSimulacao) -> Relatorio:
    """Gera o relatório. Se a IA falhar (ou não estiver configurada), devolve só os indicadores."""
    indicadores = calcular_indicadores(resultado, float(negocio.get("preco", 0)))
    relatorio = Relatorio(indicadores=indicadores,
                          financeiro=calcular_financeiro(negocio, indicadores, resultado.pesquisa))
    if provider is None:
        relatorio.erro_analise = "Agente analista não configurado (defina LLM_MODEL_ANALISTA no .env)."
        return relatorio
    inicio, tokens_antes = time.perf_counter(), provider.total_tokens()
    try:
        # O código tira antes os trechos claramente extrapolados; a IA ainda pode descartar outros
        filtrado, descartadas_codigo = filtrar_extrapoladas(resultado, negocio)
        pedido = montar_pedido(negocio, filtrado, indicadores, relatorio.financeiro)
        if descartadas_codigo:
            pedido += ("\n\n(Já foram retirados pelo sistema, por serem extrapolados, e NÃO devem ser usados: "
                       + "; ".join(descartadas_codigo) + ")")
        analise, origem = await provider.gerar_com_origem(
            SISTEMA_ANALISTA, [{"role": "user", "content": pedido}], AnaliseDebate
        )
        analise.opinioes_descartadas = list(dict.fromkeys(descartadas_codigo + analise.opinioes_descartadas))
        relatorio.analise, relatorio.origem_analise = analise, origem
    except Exception as erro:  # noqa: BLE001 — o relatório sem texto ainda é útil
        log.exception("Agente analista falhou")
        relatorio.erro_analise = f"Não foi possível gerar a análise em texto ({type(erro).__name__}). Os números continuam válidos."
    relatorio.tokens_usados = provider.total_tokens() - tokens_antes
    relatorio.duracao_segundos = round(time.perf_counter() - inicio, 1)
    return relatorio
