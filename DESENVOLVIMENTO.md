# MarketMind — Desenvolvimento

Documento vivo da equipe: **como o projeto está sendo construído, o que já foi feito e o que falta.**
Visão geral do produto: [README.md](README.md) · Proposta original: [docs/proposta.md](docs/proposta.md)

---

## 1. Como usar este documento

**Regra da equipe: todo commit atualiza este arquivo.**

1. Marque no [checklist](#7-plano-de-execução) o que foi concluído (`- [x]`).
2. Adicione uma linha no [Changelog](#9-changelog) (mais recente no topo) com data, autor e o que mudou.
3. Se tomou uma decisão técnica, registre em [Decisões](#8-decisões) (tomadas ou pendentes).

Formato sugerido de mensagem de commit: `tipo: descrição curta` — tipos: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`.
Ex.: `feat: rodada 1 do debate com MockProvider`.

---

## 2. Tecnologias necessárias

### Núcleo

| Camada | Tecnologia | Por quê |
|---|---|---|
| Frontend | **React + Vite + TypeScript** | Formulário, feed do debate e dashboard; Vite é rápido para começar |
| Backend | **Python 3.11+ + FastAPI** (rodando com **Uvicorn**) | API simples, assíncrona, ótima para orquestrar chamadas de LLM |
| IA | **API de LLM** (provedor a definir) | Mesmo modelo atuando como agentes diferentes, com prompts e memória separados |
| Persistência | **SQLite** | Negócios, simulações, mensagens e relatórios sem infraestrutura extra |
| Deploy | **Vercel** (frontend) + **Render** (backend) | Planos gratuitos e URL pública para teste |

### Bibliotecas de apoio

**Backend:** `fastapi`, `uvicorn`, `pydantic` (validação e saída estruturada dos agentes), `sqlmodel` (ORM sobre SQLite), `python-dotenv` (variáveis de ambiente), `sse-starlette` (feed em tempo real), `pytest` (testes). O SDK do LLM entra quando o provedor for escolhido.

**Frontend:** `recharts` (gráfico de interesse por persona), `tailwindcss` (estilo rápido). Chamadas à API com `fetch`.

### Ferramentas para cada membro instalar

- **Git** e acesso ao repositório
- **Node.js 20+** (frontend)
- **Python 3.11+** (backend)
- Editor: VS Code (recomendado)

### O que NÃO vamos usar no MVP

LangChain/CrewAI (orquestração é simples, Python puro basta), Docker, banco de dados em servidor, scraping.

---

## 3. Arquitetura

```
frontend (Vercel)                      backend (Render)
┌──────────────────┐   HTTP / SSE    ┌──────────────────────────────────┐
│ Formulário       │ ──────────────► │ api/         rotas               │
│ Feed do debate   │ ◄────────────── │ services/    orquestrador        │
│ Dashboard        │                 │              calculadora         │
└──────────────────┘                 │ agents/      personas, analista  │
                                     │ llm/         LLMProvider ──────► mock | API real
                                     │ db/ models/  SQLite              │
                                     └──────────────────────────────────┘
```

### Endpoints planejados

| Método | Rota | Função |
|---|---|---|
| `POST` | `/negocios` | Cadastra negócio + até 3 concorrentes |
| `POST` | `/simulacoes` | Inicia simulação para um negócio, retorna `id` |
| `GET` | `/simulacoes/{id}/stream` | SSE: envia cada mensagem do debate assim que é gerada |
| `GET` | `/simulacoes/{id}` | Resultado completo: mensagens, relatório, financeiro |

### Tabelas (SQLite)

- `negocio` — dados do formulário (tipo, local, produto, preço, público, divulgação, custos, taxa de plataforma)
- `concorrente` — nome, preço, observação, origem do dado
- `simulacao` — status, data, provedor/modelo usado
- `mensagem` — simulação, persona, rodada, texto, interesse (0–10), compraria
- `relatorio` — JSON do analista + resultado financeiro

---

## 4. Como funciona a parte de LLM

### 4.1 Provedores — um código, vários LLMs

O backend fala com a IA **apenas através da classe `LLMProvider`** (`backend/app/llm/base.py`). O resto do código chama `provider.gerar(prompt, mensagens, Schema)` e recebe um objeto Pydantic já validado, sem saber quem está por trás.

```
                    ┌─────────────────┐
 orquestrador ────► │   LLMProvider   │  gerar() → valida JSON → tenta de novo se inválido
                    └────────┬────────┘
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
   MockProvider     OpenAICompatProvider   GeminiProvider
   (demo_data/)     Groq / Ollama          Google AI Studio
```

| `LLM_PROVIDER` | O que é | Chave | Arquivo |
|---|---|---|---|
| `mock` | Respostas gravadas em `backend/demo_data/` — **padrão da demo pública** | Não | `llm/mock.py` |
| `groq` | Nuvem do Groq rodando modelos abertos (Llama etc.), API no formato OpenAI. **Grátis com limite diário** | [console.groq.com/keys](https://console.groq.com/keys) | `llm/openai_compat.py` |
| `gemini` | Gemini do Google, chave gerada no **Google AI Studio**. Grátis com limite diário | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `llm/gemini.py` |
| `ollama` | Modelo rodando **no seu PC** (não serve para a URL pública) | Não | `llm/openai_compat.py` |

- Groq e Ollama usam o mesmo código (formato OpenAI); muda só o endereço.
- O prompt de sistema recebe automaticamente a lista de campos da resposta; o Pydantic valida e, se vier inválido, há **uma nova tentativa**. (Com o JSON Schema bruto no prompt, o modelo às vezes devolvia o próprio schema — por isso usamos lista de campos.)
- Planos grátis podem usar os dados enviados para treino: **não usar dados reais de empreendedores** com chaves grátis.
- Na URL pública, manter `mock` como padrão para a cota grátis não esgotar com visitantes.

**Modelos configurados e resultados dos testes (2026-11-11):**

| Uso | Groq (padrão) | Gemini (reserva) |
|---|---|---|
| Personas | `openai/gpt-oss-20b` | `gemini-3.5-flash-lite` |
| Analista | `openai/gpt-oss-120b` | um `gemini-*-flash` |
| Tempo por persona | ~2 s | ~4 s |
| Limite grátis observado | **8.000 tokens/minuto** — duas simulações seguidas estouram | não medido ainda |

- Modelos Groq marcados "Enterprise" (ex.: Llama) **não** funcionam no plano grátis. Whisper, Orpheus e Guard não são modelos de conversa.
- Ao bater no limite (erro 429), o cliente espera e tenta de novo sozinho (`max_retries=6`) — a simulação fica mais lenta, mas não falha.
- Uma persona no Gemini Flash-Lite soltou palavras sem sentido no início da fala; o Groq teve qualidade mais estável.
- Para listar modelos disponíveis na sua chave: `python -m scripts.testar_llm --provider groq --listar-modelos`.

### 4.1.1 Como testar (passo a passo)

```powershell
# 1. Na raiz do repositório: criar seu .env (já está no .gitignore)
copy .env.example .env

# 2. Ambiente Python (uma vez)
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Testes automáticos (não precisam de chave)
pytest

# 4. Teste com o mock (não precisa de chave)
python -m scripts.testar_llm
python -m scripts.testar_llm --todas          # as 5 personas em paralelo

# 5. Teste com LLM real: preencha no .env
#    GROQ_API_KEY=...  e  LLM_MODEL_PERSONAS=<nome do modelo no painel do Groq>
python -m scripts.testar_llm --provider groq --todas
#    ou GEMINI_API_KEY=... e um modelo Gemini
python -m scripts.testar_llm --provider gemini --modelo <nome-do-modelo>
```

> 🔒 **Repositório público.** Chaves ficam **só** no `.env` local (ignorado pelo Git). Antes de cada commit, rode `git status` e confira que nenhum `.env`, `.db` ou `.log` aparece. Se uma chave vazar, **revogue-a imediatamente** no painel do provedor e gere outra.

**O `MockProvider`** devolve `backend/demo_data/<schema>.json` (ex.: `opiniao.json`) com pequeno atraso para simular a "digitação" no feed. Quando tivermos um LLM real, gravamos uma boa simulação e ela passa a ser o conteúdo do modo demo — plano B garantido para a apresentação.

### 4.2 Os agentes

| Agente | Implementação | Entrada → Saída |
|---|---|---|
| Agente de contexto | Função Python (sem LLM no MVP) | Formulário + concorrentes → texto de contexto padronizado, com origem dos dados |
| Personas (5) | 1 prompt de sistema por persona | Contexto (+ falas dos outros na rodada 2) → `Opiniao` em JSON |
| Moderador / orquestrador | Python puro (`services/`) | Controla rodadas, chama personas em paralelo (`asyncio.gather`), salva histórico |
| Agente analista | 1 prompt, modelo mais forte | Histórico completo → `Relatorio` em JSON |
| Calculadora | Python puro, **sem LLM** | Preço e custos → margem e ponto de equilíbrio |

**Personas fixas no MVP:** Econômico, Exigente, Ocupado, Crítico e Fiel à região. Cada uma tem nome, idade, renda aproximada, prioridades, restrições e sensibilidade a preço definidas em `agents/personas.py`. Gerar personas dinamicamente fica como melhoria.

### 4.3 Saída estruturada

Toda resposta de agente é **JSON validado com Pydantic**. Isso deixa o dashboard baseado em números, não em interpretação de texto.

```json
// Opiniao (persona, por rodada)
{
  "fala": "<opinião da persona em linguagem natural>",
  "interesse": 5,
  "compraria": "sim | nao | talvez",
  "pontos_positivos": ["<ponto positivo>"],
  "objecoes": ["<objeção>"],
  "mudou_de_opiniao": false
}
```

```json
// Relatorio (analista)
{
  "resumo": "...",
  "pontos_positivos": ["..."],
  "objecoes": ["..."],
  "recomendacoes": ["..."],
  "experimentos_sugeridos": ["<experimento para validar com consumidores reais>"],
  "interesse_por_persona": {"<persona>": 0}
}
```

### 4.4 O debate

```
Rodada 1  →  5 chamadas em paralelo: cada persona vê só o negócio
Rodada 2  →  5 chamadas em paralelo: cada persona vê o negócio + as falas da rodada 1 dos outros
Análise   →  1 chamada: analista recebe todo o histórico
```

- **Memória:** cada persona mantém o próprio histórico de mensagens (lista em Python) — memória curta, só durante a simulação.
- **Evitar concordância excessiva:** LLMs tendem a concordar entre si. O prompt instrui a persona a manter suas prioridades e só mudar de opinião diante de argumento concreto; o campo `mudou_de_opiniao` registra mudanças, que viram destaque no relatório.
- **Custo:** ~11 chamadas por simulação (5 + 5 + 1). Personas podem usar um modelo menor e barato; o analista, um modelo mais capaz.

### 4.5 Linguagem responsável (vale para prompts e interface)

Usar "interesse simulado", "percepção dos agentes", "hipótese a validar". Nunca "chance de sucesso" ou "previsão de vendas". Mostrar aviso de que as opiniões são sintéticas.

---

## 5. Calculadora financeira

Funções puras em `backend/app/services/`, com testes unitários.

```
receita líquida por venda   = preço × (1 − taxa de plataforma%)
margem de contribuição      = receita líquida − custo variável
ponto de equilíbrio         = custo fixo mensal ÷ margem   (vendas/mês, arredondado para cima)
```

| Entrada | Tipo | Observação |
|---|---|---|
| `preco` | R$ | Preço de venda unitário |
| `custo_variavel` | R$ | Custo por unidade vendida |
| `custo_fixo_mensal` | R$ | Aluguel, salários, etc. |
| `taxa_plataforma` | % (0–100) | Comissão de apps/marketplaces; 0 se não houver |

O campo **taxa de plataforma (%)** foi adicionado ao formulário porque pode reduzir muito a margem de negócios que vendem por aplicativos ou marketplaces. O relatório deve listar o que **não** foi considerado (impostos, entrega, perdas, etc.). Se margem ≤ 0, exibir alerta em vez do ponto de equilíbrio.

---

## 6. Deploy e ambiente

| Peça | Onde | Observação |
|---|---|---|
| Frontend | Vercel | `VITE_API_URL` aponta para a URL do backend |
| Backend | Render (Web Service, plano free) | Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Banco | SQLite no disco do Render | Dados podem ser apagados a cada deploy/reinício — aceitável para o MVP |

Atenções:
- O plano free do Render "dorme" após inatividade; a primeira requisição pode levar ~1 min. **Acordar o backend antes da apresentação.**
- Variáveis de ambiente: ver [.env.example](.env.example). Chaves de API só no painel do Render, **nunca** no repositório.
- A demo pública roda com `LLM_PROVIDER=mock` até termos LLM — sem custo e sem risco de abuso da chave.

---

## 7. Plano de execução

### Dia 1 — Fundação
- [x] Estrutura de pastas, README e este documento
- [ ] Scaffold do backend (FastAPI, `main.py`, CORS, `requirements.txt`)
- [ ] Scaffold do frontend (Vite + React + TS, Tailwind)
- [ ] Modelos Pydantic/SQLModel e conexão SQLite
- [ ] `POST /negocios` + formulário enviando dados
- [ ] Primeiro deploy (Vercel + Render) com "hello world"

### Dia 2 — Agentes
- [x] Interface `LLMProvider` + `MockProvider` + `demo_data/` + adaptadores Groq, Gemini e Ollama + script de teste
- [ ] Definição das 5 personas e prompts
- [ ] Orquestrador: rodada 1 e rodada 2 em paralelo, histórico salvo
- [ ] `POST /simulacoes` e `GET /simulacoes/{id}/stream` (SSE)
- [ ] Feed do debate no frontend
- [ ] Testar Groq e Gemini com chaves reais e escolher o padrão

### Dia 3 — Resultado
- [ ] Agente analista + schema `Relatorio`
- [ ] Calculadora financeira + testes
- [ ] Dashboard: interesse por persona, objeções, recomendações, financeiro
- [ ] Avisos de dados sintéticos e despesas não consideradas na interface

### Dia 4 — Estabilização
- [ ] Testes do orquestrador com `MockProvider`
- [ ] Correções e polimento visual
- [ ] Gravar simulação real para o modo demo
- [ ] README com "Como rodar", diagrama do fluxo dos agentes e BMC
- [ ] Ensaio do pitch com a URL pública

### Divisão por frente

| Frente | Responsável | Pastas principais |
|---|---|---|
| Backend | _a definir_ | `backend/app/api`, `services`, `models`, `db` |
| Frontend | _a definir_ | `frontend/src` |
| IA / Agentes | _a definir_ | `backend/app/agents`, `backend/app/llm`, `backend/demo_data` |
| Produto / Validação | _a definir_ | `docs/` (entrevistas, BMC, pitch) |

---

## 8. Decisões

### Tomadas
| Data | Decisão | Motivo |
|---|---|---|
| 2026-11-11 | Backend acessa LLM só via interface `LLMProvider`, com `MockProvider` como padrão | Ainda não temos provedor; permite desenvolver e demonstrar sem custo |
| 2026-11-11 | Demo em URL pública: Vercel + Render | Avaliadores podem testar; ambos têm plano gratuito |
| 2026-11-11 | Saída dos agentes em JSON validado (Pydantic) | Dashboard baseado em números, não em texto livre |
| 2026-11-11 | 5 personas fixas no MVP | Menos variação e menos risco na demo |
| 2026-11-11 | Campo "taxa de plataforma (%)" no cálculo financeiro | Comissões de apps/marketplaces alteram muito a margem e o ponto de equilíbrio |
| 2026-11-11 | Sem LangChain/CrewAI | Orquestração simples em Python puro é suficiente e mais fácil de depurar |

### Pendentes
- [ ] **Provedor de LLM padrão**: Groq ou Gemini (ambos grátis) — testar qualidade das personas e limites diários de cada um.
- [ ] Dados dos concorrentes entram no prompt das personas ou só no relatório?
- [ ] Comparação de cenários (ex.: dois preços ou duas ofertas lado a lado) — fazer se sobrar tempo no Dia 3/4?
- [ ] Responsáveis por cada frente.

---

## 9. Changelog

*Mais recente no topo. Uma linha por commit.*

| Data | Autor | Commit | Mudança |
|---|---|---|---|
| 2026-11-11 | Júlio | `feat: camada de LLM` | Interface `LLMProvider`, provedores mock/Groq/Gemini/Ollama, 5 personas, schema `Opiniao`, script `testar_llm`, testes; `.gitignore` reforçado para repo público |
| 2026-11-11 | Júlio | `docs: estrutura inicial` | Estrutura de pastas, README, DESENVOLVIMENTO.md, `.gitignore`, `.env.example`, resumo da proposta |
