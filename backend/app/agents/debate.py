"""Textos enviados às personas em cada rodada do debate."""

import random

from app.agents.contexto import formatar_negocio
from app.models.schemas import MensagemDebate


def pedido_rodada_1(negocio: dict, pesquisa=None) -> str:
    return (
        "RODADA 1 — avaliação individual.\n\n"
        f"{formatar_negocio(negocio, pesquisa)}\n\n"
        "Avalie esta oferta a partir do seu perfil. Você ainda não ouviu nenhum outro consumidor."
    )


def resumo_falas(falas: list[MensagemDebate]) -> str:
    """Resumo do que cada um disse: fala, nota, decisão, do que gostou, principal objeção e sugestão ao dono.

    Pontos positivos, objeções e sugestões são a informação nova da rodada 2:
    é o que pode fazer uma persona enxergar algo que não tinha considerado.
    """
    blocos = []
    for m in falas:
        o = m.opiniao
        linhas = [f'- {m.persona_nome} (interesse {o.interesse}/10, compraria: {o.compraria}): "{o.fala}"']
        if o.pontos_positivos:
            linhas.append(f"  Gostou de: {'; '.join(o.pontos_positivos[:2])}")
        if o.objecoes:
            linhas.append(f"  Principal objeção: {o.objecoes[0]}")
        if o.o_que_mudaria:
            linhas.append(f"  Sugestão ao dono: {o.o_que_mudaria}")
        blocos.append("\n".join(linhas))
    return "\n".join(blocos)


def pedido_rodada_2(falas_dos_outros: list[MensagemDebate], rng: random.Random | None = None) -> str:
    # Embaralha a ordem para a persona não reagir sempre ao primeiro da lista
    falas = list(falas_dos_outros)
    (rng or random).shuffle(falas)
    return (
        "RODADA 2 — debate.\n\n"
        "Estes foram os comentários dos outros consumidores na rodada 1:\n"
        f"{resumo_falas(falas)}\n\n"
        "Agora reaja ao debate:\n"
        "- Comece respondendo ao comentário com o qual você MAIS DISCORDA, citando a pessoa pelo nome e "
        "explicando por quê a partir da sua realidade. Depois, comente o que outra pessoa disse que mexeu "
        "com a sua avaliação, para melhor ou para pior.\n"
        "- NÃO comece a fala com \"Concordo\". Varie o início, como uma pessoa real numa conversa.\n"
        "- Concordar com todo mundo não é realista; discordar de tudo também não.\n"
        "- Mantenha as SUAS prioridades, mas leve a sério os argumentos, as vantagens e as sugestões dos outros. "
        "Se algo do debate mudou o que você pensa da oferta, ajuste a nota e a decisão e diga na fala o que te "
        "convenceu (se depender de o dono adotar uma sugestão, deixe isso claro). Nesse caso marque "
        "mudou_de_opiniao como true; se mantiver sua posição, false.\n"
        "- Atualize \"o_que_mudaria\" se o debate te deu uma ideia melhor."
    )
