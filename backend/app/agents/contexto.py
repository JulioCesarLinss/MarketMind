"""Agente de contexto (MVP: função Python, sem LLM).

Transforma os dados do formulário em um texto padronizado para as personas.
"""


def formatar_negocio(negocio: dict) -> str:
    linhas = [
        "## Oferta a avaliar (dados informados pelo empreendedor)",
        f"- Tipo de negócio: {negocio.get('tipo', '-')}",
        f"- Localização: {negocio.get('localizacao', '-')}",
        f"- Produto principal: {negocio.get('produto', '-')}",
        f"- Preço: R$ {negocio.get('preco', 0):.2f}",
        f"- Público pretendido: {negocio.get('publico', '-')}",
        f"- Divulgação e canais: {negocio.get('divulgacao', '-')}",
    ]
    concorrentes = negocio.get("concorrentes") or []
    if concorrentes:
        linhas.append("\n## Concorrentes (cadastrados manualmente pelo empreendedor)")
        for c in concorrentes:
            linhas.append(f"- {c.get('nome', '-')}: R$ {c.get('preco', 0):.2f} — {c.get('observacao', '')}")
    else:
        linhas.append("\n## Concorrentes\n- Nenhum concorrente foi informado pelo empreendedor.")
    return "\n".join(linhas)
