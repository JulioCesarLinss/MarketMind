"""Provedor Gemini (chave gerada no Google AI Studio), via SDK oficial google-genai."""

import asyncio

from google import genai
from google.genai import errors, types

from app.llm.base import LLMProvider, Mensagens

# Erros temporários que valem uma nova tentativa: limite (429) e servidor sobrecarregado (500/503)
CODIGOS_TEMPORARIOS = {429, 500, 503}
TENTATIVAS_HTTP = 3


class GeminiProvider(LLMProvider):
    nome = "gemini"

    def __init__(self, api_key: str, modelo: str):
        super().__init__(modelo)
        self.client = genai.Client(api_key=api_key)

    async def _completar(self, sistema: str, mensagens: Mensagens) -> str:
        # Gemini chama o papel do assistente de "model" em vez de "assistant"
        conteudos = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in mensagens
        ]
        for tentativa in range(TENTATIVAS_HTTP):
            try:
                resposta = await self.client.aio.models.generate_content(
                    model=self.modelo,
                    contents=conteudos,
                    config=types.GenerateContentConfig(
                        system_instruction=sistema,
                        response_mime_type="application/json",
                    ),
                )
                return resposta.text or ""
            except errors.APIError as erro:
                ultima = tentativa == TENTATIVAS_HTTP - 1
                if erro.code not in CODIGOS_TEMPORARIOS or ultima:
                    raise
                await asyncio.sleep(2 * (tentativa + 1))  # espera 2s, depois 4s
        raise RuntimeError("inalcançável")
