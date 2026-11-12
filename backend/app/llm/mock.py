"""Provedor de demonstração: devolve respostas gravadas em backend/demo_data/.

Não chama nenhuma API — sem chave, sem custo, sem internet.
O arquivo usado é `<nome_do_schema_em_minusculas>.json` (ex.: opiniao.json).
"""

import asyncio
from pathlib import Path

from app.llm.base import LLMProvider, Mensagens, T

DEMO_DATA = Path(__file__).resolve().parents[2] / "demo_data"


class MockProvider(LLMProvider):
    nome = "mock"

    def __init__(self, atraso_segundos: float = 0.5):
        super().__init__(modelo="demo")
        self.atraso = atraso_segundos

    async def gerar(self, sistema: str, mensagens: Mensagens, schema: type[T], tentativas: int = 2) -> T:
        await asyncio.sleep(self.atraso)  # simula o tempo de "digitação" no feed
        arquivo = DEMO_DATA / f"{schema.__name__.lower()}.json"
        if not arquivo.exists():
            raise FileNotFoundError(f"MockProvider: crie {arquivo} com um exemplo de {schema.__name__}")
        return schema.model_validate_json(arquivo.read_text(encoding="utf-8"))

    async def _completar(self, sistema: str, mensagens: Mensagens) -> str:  # não usado
        raise NotImplementedError
