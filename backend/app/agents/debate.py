"""Textos enviados às personas em cada rodada do debate."""

from app.agents.contexto import formatar_negocio
from app.models.schemas import MensagemDebate


def pedido_rodada_1(negocio: dict) -> str:
    return (
        "RODADA 1 — avaliação individual.\n\n"
        f"{formatar_negocio(negocio)}\n\n"
        "Avalie esta oferta a partir do seu perfil. Você ainda não ouviu nenhum outro consumidor."
    )


def resumo_falas(falas: list[MensagemDebate]) -> str:
    """Resumo curto do que cada um disse (só o essencial, para economizar tokens)."""
    return "\n".join(
        f'- {m.persona_nome} (interesse {m.opiniao.interesse}/10, compraria: {m.opiniao.compraria}): '
        f'"{m.opiniao.fala}"'
        for m in falas
    )


def pedido_rodada_2(falas_dos_outros: list[MensagemDebate]) -> str:
    return (
        "RODADA 2 — debate.\n\n"
        "Estes foram os comentários dos outros consumidores na rodada 1:\n"
        f"{resumo_falas(falas_dos_outros)}\n\n"
        "Agora reaja ao debate:\n"
        "- Responda diretamente a pelo menos um deles, citando-o pelo nome, dizendo se concorda ou discorda e por quê.\n"
        "- Continue avaliando a partir das SUAS prioridades; não adote as prioridades dos outros.\n"
        "- Só mude sua avaliação se algum argumento concreto realmente afetar o que importa para você. "
        "Se mudar, marque mudou_de_opiniao como true e diga na fala o que te convenceu.\n"
        "- Se mantiver sua posição, marque mudou_de_opiniao como false."
    )
