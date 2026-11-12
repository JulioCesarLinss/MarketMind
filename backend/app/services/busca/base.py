"""Interface comum dos serviços de busca na internet."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

log = logging.getLogger(__name__)

LIMITE_TEXTO = 20_000  # caracteres por página (o suficiente para achar preços sem estourar memória)


@dataclass
class ResultadoBusca:
    titulo: str
    url: str
    conteudo: str  # texto da página (ou o resumo, se o serviço não devolver o texto completo)


class BuscaIndisponivelError(Exception):
    """O serviço de busca falhou (sem chave, sem créditos, fora do ar...)."""


class BuscaWeb(ABC):
    nome: str = "base"

    @abstractmethod
    async def buscar(self, consulta: str, max_resultados: int = 5) -> list[ResultadoBusca]:
        """Faz a busca e devolve os resultados. Levanta BuscaIndisponivelError se falhar."""


class BuscaComReserva(BuscaWeb):
    """Tenta cada serviço em ordem; se um falhar, passa para o próximo."""

    def __init__(self, servicos: list[BuscaWeb]):
        self.servicos = servicos
        self.nome = " → ".join(s.nome for s in servicos)

    async def buscar(self, consulta: str, max_resultados: int = 5) -> list[ResultadoBusca]:
        erros = []
        for servico in self.servicos:
            try:
                return await servico.buscar(consulta, max_resultados)
            except BuscaIndisponivelError as erro:
                log.warning("Busca %s falhou (%s) — tentando o próximo", servico.nome, erro)
                erros.append(f"{servico.nome}: {erro}")
        raise BuscaIndisponivelError("; ".join(erros) or "nenhum serviço de busca configurado")
