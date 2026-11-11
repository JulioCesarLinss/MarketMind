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


def mudou_de_posicao(antes: Opiniao, depois: Opiniao) -> bool:
    """Critério OBJETIVO de mudança, calculado pelo código (não pela palavra da IA):
    mudou a decisão de compra OU a nota de interesse variou 2 pontos ou mais."""
    return antes.compraria != depois.compraria or abs(antes.interesse - depois.interesse) >= 2


class MensagemDebate(BaseModel):
    """Uma fala no feed do debate (o que o frontend vai exibir)."""

    persona_id: str
    persona_nome: str
    rodada: int
    opiniao: Opiniao
    origem: str = Field(description="Quem gerou a resposta, ex.: groq/openai/gpt-oss-20b")
    duracao_segundos: float


class ResultadoSimulacao(BaseModel):
    """O debate completo de uma simulação."""

    mensagens: list[MensagemDebate]
    rodadas: int
    provedor_principal: str = Field(description="Nome do provedor principal, ex.: groq")
    tokens_usados: int
    duracao_segundos: float

    def da_rodada(self, rodada: int) -> list[MensagemDebate]:
        return [m for m in self.mensagens if m.rodada == rodada]

    def comparar_rodadas(self) -> list[tuple[MensagemDebate, MensagemDebate, bool]]:
        """Para cada persona: (fala da rodada 1, fala da rodada 2, mudou de posição de fato?)."""
        r1 = {m.persona_id: m for m in self.da_rodada(1)}
        return [
            (r1[m2.persona_id], m2, mudou_de_posicao(r1[m2.persona_id].opiniao, m2.opiniao))
            for m2 in self.da_rodada(2)
            if m2.persona_id in r1
        ]

    def usou_reserva(self) -> bool:
        """True se alguma fala não veio do provedor principal (ex.: Gemini ou mock assumiram)."""
        return any(m.origem.split("/")[0] != self.provedor_principal for m in self.mensagens)
