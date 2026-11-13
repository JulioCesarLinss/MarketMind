"""Roda uma simulação completa (rodada 1 + rodada 2) no terminal.

Uso (dentro da pasta backend/, com o ambiente virtual ativado):
    python -m scripts.simular                       # cadeia do .env (Groq → Gemini → mock)
    python -m scripts.simular --provider mock       # sem gastar cota
    python -m scripts.simular --salvar saida.json   # salva o debate completo em JSON
    python -m scripts.simular --negocio barbearia   # outro negócio de exemplo (cafeteria | barbearia | roupas | marmita)
    python -m scripts.simular --sem-analista        # só o debate, sem o relatório
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.agents.especialistas import escolher_especialistas
from app.agents.analista import analisar
from app.agents.exemplos import NEGOCIOS
from app.llm import criar_provider
from app.llm.factory import ConfiguracaoLLMError, criar_provider_especialistas
from app.models.schemas import MensagemDebate, Relatorio, ResultadoSimulacao
from app.services.orquestrador import Orquestrador
from app.services.simulacoes import PesquisadorDemo
from scripts.pesquisar import criar_pesquisador, imprimir_pesquisa

ICONES = {"sim": "✅", "talvez": "🤔", "nao": "❌"}


async def imprimir_fala(m: MensagemDebate) -> None:
    o = m.opiniao
    mudou = "  🔄 mudou de opinião" if o.mudou_de_opiniao else ""
    print(
        f"\n[Consumidor] {m.persona_nome} — interesse {o.interesse}/10 "
        f"{ICONES.get(o.compraria, '')} {o.compraria}{mudou}"
    )
    print(f'  "{o.fala}"')
    if o.preco_maximo is not None:
        print(f"  Pagaria no máximo: R$ {o.preco_maximo:.2f}")
    if o.o_que_mudaria:
        print(f"  O que mudaria a decisão: {o.o_que_mudaria}")
    print(f"  ({m.duracao_segundos}s via {m.origem})")


VEREDITOS = {"favoravel": "✅ favorável", "favoravel_com_ajustes": "🟡 favorável com ajustes", "desfavoravel": "❌ desfavorável"}


async def imprimir_parecer(m) -> None:
    p = m.parecer
    print(f"\n[Especialista] {m.especialista_nome} — nota {p.nota}/10 {VEREDITOS[p.veredito]} · preço {p.avaliacao_preco}"
          + (f" (sugere R$ {p.preco_sugerido:.2f})" if p.preco_sugerido is not None else ""))
    print(f'  "{p.resumo}"')
    for titulo, itens in (("+", p.pontos_fortes), ("−", p.riscos), ("→", p.recomendacoes)):
        for item in itens:
            print(f"  {titulo} {item}")
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


def imprimir_relatorio(rel: Relatorio) -> None:
    if rel.financeiro:
        from app.services.financeiro import formatar_financeiro
        print("\n" + "=" * 70)
        print("VIABILIDADE FINANCEIRA (calculada pelo código)")
        print("=" * 70)
        print(formatar_financeiro(rel.financeiro))
    print("\n" + "=" * 70)
    print("RELATÓRIO DO ANALISTA")
    print("=" * 70)
    if rel.analise is None:
        print(f"  ⚠ {rel.erro_analise}")
        return
    a = rel.analise
    print(f"\n{a.resumo}")
    for titulo, itens in [
        ("Elogios", a.elogios),
        ("Objeções", a.objecoes),
        ("Fatores de decisão", a.fatores_de_decisao),
        ("Pontos de atenção", a.pontos_de_atencao),
        ("Recomendações", a.recomendacoes),
        ("Experimentos para validar com clientes reais", a.experimentos),
        ("Opiniões descartadas pelo analista (extrapoladas)", a.opinioes_descartadas),
    ]:
        print(f"\n{titulo}:")
        for item in itens:
            print(f"  • {item}")
    print(f"\n  ({rel.duracao_segundos}s, {rel.tokens_usados} tokens, via {rel.origem_analise})")
    print(f"\n  {rel.aviso}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Simulação completa do debate")
    parser.add_argument("--provider", help="força um provedor, sem reserva (mock | groq | gemini | ollama)")
    parser.add_argument("--concorrencia", type=int, help="chamadas simultâneas (padrão: LLM_CONCORRENCIA)")
    parser.add_argument("--negocio", choices=list(NEGOCIOS), default="cafeteria", help="negócio de exemplo")
    parser.add_argument("--sem-analista", action="store_true", help="só o debate, sem o relatório")
    parser.add_argument("--sem-pesquisa", action="store_true", help="pula a pesquisa de mercado na internet")
    parser.add_argument("--sem-especialistas", action="store_true", help="só os consumidores, sem os pareceres")
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

    especialistas = [] if args.sem_especialistas else escolher_especialistas()
    provider_esp = provider if args.provider or not especialistas else criar_provider_especialistas()
    if especialistas:
        print(f"Especialistas via: {provider_esp.modelo}")
    orquestrador = Orquestrador(provider, concorrencia=args.concorrencia, ao_publicar=imprimir_fala,
                                especialistas=especialistas, provider_especialistas=provider_esp,
                                ao_publicar_parecer=imprimir_parecer)
    pesquisa = None
    if not args.sem_pesquisa:
        print("\n  O pesquisador está buscando preços e lojas da região...")
        try:
            pesquisa = await (PesquisadorDemo() if args.provider == "mock" else criar_pesquisador()).executar(negocio)
            imprimir_pesquisa(pesquisa)
        except ConfiguracaoLLMError as erro:
            print(f"  Pesquisador não configurado: {erro}")
    resultado = await orquestrador.executar(negocio, pesquisa)
    imprimir_resumo(resultado)

    if not args.sem_analista:
        print("\n  O analista está juntando as opiniões e filtrando o que foi extrapolado...")
        try:
            # Sem mock no fim: um relatório gravado de outro negócio seria enganoso
            analista = criar_provider(args.provider, papel="analista", mock_no_fim=False)
        except ConfiguracaoLLMError as erro:
            print(f"  Analista não configurado: {erro}")
            analista = None
        resultado.relatorio = await analisar(analista, negocio, resultado)
        resultado.tokens_usados += resultado.relatorio.tokens_usados
        imprimir_relatorio(resultado.relatorio)

    if args.salvar:
        Path(args.salvar).write_text(resultado.model_dump_json(indent=2), encoding="utf-8")
        print(f"\n  Resultado salvo em {args.salvar}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="  [aviso] %(message)s")
    asyncio.run(main())
