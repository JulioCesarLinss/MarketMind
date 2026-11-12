# MarketMind

**Simulador de mercado com múltiplos agentes de IA** — projeto da equipe para o **AKCIT Camp 2026**.

> Teste produtos, preços e estratégias antes de investir: o MarketMind cria consumidores sintéticos com perfis diferentes, faz com que eles avaliem e debatam a sua oferta, e entrega um relatório com objeções, oportunidades e cálculos financeiros básicos.

🚧 **Status:** em desenvolvimento. O andamento, as decisões técnicas e o histórico de cada commit estão em **[DESENVOLVIMENTO.md](DESENVOLVIMENTO.md)**.

---

## O problema

Quem vai abrir ou expandir um pequeno negócio precisa decidir **o que vender, quanto cobrar, para quem e como divulgar** — quase sempre com pouca informação e sem pesquisa de mercado acessível.

O MarketMind **não promete prever** se um negócio vai dar certo. Ele oferece uma forma rápida e estruturada de **explorar hipóteses**, levantar objeções e identificar o que merece ser validado com consumidores reais.

## Como funciona

### 1. Entrada do usuário

O empreendedor preenche um formulário com:

| Campo | Descrição |
|---|---|
| Tipo de negócio | Segmento e modelo de venda (ex.: loja física, delivery) |
| Localização | Bairro e cidade |
| Produto principal | O que será vendido |
| Preço de venda | Valor unitário |
| Público pretendido | Quem ele quer atingir |
| Divulgação | Canais planejados |
| Custos | Custo fixo mensal, custo variável por venda e taxa de plataforma (%) |
| Concorrentes (até 3) | Nome, preço e observações — cadastro manual |

### 2. Fluxo de processamento

```
Usuário preenche o formulário
        │
        ▼
Agente de contexto ──► organiza dados do negócio + concorrentes, identificando a origem de cada dado
        │
        ▼
Consumidores sintéticos (5 personas, cada um com prompt e memória próprios)
        │   Rodada 1: cada persona avalia a oferta individualmente
        │   Rodada 2: cada persona reage às opiniões das outras
        ▼
Moderador / orquestrador ──► controla as rodadas, distribui mensagens, salva o histórico
        │
        ▼
Agente analista ──► lê todo o debate e consolida padrões, objeções e oportunidades
        │
        ▼
Calculadora financeira (sem IA) ──► margem de contribuição e ponto de equilíbrio
        │
        ▼
Interface: feed do debate em tempo real + relatório final
```

### 3. Componentes

| Componente | Responsabilidade | Usa IA? |
|---|---|---|
| Agente de contexto | Padroniza as informações do negócio e dos concorrentes | Não (MVP) |
| Personas | Avaliam a oferta segundo prioridades próprias (preço, qualidade, conveniência, diferenciação, proximidade) | Sim |
| Moderador / orquestrador | Coordena rodadas e chamadas em paralelo, mantém o histórico | Não |
| Agente analista | Gera o relatório a partir do histórico real do debate | Sim |
| Calculadora financeira | Fórmulas determinísticas sobre os custos informados | Não |

**Por que multiagentes?** Não é um chatbot escrevendo cinco opiniões de uma vez. Cada consumidor tem instruções, preferências e memória próprias; as opiniões são geradas separadamente e depois confrontadas. O analista trabalha sobre o histórico real do debate.

### 4. Saída para o usuário

- Interesse simulado (0–10) por perfil de consumidor.
- Principais elogios, objeções e fatores de decisão de compra.
- Pontos de atenção sobre preço, produto, conveniência e divulgação.
- Sugestões de experimentos para validar com consumidores reais.
- Indicadores financeiros:

```
receita líquida por venda  = preço × (1 − taxa de plataforma)
margem de contribuição     = receita líquida − custo variável
ponto de equilíbrio        = custo fixo mensal ÷ margem de contribuição
```

## Avisos importantes

- As opiniões são **sintéticas**: não representam uma amostra estatística de consumidores reais.
- O sistema separa **dados informados pelo usuário**, **dados de concorrentes** e **opiniões geradas por IA**.
- Não há monitoramento automático de mercado: concorrentes são cadastrados manualmente.
- Não apresentamos "chance de sucesso" nem previsão de vendas — apenas **hipóteses a validar**.
- O cálculo financeiro é simplificado e depende dos custos informados.

## Tecnologias

| Parte | Tecnologia |
|---|---|
| Frontend | React + Vite + TypeScript |
| Backend | Python + FastAPI |
| IA | API de LLM (provedor a definir) — com **modo demo** que funciona sem chave |
| Persistência | SQLite |
| Deploy | Vercel (frontend) + Render (backend) |

Detalhes e justificativas em [DESENVOLVIMENTO.md](DESENVOLVIMENTO.md#2-tecnologias-necessárias).

## Estrutura do repositório

```
MarketMind/
├── README.md              # este arquivo
├── DESENVOLVIMENTO.md     # plano vivo + changelog (atualizado a cada commit)
├── .env.example           # variáveis de ambiente de referência
├── docs/                  # proposta original e materiais de apoio
├── backend/               # API FastAPI
│   ├── app/
│   │   ├── api/           # rotas HTTP
│   │   ├── agents/        # personas, moderador, analista e prompts
│   │   ├── llm/           # interface do provedor de LLM + modo mock
│   │   ├── services/      # orquestrador do debate e calculadora financeira
│   │   ├── models/        # schemas e tabelas
│   │   └── db/            # conexão SQLite
│   ├── demo_data/         # simulações gravadas para o modo demo
│   └── tests/
└── frontend/              # React + Vite
    └── src/
        ├── components/    # formulário, feed do debate, dashboard
        ├── pages/
        └── services/      # cliente da API
```

## Como rodar

**Backend (API):**

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example ..\.env    # preencha as chaves (ou deixe LLM_PROVIDER=mock)
uvicorn app.main:app --reload
```

Documentação interativa em http://localhost:8000/docs. Guia para o frontend: [docs/api.md](docs/api.md).

**Frontend:** *em construção.*

## Equipe

Projeto desenvolvido para o **AKCIT Camp 2026**. Frentes: Backend · Frontend · IA/Agentes · Produto/Validação.
