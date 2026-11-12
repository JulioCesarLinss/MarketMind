"""Métricas de qualidade do debate, calculadas sobre um ResultadoSimulacao.

Servem para comparar versões dos prompts com números, em vez de julgar no olho.
Funções puras: não chamam a IA.
"""

import re
from statistics import mean, pstdev

from app.models.schemas import ResultadoSimulacao


def _comeca_com_concordo(fala: str) -> bool:
    return bool(re.match(r"^\W*concordo", fala.strip(), flags=re.IGNORECASE))


def _citados(fala: str, nome_proprio: str, nomes: list[str]) -> set[str]:
    """Quais outras personas a fala menciona pelo nome."""
    texto = fala.lower()
    citados = set()
    for nome in nomes:
        if nome == nome_proprio:
            continue
        # Aceita o nome completo ("Consumidor Econômico") ou só o adjetivo ("Econômico")
        curto = nome.lower().replace("consumidor", "").strip()
        if nome.lower() in texto or (curto and curto in texto):
            citados.add(nome)
    return citados


def calcular_metricas(resultado: ResultadoSimulacao) -> dict:
    r1 = resultado.da_rodada(1)
    r2 = resultado.da_rodada(2)
    nomes = [m.persona_nome for m in r1]

    def notas(rodada):
        return [m.opiniao.interesse for m in rodada]

    def resumo_notas(rodada):
        valores = notas(rodada)
        if not valores:
            return {"media": 0, "desvio": 0, "amplitude": 0}
        return {
            "media": round(mean(valores), 1),
            "desvio": round(pstdev(valores), 2),
            "amplitude": max(valores) - min(valores),
        }

    precos = [m.opiniao.preco_maximo for m in resultado.mensagens if m.opiniao.preco_maximo is not None]
    comparacao = resultado.comparar_rodadas()

    citacoes = [_citados(m.opiniao.fala, m.persona_nome, nomes) for m in r2]
    total_citacoes = sum(len(c) for c in citacoes)
    mais_citada, vezes = max(
        ((n, sum(n in c for c in citacoes)) for n in nomes), key=lambda x: x[1], default=("", 0)
    )

    return {
        "pct_concordo_r2": round(100 * sum(_comeca_com_concordo(m.opiniao.fala) for m in r2) / len(r2)) if r2 else 0,
        "pct_cita_outro_r2": round(100 * sum(bool(c) for c in citacoes) / len(r2)) if r2 else 0,
        "pct_cita_2_ou_mais_r2": round(100 * sum(len(c) >= 2 for c in citacoes) / len(r2)) if r2 else 0,
        # Se todo mundo responde à mesma pessoa, esta % fica alta
        "mais_citada": {"nome": mais_citada, "pct_das_citacoes": round(100 * vezes / total_citacoes) if total_citacoes else 0},
        # Falas muito curtas costumam ser superficiais
        "palavras_por_fala_r2": round(mean(len(m.opiniao.fala.split()) for m in r2)) if r2 else 0,
        "notas_r1": resumo_notas(r1),
        "notas_r2": resumo_notas(r2),
        "decisoes_distintas_r1": len({m.opiniao.compraria for m in r1}),
        "mudaram_de_posicao": sum(1 for _, _, mudou in comparacao if mudou),
        "preco_maximo": {
            "respostas": len(precos),
            "media": round(mean(precos), 2) if precos else None,
            "min": min(precos) if precos else None,
            "max": max(precos) if precos else None,
        },
        "tokens": resultado.tokens_usados,
        "duracao_segundos": resultado.duracao_segundos,
    }
