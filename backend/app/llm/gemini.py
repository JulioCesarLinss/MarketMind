"""Provedor Gemini (chave gerada no Google AI Studio), via SDK oficial google-genai."""

from google import genai
from google.genai import types

from app.llm.base import LLMProvider, Mensagens


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
        resposta = await self.client.aio.models.generate_content(
            model=self.modelo,
            contents=conteudos,
            config=types.GenerateContentConfig(
                system_instruction=sistema,
                response_mime_type="application/json",
            ),
        )
        return resposta.text or ""
