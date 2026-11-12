"""Confere se a busca na internet e o mapa estão funcionando (sem mostrar as chaves).

Uso (dentro de backend/, com o ambiente virtual ativado):
    python -m scripts.testar_busca
"""

import asyncio
import sys

from app.config import settings
from app.services import mapa
from app.services.busca import BuscaIndisponivelError
from app.services.busca.servicos import OllamaBusca, TavilyBusca

CONSULTA = "preço corte de cabelo barbearia Recife"


async def testar_servico(nome: str, servico) -> None:
    if servico is None:
        print(f"  {nome}: sem chave no .env (pulado)")
        return
    try:
        resultados = await servico.buscar(CONSULTA, max_resultados=3)
        com_preco = sum("R$" in r.conteudo for r in resultados)
        print(f"  {nome}: OK — {len(resultados)} resultados, {com_preco} com preços em R$")
    except BuscaIndisponivelError as erro:
        print(f"  {nome}: FALHOU — {erro}")


async def main() -> None:
    print(f"Busca principal: {settings.busca_provider or '-'} · reserva: {settings.busca_reserva or '-'}")
    print("\nBusca na internet:")
    await testar_servico("tavily", TavilyBusca(settings.tavily_api_key) if settings.tavily_api_key else None)
    await testar_servico("ollama", OllamaBusca(settings.ollama_api_key) if settings.ollama_api_key else None)

    print("\nMapa (OpenStreetMap):")
    lojas, erro = await mapa.contar_lojas("Boa Viagem, Recife", "barbearia_salao", ["barbearia"], settings.mapa_raio_metros)
    if lojas:
        print(f"  OK — pelo menos {lojas.quantidade} barbearias em {settings.mapa_raio_metros} m ({lojas.fonte})")
    else:
        print(f"  FALHOU — {erro}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
