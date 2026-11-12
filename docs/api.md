# API do MarketMind — guia para o frontend

Base local: `http://localhost:8000` · Documentação interativa (testar pelo navegador): **http://localhost:8000/docs**

## Subir a API na sua máquina

```powershell
cd backend
py -3.12 -m venv .venv            # só na primeira vez
.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # só na primeira vez (ou quando mudar)
uvicorn app.main:app --reload
```

Você **não precisa de chave de IA** para desenvolver o front: use `?demo=true` (respostas gravadas, ~3 s por simulação).
O CORS já libera `http://localhost:5173` (porta padrão do Vite).

## Fluxo

```
1. POST /simulacoes?demo=true   (dados do formulário)  →  { "id": "bc7327ef54ca", "status": "rodando" }
2. GET  /simulacoes/{id}/stream  →  feed ao vivo: uma fala por evento, depois o evento "fim"
3. GET  /simulacoes/{id}         →  tudo de uma vez (ex.: ao recarregar a página)
```

| Método | Rota | Para quê |
|---|---|---|
| `GET` | `/health` | API está de pé? |
| `GET` | `/personas` | As 5 personas (id, nome, descrição, prioridades) para montar os cards |
| `POST` | `/simulacoes` | Inicia uma simulação. Query `demo=true` = sem IA |
| `GET` | `/simulacoes/{id}/stream` | Feed ao vivo (Server-Sent Events) |
| `GET` | `/simulacoes/{id}` | Estado completo: `status`, `mensagens`, `resultado`, `erro` |

Sem IA configurada no servidor e sem `demo=true`, o `POST` responde **503**. Dados inválidos → **422** (o FastAPI diz qual campo).

## 1. Enviar o formulário — `POST /simulacoes`

Campos = formulário do README. `custos` e `concorrentes` são opcionais (no máximo 3 concorrentes).

```json
{
  "tipo": "Barbearia premium",
  "localizacao": "Centro comercial de capital",
  "produto": "Corte + barba com toalha quente e cerveja artesanal de cortesia",
  "preco": 85.0,
  "publico": "Homens de 25 a 45 anos que trabalham em escritório",
  "divulgacao": "Instagram e agendamento por aplicativo",
  "custos": { "custo_fixo_mensal": 12000, "custo_variavel_unitario": 25, "taxa_plataforma_pct": 0 },
  "concorrentes": [
    { "nome": "Barbearia de rua", "preco": 35.0, "observacao": "sem agendamento" },
    { "nome": "Rede de barbearias de shopping", "preco": 70.0, "observacao": "ambiente moderno" }
  ]
}
```

Regras: textos obrigatórios não podem ser vazios; `preco > 0`; preços e custos `≥ 0`; `taxa_plataforma_pct` de 0 a 100.

## 2. Feed ao vivo — `GET /simulacoes/{id}/stream`

Usa o `EventSource` nativo do navegador (não precisa de biblioteca):

```ts
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const r = await fetch(`${API}/simulacoes?demo=true`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(formulario),
});
const { id } = await r.json();

const feed = new EventSource(`${API}/simulacoes/${id}/stream`);
feed.addEventListener("mensagem", (e) => {
  const msg: MensagemDebate = JSON.parse(e.data);
  adicionarNoFeed(msg);               // chega uma fala por vez (rodada 1, depois rodada 2)
});
feed.addEventListener("fim", (e) => {
  const resultado: ResultadoSimulacao = JSON.parse(e.data);
  mostrarResumo(resultado);
  feed.close();                       // IMPORTANTE: senão o navegador reconecta sozinho
});
feed.addEventListener("erro", (e) => {
  mostrarErro((e as MessageEvent).data); // texto amigável
  feed.close();
});
```

- Cada simulação real leva **~60–90 s** (10 falas). No modo demo, ~3 s.
- Quem conecta atrasado (ou recarrega a página) recebe primeiro as falas que já aconteceram.
- Linhas `: ping` a cada 15 s mantêm a conexão viva; o `EventSource` as ignora.

## Tipos (TypeScript)

```ts
type Decisao = "sim" | "nao" | "talvez";

interface Opiniao {
  fala: string;                 // texto da persona (2 a 4 frases)
  interesse: number;            // 0 a 10
  compraria: Decisao;
  pontos_positivos: string[];
  objecoes: string[];
  mudou_de_opiniao: boolean;    // o que a IA DECLAROU (use comparar rodadas para o número oficial)
  preco_maximo: number | null;  // quanto pagaria no máximo
  o_que_mudaria: string;        // sugestão ao dono
}

interface MensagemDebate {
  persona_id: "economico" | "exigente" | "ocupado" | "critico" | "fiel_regiao";
  persona_nome: string;
  rodada: 1 | 2;
  opiniao: Opiniao;
  origem: string;               // ex.: "groq/openai/gpt-oss-120b" ou "gemini/..." (reserva) ou "mock/demo"
  duracao_segundos: number;
}

interface ResultadoSimulacao {
  mensagens: MensagemDebate[];  // 5 da rodada 1 + 5 da rodada 2
  rodadas: number;
  provedor_principal: string;
  tokens_usados: number;
  duracao_segundos: number;
}

interface SimulacaoEstado {      // GET /simulacoes/{id}
  id: string;
  status: "rodando" | "concluida" | "erro";
  negocio: object;
  mensagens: MensagemDebate[];
  resultado: ResultadoSimulacao | null;
  erro: string | null;
}
```

**Mudou de opinião?** O critério oficial (o mesmo do backend) é: a decisão `compraria` mudou entre a rodada 1 e a 2 **ou** o `interesse` variou 2 pontos ou mais. Compare as duas falas da mesma `persona_id`.

## Dados de exemplo

[`docs/exemplos/resultado-simulacao.json`](exemplos/resultado-simulacao.json) — uma simulação **real** (barbearia, gpt-oss-120b), no formato `ResultadoSimulacao`. Bom para montar as telas sem subir a API.

## Ainda não existe (vai entrar na API depois)

- **Relatório do analista** (resumo, objeções, recomendações, experimentos) — vai aparecer dentro de `resultado`.
- **Indicadores financeiros** (margem, ponto de equilíbrio) — calculados a partir de `custos`.
- **Histórico salvo**: hoje as simulações ficam em memória; se o servidor reiniciar, somem.

## Lembrete de linguagem (vale para a interface)

Usar "interesse simulado", "percepção dos agentes", "hipótese a validar". Nunca "chance de sucesso" ou "previsão de vendas". Mostrar aviso de que as opiniões são sintéticas.
