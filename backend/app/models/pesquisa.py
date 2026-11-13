"""Formatos da pesquisa de mercado (o JSON gerado pelo agente pesquisador)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.services.mapa import CATEGORIAS

NomeFaixa = Literal["popular", "intermediaria", "premium"]
FAIXAS: tuple[NomeFaixa, ...] = ("popular", "intermediaria", "premium")


# ---------- O que a IA devolve (validado depois pelo código) ----------

class PlanoPesquisa(BaseModel):
    """1ª chamada: a IA adapta a pesquisa ao ramo do negócio."""

    tipo_estabelecimento: str = Field(description="Nome comum do tipo de loja, 1 a 3 palavras (ex.: 'barbearia', 'hamburgueria', 'loja de roupas femininas')")
    produto_comparavel: str = Field(description="O produto/serviço principal em poucas palavras, como as pessoas buscam (ex.: 'corte e barba', 'hambúrguer artesanal')")
    cidade: str = Field(description="Só o nome da cidade da localização informada, exatamente como escrito (ex.: 'Recife'), sem bairro nem estado")
    categoria_mapa: Literal[tuple(CATEGORIAS)] = Field(  # type: ignore[valid-type]
        description=("Categoria do mapa mais próxima das lojas concorrentes. Prefira sempre uma categoria próxima a 'outro' "
                     "(ex.: marmitaria, comida caseira ou self-service = restaurante; açaí = sorveteria; "
                     "salão de unhas = estetica_beleza). Use 'outro' só se nenhuma servir.")
    )
    palavras_nome: list[str] = Field(
        description=("2 ou 3 palavras que identificam o TIPO de negócio no nome dos estabelecimentos (ex.: 'burger', "
                     "'hamburgueria'; 'marmita', 'marmitaria'). Nunca adjetivos ou públicos ('fitness', 'premium', 'gourmet'), "
                     "que aparecem no nome de negócios de outros ramos.")
    )


class ExtracaoMercado(BaseModel):
    """2ª chamada: a IA lê os trechos com preços e lista os exemplos."""

    exemplos: list[str] = Field(
        description=(
            "Um item por produto/serviço COMPARÁVEL à oferta, no formato exato "
            "'faixa | estabelecimento | item | preço | trecho', onde faixa é popular, intermediaria ou premium, "
            "preço é só o número (ex.: 32,90) e trecho é o id do trecho de onde saiu (ex.: T3). "
            "Liste TODOS os itens comparáveis que encontrar (até 30), de estabelecimentos diferentes sempre que possível. "
            "Use apenas preços escritos nos trechos; não invente. Lista vazia se nada for comparável."
        )
    )


# ---------- Resultado final (calculado pelo código) ----------

class ExemploMercado(BaseModel):
    faixa: NomeFaixa
    estabelecimento: str
    item: str
    preco: float
    fonte_url: str


class FaixaMercado(BaseModel):
    faixa: NomeFaixa
    quantidade: int
    media: float | None = None
    desvio_padrao: float | None = None
    minimo: float | None = None
    maximo: float | None = None
    dados_suficientes: bool = Field(description="False se houver menos de 2 exemplos de preço")
    exemplos: list[ExemploMercado] = Field(default_factory=list)


class LojasRegiao(BaseModel):
    quantidade: int | None = Field(description="Pelo menos esta quantidade de lojas do ramo no raio (None = não foi possível contar)")
    raio_metros: int
    categoria: str
    nivel_concorrencia: str = Field(description="nenhum concorrente mapeado | baixa | media | alta | indeterminado")
    nomes: list[str] = Field(default_factory=list)
    fonte: str = ""
    erro: str | None = None
    observacao: str = "Número mínimo: lojas pequenas nem sempre estão no OpenStreetMap."


class PosicaoPreco(BaseModel):
    preco_usuario: float
    media_mercado: float | None
    desvio_padrao_mercado: float | None
    desvios_da_media: float | None = Field(description="(preço do usuário − média) ÷ desvio-padrão")
    faixa_mais_proxima: NomeFaixa | None
    resumo: str


class Fonte(BaseModel):
    titulo: str
    url: str


class PesquisaMercado(BaseModel):
    consultas: list[str] = Field(default_factory=list)
    faixas: list[FaixaMercado] = Field(default_factory=list)
    total_precos: int = 0
    media_geral: float | None = None
    desvio_padrao_geral: float | None = None
    posicao: PosicaoPreco | None = None
    lojas_regiao: LojasRegiao | None = None
    fontes: list[Fonte] = Field(default_factory=list)
    provedor_busca: str | None = None
    tokens_usados: int = 0
    duracao_segundos: float = 0
    gerada_em: str = ""
    erro: str | None = Field(default=None, description="Por que a parte de preços falhou (a simulação continua)")
    observacao: str = Field(default="", description="Ex.: possível negócio único na região (nenhum concorrente encontrado)")
    aviso: str = (
        "Referência automática obtida na internet e no OpenStreetMap: valores aproximados e possivelmente "
        "incompletos. Confira as fontes antes de decidir."
    )

    def tem_precos(self) -> bool:
        return self.total_precos > 0

    def tem_dados(self) -> bool:
        """Trouxe algo útil (preços ou contagem de lojas)? Senão, nem entra no contexto das personas."""
        return (self.tem_precos() or bool(self.lojas_regiao and self.lojas_regiao.quantidade is not None)
                or bool(self.observacao))
