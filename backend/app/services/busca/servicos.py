"""Adaptadores dos serviços de busca (HTTP com httpx)."""

import httpx

from app.services.busca.base import LIMITE_TEXTO, BuscaIndisponivelError, BuscaWeb, ResultadoBusca

TIMEOUT = 40


class TavilyBusca(BuscaWeb):
    """Tavily: 1.000 buscas grátis por mês, sem cartão (https://app.tavily.com)."""

    nome = "tavily"
    URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def buscar(self, consulta: str, max_resultados: int = 5) -> list[ResultadoBusca]:
        corpo = {
            "query": consulta,
            "max_results": max_resultados,
            "search_depth": "basic",      # 1 crédito por busca
            "include_raw_content": "text",  # texto da página: é onde os preços aparecem
            "country": "brazil",
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resposta = await client.post(self.URL, json=corpo, headers={"Authorization": f"Bearer {self.api_key}"})
        except httpx.HTTPError as erro:
            raise BuscaIndisponivelError(f"falha de conexão ({type(erro).__name__})") from erro
        if resposta.status_code != 200:
            raise BuscaIndisponivelError(f"HTTP {resposta.status_code}")
        return [
            ResultadoBusca(
                titulo=r.get("title") or "",
                url=r.get("url") or "",
                conteudo=((r.get("raw_content") or "") + "\n" + (r.get("content") or ""))[:LIMITE_TEXTO],
            )
            for r in resposta.json().get("results", [])
        ]


class OllamaBusca(BuscaWeb):
    """Busca do Ollama (https://ollama.com/settings/keys). Atenção: exige créditos pagos."""

    nome = "ollama"
    URL = "https://ollama.com/api/web_search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def buscar(self, consulta: str, max_resultados: int = 5) -> list[ResultadoBusca]:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resposta = await client.post(
                    self.URL,
                    json={"query": consulta, "max_results": max_resultados},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
        except httpx.HTTPError as erro:
            raise BuscaIndisponivelError(f"falha de conexão ({type(erro).__name__})") from erro
        if resposta.status_code == 402:
            raise BuscaIndisponivelError("a busca do Ollama exige créditos pagos")
        if resposta.status_code != 200:
            raise BuscaIndisponivelError(f"HTTP {resposta.status_code}")
        return [
            ResultadoBusca(titulo=r.get("title") or "", url=r.get("url") or "", conteudo=(r.get("content") or "")[:LIMITE_TEXTO])
            for r in resposta.json().get("results", [])
        ]
