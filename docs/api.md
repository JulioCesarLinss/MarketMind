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
1. POST /simulacoes?demo=true&personas=economico&personas=critico   (dados do formulário)
       →  { "id": "bc7327ef54ca", "status": "rodando", "personas": ["economico", "exigente", ...] }
2. GET  /simulacoes/{id}/stream  →  feed ao vivo, nesta ordem:
       etapa {"etapa":"pesquisa"} → pesquisa (referência de mercado) → mensagem × (2 × personas escolhidas)
       → etapa {"etapa":"analise"} → fim (resultado + relatório + pesquisa)
3. GET  /simulacoes/{id}         →  tudo de uma vez (ex.: ao recarregar a página)
```

| Método | Rota | Para quê |
|---|---|---|
| `GET` | `/health` | API está de pé? |
| `GET` | `/personas` | As 5 personas (id, nome, descrição, prioridades) para montar a escolha e os cards |
| `POST` | `/simulacoes` | Inicia uma simulação. Query `demo=true` = sem IA; `personas=<id>` repetido = quais consumidores participam (mínimo 2; sem o parâmetro, todos; id inexistente ou só 1 → 422). A resposta traz `personas` (ids de quem participa) |
| `GET` | `/simulacoes/{id}/stream` | Feed ao vivo (Server-Sent Events) |
| `GET` | `/simulacoes/{id}` | Estado completo: `status`, `mensagens`, `resultado`, `erro`, `personas` |

Sem IA configurada no servidor e sem `demo=true`, o `POST` responde **503**. Dados inválidos → **422** (o FastAPI diz qual campo).

## 1. Enviar o formulário — `POST /simulacoes`

Campos = formulário do README. `custos`, `entrega` e `concorrentes` são opcionais (no máximo 3 concorrentes).
Dentro de `custos`, todos os campos são opcionais (padrão 0); `lucro_esperado_pct` (0–99) e `investimento_inicial` (R$) podem ser `null`.
Com `custos`, o `fim` traz `relatorio.financeiro` (lucro por venda, ponto de equilíbrio, cenários por clientes/dia, tempo para se pagar); sem `custos`, `financeiro` é `null`.

```json
{
  "tipo": "Barbearia premium",
  "localizacao": "Centro comercial de capital",
  "produto": "Corte + barba com toalha quente e cerveja artesanal de cortesia",
  "preco": 85.0,
  "publico": "Homens de 25 a 45 anos que trabalham em escritório",
  "divulgacao": "Instagram e agendamento por aplicativo",
  "custos": { "custo_fixo_mensal": 12000, "custo_variavel_unitario": 25, "taxa_plataforma_pct": 0, "lucro_esperado_pct": 40, "investimento_inicial": 60000 },
  "entrega": { "disponivel": false, "modelo": null, "taxa": null, "prazo": "", "area": "", "garantias": "" },
  "concorrentes": [
    { "nome": "Barbearia de rua", "preco": 35.0, "observacao": "sem agendamento" },
    { "nome": "Rede de barbearias de shopping", "preco": 70.0, "observacao": "ambiente moderno" }
  ]
}
```

Regras: textos obrigatórios não podem ser vazios; `preco > 0`; preços e custos `≥ 0`; `taxa_plataforma_pct` de 0 a 100.

`entrega` ("o produto pode ser entregue?"): `disponivel` true/false; se true, `modelo` é um de
`proprio`, `app_delivery` (iFood, 99Food), `entregador_parceiro` (motoboy terceirizado, Lalamove, Uber Flash, Loggi),
`correios` ou `outro`; `taxa` em reais (0 = grátis, null = não informada); `prazo`, `area` e `garantias`
(o que torna a entrega confiável) são textos livres. As personas avaliam se o modelo é confiável para o produto.
Sem o campo, as personas não supõem nada sobre entrega.

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
feed.addEventListener("etapa", () => {
  mostrarCarregando("O analista está lendo o debate..."); // chega quando as 10 falas terminam
});
feed.addEventListener("fim", (e) => {
  const resultado: ResultadoSimulacao = JSON.parse(e.data);
  mostrarRelatorio(resultado.relatorio); // pode vir sem `analise` (ver erro_analise)
  feed.close();                       // IMPORTANTE: senão o navegador reconecta sozinho
});
feed.addEventListener("erro", (e) => {
  mostrarErro((e as MessageEvent).data); // texto amigável
  feed.close();
});
```

- Cada simulação real leva **~60–90 s** (10 falas) + **~3–10 s** do analista. No modo demo, ~3 s.
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
  tokens_usados: number;        // debate + analista
  duracao_segundos: number;
  relatorio: Relatorio | null;  // sempre preenchido no evento "fim"
}

