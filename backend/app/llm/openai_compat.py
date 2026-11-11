"""Provedor para APIs no formato OpenAI: Groq e Ollama usam o mesmo código.

Muda apenas o endereço (base_url) e a chave.
"""

from openai import AsyncOpenAI

from app.llm.base import LLMProvider, Mensagens

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class OpenAICompatProvider(LLMProvider):
    def __init__(self, nome: str, base_url: str, api_key: str, modelo: str):
        super().__init__(modelo)
        self.nome = nome
        # max_retries: ao bater no limite por minuto do plano grátis (erro 429), o cliente
        # espera o tempo indicado pelo provedor e tenta de novo. Se ainda falhar, a
        # reserva (Gemini) assume — por isso não vale insistir demais aqui.
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, max_retries=3)

    async def _completar(self, sistema: str, mensagens: Mensagens) -> str:
        resposta = await self.client.chat.completions.create(
            model=self.modelo,
            messages=[{"role": "system", "content": sistema}, *mensagens],
            response_format={"type": "json_object"},  # garante JSON sintaticamente válido
        )
        if resposta.usage:
            self.tokens_usados += resposta.usage.total_tokens
        return resposta.choices[0].message.content or ""
