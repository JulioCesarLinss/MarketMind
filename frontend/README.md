# Frontend MarketMind

Interface em React + Vite + TypeScript integrada à API FastAPI existente.

## Rodar localmente (Windows / PowerShell)

1. Deixe o backend rodando em `http://localhost:8000`.
2. Abra outro terminal e entre nesta pasta:

   ```powershell
   cd frontend
   npm install
   copy .env.example .env
   npm run dev
   ```

3. Abra `http://localhost:5173`.

O projeto requer Node.js 20.19+ ou 22.12+.

## Endereço da API

A variável `VITE_API_URL` em `.env` define o endereço do backend. O padrão é `http://localhost:8000`.

## Integração existente

- `GET /personas`: carrega do backend os cinco perfis de consumidor.
- `POST /simulacoes`: envia o formulário no schema `NegocioEntrada`.
- `POST /simulacoes?demo=true`: inicia a mesma simulação usando as respostas de demonstração do backend.
- `GET /simulacoes/{id}/stream`: recebe as falas reais pelo Server-Sent Events (SSE).

O nome e a descrição informados pelo usuário são combinados no campo `produto`, pois o schema atual do backend não possui um campo separado para nome. Os campos `tipo`, `localizacao`, `preco`, `publico` e `divulgacao` são obrigatórios na API; custos e concorrentes são opcionais.

A tela de resultado utiliza somente os dados retornados pelo backend. O relatório de um agente analista e os cálculos financeiros avançados não foram simulados no frontend porque ainda não estão disponíveis na API atual.
