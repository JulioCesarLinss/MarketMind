"""Teste manual da camada de LLM: uma ou todas as personas avaliam um negócio de exemplo.

Uso (dentro da pasta backend/, com o ambiente virtual ativado):
    python -m scripts.testar_llm                      # cadeia do .env: principal → reserva → mock
    python -m scripts.testar_llm --provider groq      # só um provedor, sem reserva
    python -m scripts.testar_llm --todas              # as 5 personas em paralelo
    python -m scripts.testar_llm --provider groq --listar-modelos   # nomes de modelos da sua chave
"""

import argparse
import asyncio
import logging
import sys
import time

from app.agents.contexto import formatar_negocio
from app.agents.personas import PERSONAS
from app.llm import criar_provider
from app.llm.factory import ConfiguracaoLLMError
from app.models.schemas import Opiniao

# Negócio fictício só para teste
NEGOCIO_EXEMPLO = {
    "tipo": "Cafeteria com delivery",
    "localizacao": "Bairro residencial de cidade média",
    "produto": "Café especial e salgados artesanais",
    "preco": 18.0,
    "publico": "Adultos que trabalham em casa",
    "divulgacao": "Instagram e WhatsApp",
    "concorrentes": [
        {"nome": "Padaria tradicional do bairro", "preco": 9.0, "observacao": "café comum, entrega rápida"},
    ],
}


async def avaliar(provider, persona_id: str) -> None:
    persona = PERSONAS[persona_id]
    mensagens = [{"role": "user", "content": formatar_negocio(NEGOCIO_EXEMPLO) + "\n\nDê sua avaliação."}]
    inicio = time.perf_counter()
    try:
        opiniao, origem = await provider.gerar_com_origem(persona.prompt_sistema(), mensagens, Opiniao)
    except Exception as erro:  # mostra o erro desta persona sem derrubar as outras
        print(f"\n=== {persona.nome} — ERRO ===\n{type(erro).__name__}: {str(erro)[:500]}")
        return
    duracao = time.perf_counter() - inicio
    print(f"\n=== {persona.nome} ({duracao:.1f}s) — respondido por {origem} ===")
    print(opiniao.model_dump_json(indent=2))


async def listar_modelos(provider: str) -> None:
    """Mostra os nomes de modelos disponíveis para a chave configurada no .env."""
    from app.config import settings

    if provider == "groq":
        from openai import AsyncOpenAI

        from app.llm.openai_compat import GROQ_BASE_URL

        if not settings.groq_api_key:
            print("Preencha GROQ_API_KEY no .env primeiro.")
            return
        client = AsyncOpenAI(base_url=GROQ_BASE_URL, api_key=settings.groq_api_key)
        nomes = sorted([m.id async for m in client.models.list()])
    elif provider == "gemini":
        from google import genai

        if not settings.gemini_api_key:
            print("Preencha GEMINI_API_KEY no .env primeiro.")
            return
        client = genai.Client(api_key=settings.gemini_api_key)
        nomes = sorted(
            m.name.removeprefix("models/")
            for m in client.models.list()
            if "generateContent" in (m.supported_actions or [])
        )
    else:
        print("Use --listar-modelos com --provider groq ou --provider gemini.")
        return

    print(f"Modelos disponíveis no {provider} (copie um nome para LLM_MODEL_PERSONAS no .env):")
    for nome in nomes:
        print(f"  {nome}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Testa o provedor de LLM configurado")
    parser.add_argument("--provider", help="mock | groq | gemini | ollama (padrão: LLM_PROVIDER do .env)")
    parser.add_argument("--modelo", help="nome do modelo (padrão: LLM_MODEL_PERSONAS do .env)")
    parser.add_argument("--persona", default="economico", choices=list(PERSONAS))
    parser.add_argument("--todas", action="store_true", help="roda as 5 personas em paralelo")
    parser.add_argument("--listar-modelos", action="store_true", help="lista os modelos disponíveis na sua chave")
    args = parser.parse_args()

    if args.listar_modelos:
        await listar_modelos((args.provider or "").lower())
        return

    try:
        provider = criar_provider(args.provider, args.modelo)
    except ConfiguracaoLLMError as erro:
        print(f"Erro de configuração: {erro}")
        return

    print(f"Provedor: {provider.nome} | Cadeia: {provider.modelo}")
    ids = list(PERSONAS) if args.todas else [args.persona]
    await asyncio.gather(*(avaliar(provider, pid) for pid in ids))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # acentos corretos no terminal do Windows
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="  [aviso] %(message)s")
    asyncio.run(main())