// ---- Relatório (dashboard) ----
interface Relatorio {
  indicadores: Indicadores;      // NÚMEROS: calculados pelo código, sempre presentes
  analise: AnaliseDebate | null; // TEXTO: escrito pela IA; null se o analista falhou
  origem_analise: string | null;
  erro_analise: string | null;   // mensagem amigável quando analise == null
  tokens_usados: number;
  duracao_segundos: number;
  aviso: string;                 // mostrar na tela: opiniões sintéticas, hipóteses a validar
}

interface Indicadores {
  preco_ofertado: number;
  interesse_medio_r1: number;    // 0 a 10
  interesse_medio_r2: number;
  decisoes_r2: { sim: number; talvez: number; nao: number };
  preco_maximo_medio: number | null; // compare com preco_ofertado (ótimo para um gráfico)
  preco_maximo_mediano: number | null;
  aceitam_preco: number;              // quantas personas pagariam o preço cobrado
  avaliacao_preco: 'ideal' | 'espaco_para_subir' | 'acima_do_aceito' | 'sem_dados';
  preco_referencia: number | null;   // preço a destacar: o cobrado (maioria aceita) ou a mediana do que pagariam
  mudaram_de_posicao: number;
  por_persona: {
    persona_id: string; persona_nome: string;
    interesse_r1: number; interesse_r2: number;
    compraria_r1: Decisao; compraria_r2: Decisao;
    mudou: boolean;              // critério oficial de mudança de opinião
    preco_maximo: number | null;
  }[];
}

interface AnaliseDebate {
  resumo: string;
  elogios: string[];             // com quem disse entre parênteses
  objecoes: string[];            // da mais citada para a menos
  fatores_de_decisao: string[];
  pontos_de_atencao: string[];   // cada item começa com "Preço:", "Produto:", "Conveniência:" ou "Divulgação:"
  recomendacoes: string[];       // da mais importante para a menos
  experimentos: string[];        // testes com clientes reais
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

**Mudou de opinião?** Use `relatorio.indicadores.por_persona[].mudou` (critério oficial: a decisão mudou **ou** o interesse variou 2+ pontos). Não use `opiniao.mudou_de_opiniao`, que é só o que a IA declarou.

## Pesquisa de mercado (agente pesquisador)

Antes da primeira fala, o backend pesquisa o mercado e envia o evento `pesquisa` (também fica em `resultado.pesquisa`).
Leva ~20–40 s numa simulação real (no modo demo, 0,5 s, com números fictícios avisados em `aviso`).

```ts
fonte.addEventListener('etapa', (e) => {
  const { etapa } = JSON.parse(e.data) // 'pesquisa' | 'analise'
})
fonte.addEventListener('pesquisa', (e) => {
  const pesquisa: PesquisaMercado = JSON.parse(e.data)
})
```

Campos principais de `PesquisaMercado` (tipos completos em `frontend/src/types.ts`):
- `faixas[]`: `popular`, `intermediaria`, `premium`, cada uma com `media`, `desvio_padrao`, `minimo`, `maximo`, `quantidade`,
  `dados_suficientes` e `exemplos[]` (estabelecimento, item, preço, link da fonte).
- `media_geral`, `desvio_padrao_geral`, `total_precos`.
- `posicao`: `preco_usuario`, `desvios_da_media`, `faixa_mais_proxima` e `resumo` (frase pronta).
- `lojas_regiao`: `quantidade` (mínimo mapeado), `nivel_concorrencia` (`baixa` | `media` | `alta` | `nenhum concorrente mapeado` |
  `indeterminado`), `observacao`, `erro`.
- `fontes[]` (título + URL), `erro` (por que os preços falharam; a simulação continua), `aviso` (mostrar na tela).

Exemplo real: [`docs/exemplos/pesquisa-mercado.json`](exemplos/pesquisa-mercado.json).

## Dados de exemplo

[`docs/exemplos/resultado-simulacao.json`](exemplos/resultado-simulacao.json) — uma simulação **real** (barbearia, gpt-oss-120b), no formato `ResultadoSimulacao`, **com o relatório do analista**. Bom para montar as telas sem subir a API.

## Ainda não existe (vai entrar na API depois)

- **Indicadores financeiros** (margem, ponto de equilíbrio) — calculados a partir de `custos`; vão entrar dentro de `relatorio`.
- **Histórico salvo**: hoje as simulações ficam em memória; se o servidor reiniciar, somem.

## Lembrete de linguagem (vale para a interface)

Usar "interesse simulado", "percepção dos agentes", "hipótese a validar". Nunca "chance de sucesso" ou "previsão de vendas". Mostrar aviso de que as opiniões são sintéticas.
