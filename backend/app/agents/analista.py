"""Agente analista: lê o debate inteiro e escreve o relatório para o empreendedor.

Divisão de trabalho:
    - NÚMEROS (interesse médio, decisões, preço máximo, quem mudou): calculados pelo código,
      em `calcular_indicadores`. A IA recebe esses números prontos e não pode inventar outros.
    - TEXTO (resumo, elogios, objeções, recomendações, experimentos): escrito pela IA,
      com base SOMENTE no que as personas disseram.
"""

import logging
import time
from statistics import mean

from app.agents.contexto import formatar_negocio
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
Você recebe: os dados do negócio, o debate entre 5 consumidores sintéticos (2 rodadas) e indicadores já calculados.

Regras:
- Baseie-se SOMENTE no debate e nos dados. Cada elogio e objeção deve indicar entre parênteses quem disse (ex.: "(Econômico, Crítico)").
- Os números já estão calculados: use-os como estão. Não recalcule nem invente números, percentuais ou estatísticas.
- Priorize o que apareceu em mais de uma persona e o que fez alguém mudar de opinião.
- Se houver referência de mercado, compare o preço da oferta com as faixas (popular, intermediária, premium) e com o nível de concorrência na região, deixando claro que são valores aproximados da internet.
- Recomendações: concretas, baratas e viáveis para um pequeno negócio DESTE ramo, cada uma ligada a uma objeção. Aproveite as boas sugestões que as próprias personas deram ao dono.
- Experimentos: testes rápidos com clientes reais, dizendo o que fazer e o que medir (ex.: "oferecer X para os 20 primeiros clientes e contar quantos voltam em 30 dias").
- Linguagem responsável: fale em "interesse simulado" e "hipóteses a validar". NUNCA fale em chance de sucesso, garantia ou previsão de vendas.
- Português do Brasil, direto, para quem não é especialista."""


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
    return Indicadores(
        preco_ofertado=preco_ofertado,
        interesse_medio_r1=round(mean(m.opiniao.interesse for m in r1), 1) if r1 else 0,
        interesse_medio_r2=round(mean(m.opiniao.interesse for m in r2), 1) if r2 else 0,
        decisoes_r2={d: sum(m.opiniao.compraria == d for m in r2) for d in ("sim", "talvez", "nao")},
        preco_maximo_medio=round(mean(precos), 2) if precos else None,
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
    for p in ind.por_persona:
        linhas.append(
            f"- {p.persona_nome}: interesse {p.interesse_r1} → {p.interesse_r2}, "
            f"{p.compraria_r1} → {p.compraria_r2}{' (mudou)' if p.mudou else ''}"
        )
    return "\n".join(linhas)


def montar_pedido(negocio: dict, resultado: ResultadoSimulacao, indicadores: Indicadores) -> str:
    rodadas = "\n\n".join(
        f"## Rodada {n}\n" + "\n\n".join(_transcrever(m) for m in resultado.da_rodada(n))
        for n in range(1, resultado.rodadas + 1)
    )
    return (
        f"{formatar_negocio(negocio, resultado.pesquisa)}\n\n"
        f"# Debate entre os consumidores sintéticos\n{rodadas}\n\n"
        f"# Indicadores (já calculados, use como estão)\n{_formatar_indicadores(indicadores)}\n\n"
        "Escreva o relatório para o empreendedor."
    )


async def analisar(provider: LLMProvider | None, negocio: dict, resultado: ResultadoSimulacao) -> Relatorio:
    """Gera o relatório. Se a IA falhar (ou não estiver configurada), devolve só os indicadores."""
    indicadores = calcular_indicadores(resultado, float(negocio.get("preco", 0)))
    relatorio = Relatorio(indicadores=indicadores)
    if provider is None:
        relatorio.erro_analise = "Agente analista não configurado (defina LLM_MODEL_ANALISTA no .env)."
        return relatorio
    inicio, tokens_antes = time.perf_counter(), provider.total_tokens()
    try:
        pedido = montar_pedido(negocio, resultado, indicadores)
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
