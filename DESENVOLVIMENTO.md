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

### Endpoints

Implementados: `GET /health`, `GET /personas`, `POST /simulacoes` (`?demo=true` = sem IA), `GET /simulacoes/{id}/stream` (SSE), `GET /simulacoes/{id}`. Guia completo para o frontend: [docs/api.md](docs/api.md). O cadastro separado de negócios (`POST /negocios`) ficou para quando houver SQLite: por enquanto o formulário vai direto no `POST /simulacoes`.

Plano original:

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
| Analista | `openai/gpt-oss-120b` | `gemini-3.5-flash` |
| Tempo por persona | ~2 s | ~2–4 s |
| Limite grátis observado | **8.000 tokens/minuto** — duas simulações seguidas estouram | `gemini-3.5-flash` deu erro 503 (sobrecarga) em um teste |

- Modelos Groq marcados "Enterprise" (ex.: Llama) **não** funcionam no plano grátis. Whisper, Orpheus e Guard não são modelos de conversa.
- Uma persona no Gemini Flash-Lite soltou palavras sem sentido no início da fala uma vez; no reteste respondeu normalmente.
- Para listar modelos disponíveis na sua chave: `python -m scripts.testar_llm --provider groq --listar-modelos`.

### 4.1.0 Reserva automática (fallback)

`criar_provider()` monta uma **cadeia**: cada chamada tenta o primeiro; se falhar, passa ao próximo.

```
Groq (principal) ──falhou?──► Gemini (reserva) ──falhou?──► mock (respostas gravadas)
```

