"""Schemas das respostas dos agentes (validados com Pydantic)."""

from typing import Literal

from pydantic import BaseModel, Field


class Opiniao(BaseModel):
    """Resposta de uma persona em uma rodada do debate."""

    fala: str = Field(description="Opinião da persona em linguagem natural, 1 a 3 frases, em primeira pessoa")
    interesse: int = Field(ge=0, le=10, description="Interesse em comprar, de 0 (nenhum) a 10 (total)")
    compraria: Literal["sim", "nao", "talvez"]
    pontos_positivos: list[str] = Field(default_factory=list, description="O que agradou na oferta")
    objecoes: list[str] = Field(default_factory=list, description="O que impede ou dificulta a compra")
    mudou_de_opiniao: bool = Field(default=False, description="Se mudou de posição após ouvir as outras personas")
