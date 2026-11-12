"""Mede a qualidade do debate com números (para comparar versões dos prompts).

Uso (dentro da pasta backend/, com o ambiente virtual ativado):
    python -m scripts.avaliar_personas --negocio cafeteria
    python -m scripts.avaliar_personas --todos                  # todos os negócios (gasta mais cota)
    python -m scripts.avaliar_personas --provider mock          # sem gastar cota
    python -m scripts.avaliar_personas --negocio cafeteria --salvar antes.json

Cada simulação real gasta ~10-15 mil tokens do plano grátis. Com --todos, há uma
pausa entre os negócios para não estourar o limite por minuto.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from app.agents.exemplos import NEGOCIOS
from app.llm import criar_provider
from app.llm.factory import ConfiguracaoLLMError
from app.services.metricas import calcular_metricas
from app.services.orquestrador import Orquestrador

PAUSA_ENTRE_NEGOCIOS = 60  # segundos (o limite do Groq é por minuto)


def imprimir_metricas(nome: str, m: dict) -> None:
    print(f"\n=== {nome} ===")
    print(f"  Falas da rodada 2 começando com 'Concordo': {m['pct_concordo_r2']}%   (meta: < 40%)")
    print(f"  Falas da rodada 2 citando outra persona:    {m['pct_cita_outro_r2']}%")
    print(f"  Falas da rodada 2 citando 2+ personas:      {m['pct_cita_2_ou_mais_r2']}%   (meta: ≥ 60%)")
    mc = m["mais_citada"]
    if mc["nome"]:
        print(f"  Persona mais citada: {mc['nome']} ({mc['pct_das_citacoes']}% das citações)   (meta: ≤ 40%)")
    print(f"  Palavras por fala na rodada 2 (média):     {m['palavras_por_fala_r2']}")
    for r in ("r1", "r2"):
        n = m[f"notas_{r}"]
        print(f"  Notas {r}: média {n['media']}, desvio {n['desvio']}, amplitude {n['amplitude']}"
              + ("   (meta: amplitude ≥ 4)" if r == "r1" else ""))
    print(f"  Decisões diferentes na rodada 1: {m['decisoes_distintas_r1']}   (meta: ≥ 2)")
    print(f"  Mudaram de posição: {m['mudaram_de_posicao']}")
    p = m["preco_maximo"]
    if p["respostas"]:
        print(f"  Preço máximo aceitável: média R$ {p['media']:.2f} (de R$ {p['min']:.2f} a R$ {p['max']:.2f})")
    print(f"  Tokens: {m['tokens']}   (meta: < 10 mil)   Tempo: {m['duracao_segundos']}s")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Métricas de qualidade das personas")
    parser.add_argument("--negocio", choices=list(NEGOCIOS), default="cafeteria")
    parser.add_argument("--todos", action="store_true", help="roda todos os negócios de exemplo")
    parser.add_argument("--provider", help="força um provedor, sem reserva (mock | groq | gemini | ollama)")
    parser.add_argument("--salvar", help="arquivo .json para guardar métricas e falas")
    args = parser.parse_args()

    try:
        provider = criar_provider(args.provider)
    except ConfiguracaoLLMError as erro:
        print(f"Erro de configuração: {erro}")
        return

    nomes = list(NEGOCIOS) if args.todos else [args.negocio]
    saida = {}
    for i, nome in enumerate(nomes):
        if i > 0 and provider.nome != "mock":
            print(f"\n  (pausa de {PAUSA_ENTRE_NEGOCIOS}s por causa do limite por minuto...)")
            await asyncio.sleep(PAUSA_ENTRE_NEGOCIOS)
        print(f"Simulando: {nome}...")
        resultado = await Orquestrador(provider).executar(NEGOCIOS[nome])
        metricas = calcular_metricas(resultado)
        imprimir_metricas(nome, metricas)
        saida[nome] = {"metricas": metricas, "resultado": resultado.model_dump()}

    if args.salvar:
        Path(args.salvar).parent.mkdir(parents=True, exist_ok=True)
        Path(args.salvar).write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSalvo em {args.salvar}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="  [aviso] %(message)s")
    asyncio.run(main())
