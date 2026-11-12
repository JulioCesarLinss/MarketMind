"""Interface comum a todos os provedores de LLM.

O resto do sistema chama apenas `provider.gerar(...)` e recebe um objeto
Pydantic já validado — sem saber se por trás está Groq, Gemini, Ollama ou o mock.
"""

import json
import re
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# Mensagens no formato: [{"role": "user" | "assistant", "content": "..."}]
Mensagens = list[dict[str, str]]


class RespostaInvalidaError(Exception):
    """O modelo não devolveu um JSON válido para o schema pedido."""


def _descrever_campo(prop: dict) -> str:
    """Traduz uma propriedade do JSON Schema para uma descrição curta em português."""
    if "anyOf" in prop:  # campo opcional, ex.: float | None
        tipos = {p.get("type") for p in prop["anyOf"]}
        if "number" in tipos or "integer" in tipos:
            tipo = "número ou null"
        else:
            tipo = "texto ou null"
    elif "enum" in prop:
        tipo = "um destes valores: " + ", ".join(json.dumps(v, ensure_ascii=False) for v in prop["enum"])
    elif prop.get("type") == "integer":
        faixa = f" de {prop['minimum']} a {prop['maximum']}" if "minimum" in prop and "maximum" in prop else ""
        tipo = f"número inteiro{faixa}"
    elif prop.get("type") == "number":
        tipo = "número"
    elif prop.get("type") == "array":
        tipo = "lista de textos"
    elif prop.get("type") == "boolean":
        tipo = "true ou false"
    else:
        tipo = "texto"
    descricao = prop.get("description")
    return f"{tipo} — {descricao}" if descricao else tipo


def instrucao_json(schema: type[BaseModel]) -> str:
    """Texto anexado ao prompt de sistema descrevendo o formato de resposta.

    Usa uma lista simples de campos em vez do JSON Schema bruto: com o schema bruto,
    alguns modelos devolvem o próprio schema em vez de preenchê-lo.
    """
    propriedades = schema.model_json_schema().get("properties", {})
    campos = "\n".join(f'- "{nome}": {_descrever_campo(prop)}' for nome, prop in propriedades.items())
    return (
        "\n\n## Formato da resposta\n"
        "Responda APENAS com um objeto JSON (sem texto antes ou depois, sem blocos de código) "
        "contendo exatamente estes campos, preenchidos com a SUA avaliação:\n"
        f"{campos}\n"
        "Não descreva o formato nem repita estas instruções: devolva somente o objeto JSON preenchido."
    )


def extrair_json(texto: str) -> str:
    """Remove cercas ```json ... ``` que alguns modelos insistem em colocar."""
    texto = texto.strip()
    cerca = re.match(r"^```(?:json)?\s*(.*?)\s*```$", texto, re.DOTALL)
    return cerca.group(1) if cerca else texto


class LLMProvider(ABC):
    nome: str = "base"

    def __init__(self, modelo: str):
        self.modelo = modelo
        self.tokens_usados = 0  # somado a cada chamada (entrada + saída)

    def total_tokens(self) -> int:
        """Tokens gastos por este provedor desde que foi criado."""
        return self.tokens_usados

    async def gerar(
        self,
        sistema: str,
        mensagens: Mensagens,
        schema: type[T],
        tentativas: int = 2,
    ) -> T:
        """Chama o modelo e valida a resposta com o schema. Tenta de novo se vier inválida."""
        sistema_completo = sistema + instrucao_json(schema)
        ultimo_erro: Exception | None = None
        for _ in range(tentativas):
            texto = await self._completar(sistema_completo, mensagens)
            try:
                return schema.model_validate_json(extrair_json(texto))
            except ValidationError as erro:
                ultimo_erro = erro
        raise RespostaInvalidaError(
            f"{self.nome}/{self.modelo} não devolveu JSON válido para {schema.__name__}: {ultimo_erro}"
        )

    async def gerar_com_origem(
        self,
        sistema: str,
        mensagens: Mensagens,
        schema: type[T],
        tentativas: int = 2,
    ) -> tuple[T, str]:
        """Igual a `gerar`, mas também diz quem respondeu (ex.: "groq/openai/gpt-oss-20b")."""
        resultado = await self.gerar(sistema, mensagens, schema, tentativas)
        return resultado, f"{self.nome}/{self.modelo}"

    @abstractmethod
    async def _completar(self, sistema: str, mensagens: Mensagens) -> str:
        """Faz a chamada ao provedor e devolve o texto bruto da resposta."""
