"""Agente analista: lê o debate inteiro e escreve o relatório para o empreendedor.

Divisão de trabalho:
    - NÚMEROS (interesse médio, decisões, preço máximo, quem mudou): calculados pelo código,
      em `calcular_indicadores`. A IA recebe esses números prontos e não pode inventar outros.
    - TEXTO (resumo, elogios, objeções, recomendações, experimentos): escrito pela IA,
      com base SOMENTE no que as personas disseram.
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
    Relatorio,
    ResultadoSimulacao,
)

log = logging.getLogger(__name__)

SISTEMA_ANALISTA = """Você é um analista de mercado que ajuda pequenos empreendedores a entender a reação de consumidores à sua oferta.
Você recebe: os dados do negócio, o debate entre consumidores sintéticos (2 rodadas) e indicadores já calculados.

Regras:
- Ignore objeções técnicas que um cliente comum não saberia avaliar (ex.: como um alimento esquenta no micro-ondas); priorize o que importa no dia a dia de quem compra.
- Baseie-se SOMENTE no debate e nos dados. Cada elogio e objeção deve indicar entre parênteses quem disse (ex.: "(Econômico, Crítico)").
- Os números já estão calculados: use-os como estão. Não recalcule nem invente números, percentuais ou estatísticas.
- Priorize o que apareceu em mais de uma persona e o que fez alguém mudar de opinião.
- Se houver referência de mercado, compare o preço da oferta com as faixas (popular, intermediária, premium) e com o nível de concorrência na região, deixando claro que são valores aproximados da internet.
- Se houver "Viabilidade financeira", use os números como estão: diga se o preço cobre o custo, se o lucro bate com o esperado,
  quanto lucraria nos cenários de clientes por dia e, se houver investimento, em quanto tempo se paga. Relacione com o debate e
  com a concorrência (ex.: "com 20 clientes por dia o lucro seria de R$ X por mês; com concorrência alta, valide esse movimento").
  NÃO fale em ponto de equilíbrio. Lembre que a conta não inclui impostos nem salários de funcionários e que negócios novos
  costumam levar meses para lucrar. Sem essa seção, não fale de lucro.
- Se a oferta tiver entrega, avalie se o modelo informado é confiável para este produto (prazo, taxa, área, riscos) com base no que as personas disseram.
- Recomendações: concretas, baratas e viáveis para um pequeno negócio DESTE ramo, cada uma ligada a uma objeção. Aproveite as boas sugestões que as próprias personas deram ao dono.
- Preço: use a "Avaliação do preço" dos indicadores. Se a maioria pagaria o preço cobrado, NÃO recomende baixar o preço.
- Experimentos: testes rápidos com clientes reais, dizendo o que fazer e o que medir, ADEQUADOS A ESTE RAMO e ao jeito como ele vende.
  Amostra grátis, degustação e brinde NÃO são o padrão: em restaurante, marmita, delivery e na maioria dos serviços eles dão
  prejuízo e não mostram se o cliente pagaria. Sugira no máximo UM experimento com algo gratuito, e só se fizer sentido no ramo.
  Prefira testes em que o cliente paga, por exemplo:
  · comida, marmita e delivery: combo ou kit de lançamento, plano semanal ou mensal, cupom para a 2ª compra, comparar duas
    versões do cardápio ou da foto no app, pesquisa rápida após a entrega, parceria com empresas ou condomínios próximos;
  · serviços (barbearia, estética, aulas, consertos): pacote ou assinatura, horário com preço diferente, programa de indicação,
    pré-venda de pacotes;
  · lojas e produtos: pré-venda, kit, frete grátis acima de um valor, testar dois preços ou dois anúncios.
  Diga sempre o que medir (vendas, recompra em X dias, ticket médio, quantos usaram o cupom...).
- Linguagem responsável: fale em "interesse simulado" e "hipóteses a validar". NUNCA fale em chance de sucesso, garantia ou previsão de vendas.
- Português do Brasil, direto, para quem não é especialista."""


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
    r1, r2 = resultado.da_rodada(1), resultado.da_rodada(2)
    precos = [p.preco_maximo for p in por_persona if p.preco_maximo is not None]
    aceitam, avaliacao, referencia, mediana = avaliar_preco(por_persona, preco_ofertado)
    return Indicadores(
        preco_ofertado=preco_ofertado,
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
        f"### {m.persona_nome} — rodada {m.rodada} (interesse {o.interesse}/10, compraria: {o.compraria}"
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


def _formatar_indicadores(ind: Indicadores) -> str:
    linhas = [
        f"- Preço ofertado: R$ {ind.preco_ofertado:.2f}",
        f"- Interesse médio: {ind.interesse_medio_r1} na rodada 1 → {ind.interesse_medio_r2} na rodada 2 (escala 0 a 10)",
        f"- Decisões na rodada 2: {ind.decisoes_r2['sim']} sim, {ind.decisoes_r2['talvez']} talvez, {ind.decisoes_r2['nao']} não",
        f"- Mudaram de posição: {ind.mudaram_de_posicao} de {len(ind.por_persona)}",
    ]
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
    linhas.append(f"- Avaliação do preço: {textos_preco[ind.avaliacao_preco]}")
    for p in ind.por_persona:
        linhas.append(
            f"- {p.persona_nome}: interesse {p.interesse_r1} → {p.interesse_r2}, "
            f"{p.compraria_r1} → {p.compraria_r2}{' (mudou)' if p.mudou else ''}"
        )
    return "\n".join(linhas)


def montar_pedido(negocio: dict, resultado: ResultadoSimulacao, indicadores: Indicadores, financeiro=None) -> str:
    rodadas = "\n\n".join(
        f"## Rodada {n}\n" + "\n\n".join(_transcrever(m) for m in resultado.da_rodada(n))
        for n in range(1, resultado.rodadas + 1)
    )
    return (
        f"{formatar_negocio(negocio, resultado.pesquisa)}\n\n"
        f"# Debate entre os consumidores sintéticos\n{rodadas}\n\n"
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
        pedido = montar_pedido(negocio, resultado, indicadores, relatorio.financeiro)
        analise, origem = await provider.gerar_com_origem(
            SISTEMA_ANALISTA, [{"role": "user", "content": pedido}], AnaliseDebate
        )
        relatorio.analise, relatorio.origem_analise = analise, origem
    except Exception as erro:  # noqa: BLE001 — o relatório sem texto ainda é útil
        log.exception("Agente analista falhou")
        relatorio.erro_analise = f"Não foi possível gerar a análise em texto ({type(erro).__name__}). Os números continuam válidos."
    relatorio.tokens_usados = provider.total_tokens() - tokens_antes
    relatorio.duracao_segundos = round(time.perf_counter() - inicio, 1)
    return relatorio