- **Por que reserva e não "em conjunto":** todas as personas de uma simulação devem vir do mesmo modelo, senão não dá para saber se uma nota diferente veio do perfil ou do modelo. A reserva só entra em falha.
- **O que conta como falha:** limite estourado (429) após novas tentativas, servidor sobrecarregado (503), falta de conexão, modelo inexistente, resposta em formato inválido.
- **Novas tentativas antes de desistir:** Groq tenta 3 vezes (`max_retries=3`); Gemini tenta 3 vezes em 429/500/503, esperando 2 s e 4 s.
- **Rastreio:** `gerar_com_origem()` devolve a resposta **e quem respondeu** (ex.: `gemini/gemini-3.5-flash-lite`). O orquestrador deve salvar isso em cada mensagem, para o relatório indicar se a reserva foi usada.
- **Configuração** (`.env`): `LLM_FALLBACK_PROVIDER`, `LLM_FALLBACK_MODEL_PERSONAS`, `LLM_FALLBACK_MODEL_ANALISTA`, `LLM_MOCK_NO_FIM`. Com `--provider X` no script, testa só aquele provedor, sem reserva.
- **Testado:** com um modelo Groq inexistente, o Gemini assumiu automaticamente em ~2 s.

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
  "mudou_de_opiniao": false,
  "preco_maximo": 12.0,        // quanto pagaria no máximo (ou null) → alimenta a calculadora
  "o_que_mudaria": "<o que faria mudar de decisão>"
}
```

```json
// Relatorio (dentro de ResultadoSimulacao.relatorio)
{
  "indicadores": {                      // calculados pelo CÓDIGO
    "preco_ofertado": 85.0, "interesse_medio_r1": 4.2, "interesse_medio_r2": 4.6,
    "decisoes_r2": {"sim": 1, "talvez": 1, "nao": 3}, "preco_maximo_medio": 67.5,
    "mudaram_de_posicao": 2, "por_persona": ["..."]
  },
  "analise": {                          // escrita pela IA (null se falhar)
    "resumo": "...", "elogios": ["..."], "objecoes": ["..."], "fatores_de_decisao": ["..."],
    "pontos_de_atencao": ["Preço: ..."], "recomendacoes": ["..."], "experimentos": ["..."]
  },
  "origem_analise": "groq/openai/gpt-oss-120b",
  "aviso": "Opiniões geradas por IA (consumidores sintéticos)..."
}
```

**Agente analista** (`agents/analista.py`):
- **Números pelo código, texto pela IA:** `calcular_indicadores()` calcula interesse médio, decisões, preço máximo médio e quem mudou. A IA recebe esses números prontos, com a ordem de não recalcular nem inventar.
- **Entrada:** dados do negócio + transcrição das 2 rodadas (fala, nota, decisão, do que gostou, objeções, sugestão) + indicadores.
- **Regras:**
  - citar quem disse cada coisa;
  - recomendações viáveis ligadas às objeções, aproveitando as sugestões das personas;
  - experimentos que dizem o que medir;
  - linguagem de "hipóteses a validar".
- **Sem mock no fim da cadeia** (`criar_provider(papel="analista", mock_no_fim=False)`): um relatório gravado de outro negócio seria enganoso. Se Groq e Gemini falharem, o resultado vem com os números e `erro_analise`, e o debate não se perde.
- **Teste real** (debate da barbearia, gpt-oss-120b): ~4 mil tokens, ~3 s.
  - **Bom:** usou os números certos ("R$ 85 acima do preço máximo médio de R$ 67,50"), aproveitou as sugestões das personas e propôs experimentos mensuráveis.
  - **A observar:** às vezes atribui um elogio a todas as personas quando só algumas o citaram.

### 4.4 O debate

```
Rodada 1  →  5 chamadas em paralelo: cada persona vê só o negócio
Rodada 2  →  5 chamadas em paralelo: cada persona vê o negócio + as falas da rodada 1 dos outros
Análise   →  1 chamada: analista recebe todo o histórico
```

- **Memória:** cada persona mantém o próprio histórico de mensagens (lista em Python) — memória curta, só durante a simulação.
- **Evitar concordância excessiva:** LLMs tendem a concordar entre si. O prompt instrui a persona a manter suas prioridades e só mudar de opinião diante de argumento concreto; o campo `mudou_de_opiniao` registra mudanças, que viram destaque no relatório.
- **Custo:** ~11 chamadas por simulação (5 + 5 + 1). Personas podem usar um modelo menor e barato; o analista, um modelo mais capaz.

**Implementação** (`backend/app/services/orquestrador.py`):

| Peça | Arquivo | Função |
|---|---|---|
| `Orquestrador.executar(negocio)` | `services/orquestrador.py` | Roda rodada 1 → rodada 2 e devolve `ResultadoSimulacao` |
| Memória por persona | `Orquestrador.memoria` | Histórico próprio de cada uma: pedido r1, resposta r1, pedido r2 |
| Textos das rodadas | `agents/debate.py` | Rodada 2 recebe só um **resumo** das falas dos outros (fala, nota, decisão) |
| Limite de chamadas simultâneas | `LLM_CONCORRENCIA` (padrão 2) | Reduz estouro do limite por minuto |
| Aviso a cada fala | `ao_publicar` | Hoje imprime no terminal; a API vai usar para o feed ao vivo (SSE) |
| Formatos | `models/schemas.py` | `MensagemDebate` (fala + persona + rodada + origem) e `ResultadoSimulacao` |

Rodar: `python -m scripts.simular` (ou `--provider mock` para não gastar cota; `--salvar arquivo.json` para salvar).

**Primeira simulação real (Groq, 2026-11-11):**
- Funcionou de ponta a ponta: na rodada 2 as personas citaram umas às outras pelo nome e **2 de 5 mudaram de opinião** com justificativa.
- **~14.700 tokens por simulação**, acima do limite de 8.000/minuto do Groq grátis → as últimas falas esperaram 12–29 s. Tempo total: ~46 s.
- **Problema de qualidade:** todas as falas da rodada 2 começaram com "Concordo com..." e várias notas ficaram em 5. Próximo passo: ajustar prompts para gerar discordância real e notas mais variadas.
- **Ideia para reduzir tokens:** o `gpt-oss` é um modelo de raciocínio; configurar esforço de raciocínio baixo pode cortar muitos tokens (a testar).

**Refinamento das personas** (`agents/personas.py`, `agents/debate.py`):
- **Personas genéricas, que se adaptam ao negócio:** não sabemos o que o usuário vai cadastrar, então os perfis descrevem atitudes (preço, qualidade, tempo, diferenciação, proximidade), sem citar nenhum ramo. A regra "Como pensar" manda cada persona entender primeiro como aquele tipo de negócio funciona (produto ou serviço; presencial, entrega, agendamento ou online) e traduzir suas prioridades para ele. Exemplo: "rapidez" numa barbearia vira horário fácil de marcar, não "corte em 15 min". Um teste garante que nenhuma persona cita "entrega", "delivery", "app" etc.
- **Personas mais ricas:** `perfil_vida`, `jeito_de_falar`, `convence_se_com`, `contradicao` (conflito interno) e `discorda_de` (um tipo de opinião que incomoda, não uma persona fixa, para as respostas não convergirem todas na mesma pessoa).
- **Regras comuns** (`REGRAS`):
  - a maioria NÃO compra de negócio novo;
  - explicar o raciocínio com detalhes concretos da oferta;
  - citar ao menos uma objeção e não repetir os outros;
  - ler TODOS os campos antes de dizer que falta algo (o agendamento, por exemplo, pode estar em "Divulgação");
  - não inventar números nem características;
  - régua de notas com coerência ("sim" exige 7+, "nao" exige 4 ou menos).
- **Entrada do usuário:** usa só os campos do formulário do README. Sem concorrentes cadastrados, o contexto diz "nenhum concorrente informado", para ninguém inventar.
- **Rodada 2** (continua sendo "cada persona reage às opiniões das outras", como no README):
  - recebe de cada outra persona a fala, a nota, a decisão, **do que gostou**, a **principal objeção** e a **sugestão ao dono**, que são a informação nova capaz de mudar uma opinião;
  - começa respondendo a quem mais discorda, depois comenta o que mexeu com a própria avaliação;
  - proibido começar com "Concordo";
  - as falas chegam **embaralhadas** (semente opcional em `Orquestrador(semente=...)`);
  - pode mudar a nota quando algo do debate a convencer, deixando claro se depende de o dono adotar uma sugestão.
- **Resposta** ganhou `preco_maximo` (vai alimentar a calculadora) e `o_que_mudaria` (uma mudança realista que o dono conseguiria fazer). A fala tem de 2 a 4 frases com argumentos concretos.
- **Tentativas que pioraram e foram desfeitas:**
  - frase de exemplo por persona: o modelo copiava literalmente;
  - limite de 3 frases e roteiro rígido "cite 2 pessoas": falas superficiais;
  - "sugestões não mudam a nota": ninguém mudava de opinião;
  - "se faltar algo, diga que faltou": a persona dizia que não havia agendamento, mas ele estava no campo Divulgação.
- **Tokens:** `LLM_REASONING_EFFORT=low` é enviado aos modelos `gpt-oss` (padrão `low`; vazio = não enviar).

**Medir a qualidade:** `python -m scripts.avaliar_personas --negocio cafeteria` (ou `--todos`, ou `--provider mock`; `--salvar arquivo.json`). As métricas estão em `services/metricas.py`. Há 4 negócios de exemplo em `agents/exemplos.py` (`cafeteria`, `barbearia`, `roupas`, `marmita`), que também servem para `python -m scripts.simular --negocio barbearia`.

| Métrica (Groq, 2026-11-11) | Prompt original (cafeteria) | Atual, gpt-oss-20b (barbearia) | Atual, gpt-oss-120b (barbearia) | Meta |
|---|---|---|---|---|
| Falas da rodada 2 começando com "Concordo" | 100% | **0%** | **0%** | < 40% |
| Falas da rodada 2 citando 2+ personas | — | 80% | **100%** | ≥ 60% |
| Persona mais citada (% das citações) | — | 33% | 30% | ≤ 40% |
| Palavras por fala (rodada 2) | — | 82 | 83 | — |
| Amplitude das notas (rodada 1 → 2) | 3 → 3 | 1 → 1 | 2 → **4** | ≥ 4 |
| Mudaram de posição | 1 | 2 | 2 | — |
| Tokens | 14.419 | 20.470 | 21.290 | < 10 mil ❌ |

Observações:
- **O modelo pesa mais que o prompt.** Com o 20b, as falas ainda escorregam: saem do personagem ("eu curto o toque de personalização", dito pelo Econômico) e inventam dados ("a concorrência também dá cerveja"). Com o **120b**, cada persona fica no personagem, usa os dados reais (R$ 35 na rua, R$ 70 no shopping, o app) e propõe sugestões criativas ("desconto para marcações pelo app", "retoque gratuito"). **Recomendação:** `LLM_MODEL_PERSONAS=openai/gpt-oss-120b`.
- **Tokens:** cerca de 85% é texto de entrada (regras + formato + negócio, repetidos em cada uma das 10 chamadas; na rodada 2, também o histórico e o resumo dos outros). Passa dos 8 mil/min do Groq grátis, então as últimas falas esperam ou vão para a reserva Gemini (simulação de 75–85 s).

**Fica para depois do MVP:** mais personas (impulsiva, desconfiada de negócio novo, não-consumidor) e várias instâncias por arquétipo, pois cada persona custa ~2 chamadas; adaptar as personas ao negócio com IA; validar as respostas com clientes reais de alguns negócios (bom argumento para a apresentação).

### 4.4.1 Agente pesquisador (referência de mercado)

`agents/pesquisador.py` roda **antes do debate** e gera um JSON (`PesquisaMercado`) que entra no contexto das personas e do analista.

1. **IA planeja** (modelo das personas): tipo de estabelecimento, produto comparável, cidade, categoria do mapa (de uma **lista fechada** em `services/mapa.py`) e palavras do nome.
2. **O código monta 3 buscas** (geral, "barato popular", "premium") e busca no **Tavily** (`services/busca/`, mesmo padrão da camada de LLM, com reserva opcional).
3. **Ao mesmo tempo, conta lojas** no OpenStreetMap: o Nominatim acha as coordenadas e o Overpass conta num raio de 2 km (3 servidores consultados em paralelo). Se o Overpass falhar, há o plano B, a busca por nome no Nominatim, marcada como **parcial**: nível de concorrência "indeterminado" e sem nomes.
4. **O código recorta só os trechos com "R$"** (no máximo 25, descartando valores fora de 0,2×–5× o preço do usuário) e a **IA extrai** os exemplos (modelo do analista).
5. **O código valida e calcula:**
   - aceita só preços escritos no trecho citado;
   - no máximo 3 por loja;
   - com 6 ou mais preços, as faixas são os **terços da distribuição de preços**;
   - calcula média, desvio-padrão, mínimo e máximo por faixa e no geral;
   - calcula a posição do preço do usuário (diferença em % e em desvios-padrão).

**Falhas:** cada parte falha sozinha (`erro` no JSON) e a simulação segue. Se a pesquisa não trouxer dados, ela nem entra no prompt das personas. Há **cache** de 24 h por negócio.

**Comandos:** `python -m scripts.testar_busca` confere as chaves e o mapa; `python -m scripts.pesquisar --negocio barbearia --salvar pesquisa.json` gera o JSON; `python -m scripts.simular` mostra a pesquisa antes do debate (`--sem-pesquisa` para pular).

**Chaves:** `TAVILY_API_KEY` (grátis, 1.000 buscas/mês, sem cartão: https://app.tavily.com). A busca do Ollama (`OLLAMA_API_KEY`) foi implementada como reserva, mas **exige créditos pagos** (erro 402 no teste).

**Testes reais (2026-11-12):**
- **Barbearia** (Boa Viagem, R$ 85): 7 preços confirmados de barbearias reais (Booksy, Trois, Baffi, Savoie), média R$ 94,71 ± R$ 31,54, faixas R$ 51 / R$ 100 / R$ 130. Levou ~21 s e ~7 mil tokens.
- **Marmitaria** (Graças, R$ 26): 7 preços, média R$ 21,07, "23% acima da média, 1,6 desvio-padrão".
- **Overpass:** os 3 servidores públicos estavam fora do ar nos testes, então a contagem ficou parcial (plano B). No Render pode funcionar: conferir.

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
- [x] Scaffold do backend (FastAPI, `main.py`, CORS, `requirements.txt`)
- [ ] Scaffold do frontend (Vite + React + TS, Tailwind)
- [ ] Modelos Pydantic/SQLModel e conexão SQLite
- [ ] `POST /negocios` + formulário enviando dados
- [ ] Primeiro deploy (Vercel + Render) com "hello world"

### Dia 2 — Agentes
- [x] Interface `LLMProvider` + `MockProvider` + `demo_data/` + adaptadores Groq, Gemini e Ollama + script de teste
- [x] Definição das 5 personas e prompts
- [x] Orquestrador: rodada 1 e rodada 2 com memória por persona e limite de concorrência (script `simular`) — histórico ainda não vai para o banco
- [x] `POST /simulacoes` e `GET /simulacoes/{id}/stream` (SSE)
- [ ] Feed do debate no frontend
- [x] Testar Groq e Gemini com chaves reais e escolher o padrão (Groq principal, Gemini reserva)

### Dia 3 — Resultado
- [x] Agente analista + schema `Relatorio`
- [ ] Calculadora financeira + testes
- [ ] Dashboard: interesse por persona, objeções, recomendações, financeiro
- [ ] Avisos de dados sintéticos e despesas não consideradas na interface

### Dia 4 — Estabilização
- [x] Testes do orquestrador com `MockProvider`
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
| 2026-11-12 | Agente pesquisador com Tavily (busca) + OpenStreetMap (contagem de lojas) | Tavily é grátis sem cartão; a busca do Ollama exige créditos e o ScrapeGraphAI tem só 500 créditos únicos; Google Places exige cartão |
| 2026-11-12 | Números da pesquisa calculados pelo código (preço precisa estar escrito no trecho; faixas por terços de preço) | Evita preço inventado pela IA e faixas "todas no meio" |
| 2026-11-11 | Backend acessa LLM só via interface `LLMProvider`, com `MockProvider` como padrão | Ainda não temos provedor; permite desenvolver e demonstrar sem custo |
| 2026-11-11 | Demo em URL pública: Vercel + Render | Avaliadores podem testar; ambos têm plano gratuito |
| 2026-11-11 | Saída dos agentes em JSON validado (Pydantic) | Dashboard baseado em números, não em texto livre |
| 2026-11-11 | 5 personas fixas no MVP | Menos variação e menos risco na demo |
| 2026-11-11 | Campo "taxa de plataforma (%)" no cálculo financeiro | Comissões de apps/marketplaces alteram muito a margem e o ponto de equilíbrio |
| 2026-11-11 | Sem LangChain/CrewAI | Orquestração simples em Python puro é suficiente e mais fácil de depurar |

### Pendentes
- [x] **Provedor de LLM**: Groq principal, Gemini reserva automática, mock como último recurso.
- [ ] Dados dos concorrentes entram no prompt das personas ou só no relatório?
- [ ] Comparação de cenários (ex.: dois preços ou duas ofertas lado a lado) — fazer se sobrar tempo no Dia 3/4?
- [ ] Responsáveis por cada frente.

---

## 9. Changelog

*Mais recente no topo. Uma linha por commit.*

| Data | Autor | Commit | Mudança |
|---|---|---|---|
| 2026-11-12 | Júlio | `feat: escolha das personas no formulário` | Volta para as 5 personas originais; em vez da quantidade, o usuário escolhe QUAIS participam (cards clicáveis, mínimo 2; API `?personas=<id>` repetido); seletor do modelo de entrega com o mesmo estilo dos outros campos; ícones das personas em `personaIcones.ts` |
| 2026-11-12 | Júlio | `feat: escolha de agentes, entrega e pesquisa mais completa` | Usuário escolhe de 2 a 8 consumidores (`?agentes=`; 3 personas novas: Conectada, de Família, Consciente); campo `entrega` (modelo, taxa, prazo, área, o que a torna confiável) no formulário e no contexto; Exigente reescrito (avalia o que é descrito, sem pedir certificado) + regra comum contra exigir certificação; pesquisador lê 8 páginas por busca e até 40 trechos por rodada, faz até 2 rodadas extras de busca quando vêm menos de 12 preços ou 5 lojas, e divide em 3 faixas a partir de 3 preços (barbearia: 5 → 12 preços); contagem de lojas pelo Nominatim por categoria (o Overpass público vive fora do ar), rodando junto com o Overpass; 9 testes novos |
| 2026-11-12 | Júlio | `feat: agente pesquisador de mercado` | Busca de preços na internet (Tavily, reserva Ollama) + contagem de lojas no OpenStreetMap; faixas popular/intermediária/premium com média e desvio-padrão; posição do preço do usuário; nível de concorrência; JSON entra no contexto das personas e do analista; eventos SSE `etapa pesquisa` e `pesquisa`; seção "Mercado na região" no front; scripts `pesquisar` e `testar_busca`; 20 testes novos |
| 2026-11-12 | Júlio | `feat: relatório do analista no frontend` | Tela de resultado mostra resumo, recomendações, fatores de decisão, pontos de atenção (com etiqueta da área), experimentos e o card "preço que pagariam × preço cobrado"; usa os indicadores do backend; status "analista escrevendo" no evento `etapa`; aviso quando o analista falha |
| 2026-11-12 | Júlio | `feat: agente analista` | `agents/analista.py`: indicadores calculados pelo código + análise em texto pela IA (resumo, elogios, objeções, fatores, pontos de atenção, recomendações, experimentos); schemas `Relatorio`/`Indicadores`/`AnaliseDebate`; sem mock no fim da cadeia do analista; API envia evento `etapa` e o relatório no `fim`; `simular.py` imprime o relatório (`--sem-analista` para pular); `demo_data/analisedebate.json`; exemplo real atualizado em `docs/exemplos/`; 5 testes novos |
| 2026-11-12 | Júlio | `feat: API FastAPI com feed ao vivo` | `app/main.py` (CORS via `FRONTEND_URL`), rotas `/health`, `/personas`, `/simulacoes` (+ `?demo=true`), `/simulacoes/{id}`, `/simulacoes/{id}/stream` (SSE com ping); `NegocioEntrada` (campos do README, até 3 concorrentes); simulações em memória com replay para quem conecta atrasado; `docs/api.md` + exemplo real em `docs/exemplos/`; 6 testes novos |
| 2026-11-11 | Júlio | `feat: personas genéricas e debate com discordância real` | Personas sem ramo fixo que se adaptam ao tipo de negócio; vida, tom, contradição; régua de notas, "leia todos os campos" e "não invente dados"; rodada 2 com o que os outros gostaram, objeções e sugestões, sem "Concordo", falas embaralhadas; testes com gpt-oss-120b para personas; `preco_maximo`/`o_que_mudaria`; `reasoning_effort=low`; 4 negócios de exemplo; `avaliar_personas` + `metricas.py`; 7 testes novos. "Concordo" na rodada 2: 100% → 0% |
| 2026-11-11 | Júlio | `fix: mudança de opinião calculada pelo código` | `mudou_de_posicao()`: mudou a decisão de compra ou a nota variou 2+ pontos — a IA às vezes declarava errado; resumo mostra quais falas usaram a reserva |
| 2026-11-11 | Júlio | `feat: orquestrador do debate` | `Orquestrador` (2 rodadas, memória por persona, concorrência limitada, aviso por fala), `MensagemDebate`/`ResultadoSimulacao`, contagem de tokens nos provedores, script `simular`, 5 testes novos; 1ª simulação real: ~14,7k tokens, 2 de 5 mudaram de opinião |
| 2026-11-11 | Júlio | `feat: reserva Groq → Gemini → mock` | `FallbackProvider`, `gerar_com_origem` (registra quem respondeu), novas tentativas no Gemini em 429/503, variáveis `LLM_FALLBACK_*` no `.env.example`, 4 testes novos |
| 2026-11-11 | Júlio | `feat: camada de LLM` | Interface `LLMProvider`, provedores mock/Groq/Gemini/Ollama, 5 personas, schema `Opiniao`, script `testar_llm`, testes; `.gitignore` reforçado para repo público |
| 2026-11-11 | Júlio | `docs: estrutura inicial` | Estrutura de pastas, README, DESENVOLVIMENTO.md, `.gitignore`, `.env.example`, resumo da proposta |
