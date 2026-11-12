"""Roda uma simulação completa (rodada 1 + rodada 2) no terminal.

Uso (dentro da pasta backend/, com o ambiente virtual ativado):
    python -m scripts.simular                       # cadeia do .env (Groq → Gemini → mock)
    python -m scripts.simular --provider mock       # sem gastar cota
    python -m scripts.simular --salvar saida.json   # salva o debate completo em JSON
    python -m scripts.simular --negocio barbearia   # outro negócio de exemplo (cafeteria | barbearia | roupas | marmita)
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.agents.exemplos import NEGOCIOS
from app.llm import criar_provider
from app.llm.factory import ConfiguracaoLLMError
from app.models.schemas import MensagemDebate, ResultadoSimulacao
from app.services.orquestrador import Orquestrador

ICONES = {"sim": "✅", "talvez": "🤔", "nao": "❌"}


async def imprimir_fala(m: MensagemDebate) -> None:
    o = m.opiniao
    mudou = "  🔄 mudou de opinião" if o.mudou_de_opiniao else ""
    print(
        f"\n[Rodada {m.rodada}] {m.persona_nome} — interesse {o.interesse}/10 "
        f"{ICONES.get(o.compraria, '')} {o.compraria}{mudou}"
    )
    print(f'  "{o.fala}"')
    if o.preco_maximo is not None:
        print(f"  Pagaria no máximo: R$ {o.preco_maximo:.2f}")
    if o.o_que_mudaria:
        print(f"  O que mudaria a decisão: {o.o_que_mudaria}")
    print(f"  ({m.duracao_segundos}s via {m.origem})")


def imprimir_resumo(resultado: ResultadoSimulacao) -> None:
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    comparacao = resultado.comparar_rodadas()
    for m1, m2, mudou in comparacao:
        marca = "🔄 mudou" if mudou else ""
        if m2.opiniao.mudou_de_opiniao and not mudou:
            marca = "(disse que mudou, mas pouco)"
        elif mudou and not m2.opiniao.mudou_de_opiniao:
            marca = "🔄 mudou (sem admitir)"
        print(
            f"  {m2.persona_nome:<28} interesse {m1.opiniao.interesse:>2} → {m2.opiniao.interesse:>2}"
            f"   {m1.opiniao.compraria:>6} → {m2.opiniao.compraria:<7} {marca}"
        )
    precos = [m2.opiniao.preco_maximo for _, m2, _ in comparacao if m2.opiniao.preco_maximo is not None]
    mudaram = sum(1 for _, _, mudou in comparacao if mudou)
    print(f"\n  Mudaram de posição: {mudaram} de {len(comparacao)}"
          "  (critério: mudou a decisão de compra ou a nota variou 2+ pontos)")
    if precos:
        print(f"  Preço máximo aceitável (rodada 2): média R$ {sum(precos) / len(precos):.2f}"
              f" (de R$ {min(precos):.2f} a R$ {max(precos):.2f})")
    print(f"  Tokens usados: {resultado.tokens_usados}")
    print(f"  Tempo total: {resultado.duracao_segundos}s")
    reservas = [m for m in resultado.mensagens if m.origem.split("/")[0] != resultado.provedor_principal]
    if reservas:
        print(f"  ⚠ Reserva usada em {len(reservas)} fala(s): "
              + ", ".join(f"{m.persona_nome} (rodada {m.rodada}, via {m.origem})" for m in reservas))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Simulação completa do debate")
    parser.add_argument("--provider", help="força um provedor, sem reserva (mock | groq | gemini | ollama)")
    parser.add_argument("--concorrencia", type=int, help="chamadas simultâneas (padrão: LLM_CONCORRENCIA)")
    parser.add_argument("--negocio", choices=list(NEGOCIOS), default="cafeteria", help="negócio de exemplo")
    parser.add_argument("--salvar", help="caminho de um arquivo .json para salvar o resultado")
    args = parser.parse_args()

    try:
        provider = criar_provider(args.provider)
    except ConfiguracaoLLMError as erro:
        print(f"Erro de configuração: {erro}")
        return

    print(f"Cadeia de provedores: {provider.modelo}")
    negocio = NEGOCIOS[args.negocio]
    print(f"Negócio: {negocio['tipo']} — {negocio['produto']} (R$ {negocio['preco']:.2f})")

    orquestrador = Orquestrador(provider, concorrencia=args.concorrencia, ao_publicar=imprimir_fala)
    resultado = await orquestrador.executar(negocio)
    imprimir_resumo(resultado)

    if args.salvar:
        Path(args.salvar).write_text(resultado.model_dump_json(indent=2), encoding="utf-8")
        print(f"\n  Resultado salvo em {args.salvar}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="  [aviso] %(message)s")
    asyncio.run(main())
