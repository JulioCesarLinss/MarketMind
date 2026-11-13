"""Dados do formulário do empreendedor (entrada da API), conforme o README."""

from typing import Literal

from pydantic import BaseModel, Field

# Modelos de entrega que o formulário oferece (chave → texto mostrado às personas)
MODELOS_ENTREGA: dict[str, str] = {
    "proprio": "entregador próprio do negócio",
    "app_delivery": "aplicativo de delivery (ex.: iFood, 99Food), com entregadores do app",
    "entregador_parceiro": "motoboy terceirizado ou app de entregas avulsas (ex.: Lalamove, Uber Flash, Loggi)",
    "correios": "Correios ou transportadora",
    "outro": "outro modelo de entrega",
}


class Concorrente(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    preco: float = Field(ge=0)
    observacao: str = Field(default="", max_length=300)


class Custos(BaseModel):
    """Dados financeiros (todos opcionais no formulário). Usados pela calculadora em services/financeiro.py."""

    custo_fixo_mensal: float = Field(default=0, ge=0, description="Aluguel, energia, internet... por mês (impostos e salários não entram na conta)")
    custo_variavel_unitario: float = Field(default=0, ge=0, description="Custo médio de produção (e entrega) de uma unidade")
    taxa_plataforma_pct: float = Field(default=0, ge=0, le=100, description="Comissão de app/marketplace, em %")
    lucro_esperado_pct: float | None = Field(default=None, ge=0, lt=100, description="Quanto do preço você espera que vire lucro, em %")
    investimento_inicial: float | None = Field(default=None, ge=0, description="Quanto vai investir para abrir o negócio (R$)")


class Entrega(BaseModel):
    """O produto pode ser entregue? Se sim, como (as personas avaliam se o modelo é confiável)."""

    disponivel: bool = Field(description="true = faz entrega; false = só presencial/retirada")
    modelo: Literal[tuple(MODELOS_ENTREGA)] | None = Field(default=None, description="Como a entrega é feita")  # type: ignore[valid-type]
    taxa: float | None = Field(default=None, ge=0, description="Taxa de entrega em reais (0 = grátis)")
    prazo: str = Field(default="", max_length=80, description="Ex.: 40 minutos, 2 dias úteis")
    area: str = Field(default="", max_length=120, description="Ex.: até 5 km, todo o Recife, Brasil todo")
    garantias: str = Field(default="", max_length=300, description="Como garante que chega certo e no prazo (rastreio, embalagem, troca...)")


class NegocioEntrada(BaseModel):
    tipo: str = Field(min_length=1, max_length=120, description="Segmento e modelo de venda")
    localizacao: str = Field(min_length=1, max_length=120, description="Bairro e cidade")
    produto: str = Field(min_length=1, max_length=1000, description="O que será vendido")
    preco: float = Field(gt=0, description="Preço de venda unitário, em reais")
    publico: str = Field(min_length=1, max_length=200, description="Quem se quer atingir")
    divulgacao: str = Field(min_length=1, max_length=200, description="Canais planejados")
    custos: Custos | None = None
    entrega: Entrega | None = None
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
