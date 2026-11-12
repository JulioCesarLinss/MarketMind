"""Roda só o agente pesquisador e mostra (ou salva) o JSON da pesquisa de mercado.

Uso (dentro de backend/, com o ambiente virtual ativado):
    python -m scripts.pesquisar --negocio barbearia
    python -m scripts.pesquisar --negocio marmita --salvar pesquisa.json

Gasta ~3 buscas do Tavily e 2 chamadas de IA.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.agents.exemplos import NEGOCIOS
from app.agents.pesquisador import Pesquisador
from app.llm import criar_provider
from app.llm.factory import ConfiguracaoLLMError
from app.models.pesquisa import PesquisaMercado
from app.services.busca import criar_busca

NOMES = {"popular": "Popular", "intermediaria": "Intermediária", "premium": "Premium"}


def reais(v: float | None) -> str:
    return "-" if v is None else f"R$ {v:.2f}".replace(".", ",")


def imprimir_pesquisa(p: PesquisaMercado) -> None:
    print("\n" + "=" * 70)
    print("PESQUISA DE MERCADO")
    print("=" * 70)
    print("Buscas:", *[f"  • {c}" for c in p.consultas], sep="\n")
    if p.tem_precos():
        print(f"\nPreços confirmados: {p.total_precos} · média geral {reais(p.media_geral)} "
              f"· desvio-padrão {reais(p.desvio_padrao_geral)}")
        for f in p.faixas:
            if f.media is None:
                print(f"  {NOMES[f.faixa]:<14} sem dados")
                continue
            aviso = "" if f.dados_suficientes else "  (poucos dados)"
            print(f"  {NOMES[f.faixa]:<14} média {reais(f.media)} ± {reais(f.desvio_padrao)} "
                  f"(de {reais(f.minimo)} a {reais(f.maximo)}, {f.quantidade} preços){aviso}")
            for e in f.exemplos[:3]:
                print(f"      - {e.estabelecimento}: {e.item} {reais(e.preco)}")
        if p.posicao:
            print(f"\n{p.posicao.resumo}")
    if p.erro:
        print(f"\n⚠ Preços: {p.erro}")
    lojas = p.lojas_regiao
    if lojas:
        if lojas.quantidade is not None:
            print(f"\nLojas na região ({lojas.raio_metros} m, categoria {lojas.categoria}): pelo menos {lojas.quantidade} "
                  f"→ concorrência {lojas.nivel_concorrencia} ({lojas.fonte})")
            if lojas.nomes:
                print("  Ex.:", ", ".join(lojas.nomes[:6]))
        else:
            print(f"\n⚠ Lojas na região: {lojas.erro}")
    if p.fontes:
        print("\nFontes:", *[f"  • {f.titulo[:60]} — {f.url}" for f in p.fontes], sep="\n")
    print(f"\n({p.duracao_segundos}s, {p.tokens_usados} tokens, busca: {p.provedor_busca})")


def criar_pesquisador() -> Pesquisador:
    return Pesquisador(
        ia_rapida=criar_provider(papel="personas", mock_no_fim=False),
        ia_extracao=criar_provider(papel="analista", mock_no_fim=False),
        busca=criar_busca(),
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Agente pesquisador de mercado")
    parser.add_argument("--negocio", choices=list(NEGOCIOS), default="barbearia")
    parser.add_argument("--salvar", help="arquivo .json para guardar a pesquisa")
    args = parser.parse_args()
    try:
        pesquisador = criar_pesquisador()
    except ConfiguracaoLLMError as erro:
        print(f"Erro de configuração: {erro}")
        return
    negocio = NEGOCIOS[args.negocio]
    print(f"Pesquisando: {negocio['tipo']} — {negocio['produto']} (R$ {negocio['preco']:.2f}) em {negocio['localizacao']}")
    pesquisa = await pesquisador.executar(negocio)
    imprimir_pesquisa(pesquisa)
    if args.salvar:
        Path(args.salvar).parent.mkdir(parents=True, exist_ok=True)
        Path(args.salvar).write_text(pesquisa.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nJSON salvo em {args.salvar}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="  [aviso] %(message)s")
    asyncio.run(main())
