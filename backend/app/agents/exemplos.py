"""Negócios fictícios para testes e demonstração (enquanto não há formulário).

Perfis bem diferentes entre si, para conferir que as personas não ficam presas a um só exemplo.
"""

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

NEGOCIOS: dict[str, dict] = {
    "cafeteria": NEGOCIO_EXEMPLO,
    "barbearia": {
        "tipo": "Barbearia premium",
        "localizacao": "Centro comercial de capital",
        "produto": "Corte + barba com toalha quente e cerveja artesanal de cortesia",
        "preco": 85.0,
        "publico": "Homens de 25 a 45 anos que trabalham em escritório",
        "divulgacao": "Instagram e agendamento por aplicativo",
        "concorrentes": [
            {"nome": "Barbearia de rua", "preco": 35.0, "observacao": "sem agendamento, atende por ordem de chegada"},
            {"nome": "Rede de barbearias de shopping", "preco": 70.0, "observacao": "ambiente moderno, várias unidades"},
        ],
    },
    "roupas": {
        "tipo": "Loja de roupas de bairro",
        "localizacao": "Rua comercial de bairro popular",
        "produto": "Roupas femininas casuais de marcas nacionais",
        "preco": 79.9,
        "publico": "Mulheres de 20 a 50 anos do próprio bairro",
        "divulgacao": "Vitrine, WhatsApp e indicação",
        "concorrentes": [
            {"nome": "Loja de departamento no shopping", "preco": 59.9, "observacao": "parcelamento sem juros"},
            {"nome": "Lojas online chinesas", "preco": 35.0, "observacao": "entrega demorada, tamanho incerto"},
        ],
    },
    "marmita": {
        "tipo": "Marmitaria fitness",
        "localizacao": "Próximo a academias e faculdade",
        "produto": "Marmitas congeladas com calorias e macronutrientes informados",
        "preco": 26.0,
        "publico": "Frequentadores de academia e estudantes",
        "divulgacao": "Instagram, iFood e parceria com academias",
        "concorrentes": [
            {"nome": "Restaurante self-service", "preco": 22.0, "observacao": "comida na hora, sem controle de calorias"},
            {"nome": "Marmita caseira de vizinha", "preco": 15.0, "observacao": "barata, cardápio fixo"},
        ],
    },
}
