"""Dados do formulário do empreendedor (entrada da API), conforme o README."""

from pydantic import BaseModel, Field


class Concorrente(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    preco: float = Field(ge=0)
    observacao: str = Field(default="", max_length=300)


class Custos(BaseModel):
    """Usados pela calculadora financeira (ainda não implementada)."""

    custo_fixo_mensal: float = Field(ge=0)
    custo_variavel_unitario: float = Field(ge=0, description="Custo para produzir/entregar uma unidade")
    taxa_plataforma_pct: float = Field(default=0, ge=0, le=100, description="Comissão de app/marketplace, em %")


class NegocioEntrada(BaseModel):
    tipo: str = Field(min_length=1, max_length=120, description="Segmento e modelo de venda")
    localizacao: str = Field(min_length=1, max_length=120, description="Bairro e cidade")
    produto: str = Field(min_length=1, max_length=1000, description="O que será vendido")
    preco: float = Field(gt=0, description="Preço de venda unitário, em reais")
    publico: str = Field(min_length=1, max_length=200, description="Quem se quer atingir")
    divulgacao: str = Field(min_length=1, max_length=200, description="Canais planejados")
    custos: Custos | None = None
    concorrentes: list[Concorrente] = Field(default_factory=list, max_length=3)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tipo": "Barbearia premium",
                    "localizacao": "Centro comercial de capital",
                    "produto": "Corte + barba com toalha quente e cerveja artesanal de cortesia",
                    "preco": 85.0,
                    "publico": "Homens de 25 a 45 anos que trabalham em escritório",
                    "divulgacao": "Instagram e agendamento por aplicativo",
                    "custos": {"custo_fixo_mensal": 12000, "custo_variavel_unitario": 25, "taxa_plataforma_pct": 0},
                    "concorrentes": [
                        {"nome": "Barbearia de rua", "preco": 35.0, "observacao": "sem agendamento"},
                        {"nome": "Rede de barbearias de shopping", "preco": 70.0, "observacao": "ambiente moderno"},
                    ],
                }
            ]
        }
    }
