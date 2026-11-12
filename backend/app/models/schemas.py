"""Schemas das respostas dos agentes (validados com Pydantic)."""

from typing import Literal

from pydantic import BaseModel, Field


class Opiniao(BaseModel):
    """Resposta de uma persona em uma rodada do debate."""

    fala: str = Field(description="Opinião da persona em linguagem natural, 2 a 4 frases, em primeira pessoa, com argumentos concretos")
    interesse: int = Field(ge=0, le=10, description="Interesse em comprar, de 0 (nenhum) a 10 (total)")
    compraria: Literal["sim", "nao", "talvez"]
    pontos_positivos: list[str] = Field(default_factory=list, description="O que agradou na oferta")
    objecoes: list[str] = Field(default_factory=list, description="O que impede ou dificulta a compra")
    mudou_de_opiniao: bool = Field(default=False, description="Se mudou de posição após ouvir as outras personas")
    preco_maximo: float | None = Field(
        default=None, description="Preço máximo em reais que você pagaria por este produto (número, ou null se não compraria)"
    )
    o_que_mudaria: str = Field(
        default="",
        description="Uma mudança realista que o dono poderia fazer e que resolveria sua principal objeção, em uma frase",
    )


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


class AnaliseDebate(BaseModel):
    """Parte em TEXTO do relatório, escrita pelo agente analista (IA)."""

    resumo: str = Field(description="Visão geral em 3 a 5 frases: como os consumidores receberam a oferta e por quê")
    elogios: list[str] = Field(description="2 a 4 pontos que agradaram, citando entre parênteses quem disse")
    objecoes: list[str] = Field(
        description="2 a 4 principais objeções, da mais citada para a menos, citando entre parênteses quem levantou"
    )
    fatores_de_decisao: list[str] = Field(description="2 a 4 fatores que mais pesaram na decisão de compra")
    pontos_de_atencao: list[str] = Field(
        description="Riscos ou pontos fracos, cada um começando pela área: 'Preço:', 'Produto:', 'Conveniência:' ou 'Divulgação:'"
    )
    recomendacoes: list[str] = Field(
        description="3 a 5 ajustes concretos e viáveis para o dono, ligados às objeções, do mais importante ao menos"
    )
    experimentos: list[str] = Field(
        description="2 a 3 testes baratos e rápidos com clientes reais, dizendo o que fazer e o que medir"
    )


class IndicadorPersona(BaseModel):
    persona_id: str
    persona_nome: str
    interesse_r1: int
    interesse_r2: int
    compraria_r1: str
    compraria_r2: str
    mudou: bool = Field(description="Critério objetivo: decisão mudou ou nota variou 2+ pontos")
    preco_maximo: float | None


class Indicadores(BaseModel):
    """Parte NUMÉRICA do relatório, calculada pelo código (não pela IA)."""

    preco_ofertado: float
    interesse_medio_r1: float
    interesse_medio_r2: float
    decisoes_r2: dict[str, int] = Field(description='Quantas personas disseram "sim", "talvez" e "nao" na rodada 2')
    preco_maximo_medio: float | None = Field(description="Média do preço máximo que as personas pagariam (rodada 2)")
    mudaram_de_posicao: int
    por_persona: list[IndicadorPersona]


class Relatorio(BaseModel):
    indicadores: Indicadores
    analise: AnaliseDebate | None = Field(default=None, description="None se o analista falhou")
    origem_analise: str | None = Field(default=None, description="Quem escreveu a análise, ex.: groq/openai/gpt-oss-120b")
    erro_analise: str | None = None
    tokens_usados: int = 0
    duracao_segundos: float = 0
    aviso: str = (
        "Opiniões geradas por IA (consumidores sintéticos): não representam uma amostra real de clientes. "
        "Use como hipóteses a validar, não como previsão de vendas."
    )


class ResultadoSimulacao(BaseModel):
    """O debate completo de uma simulação (e, depois do analista, o relatório)."""

    mensagens: list[MensagemDebate]
    rodadas: int
    provedor_principal: str = Field(description="Nome do provedor principal, ex.: groq")
    tokens_usados: int
    duracao_segundos: float
    relatorio: Relatorio | None = None

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
