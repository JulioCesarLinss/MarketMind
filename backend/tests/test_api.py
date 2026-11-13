"""Testes da API (modo demo: sem chave nem internet)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.agents.exemplos import NEGOCIOS
from app.agents.personas import PERSONAS
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def ler_eventos(client, id_):
    """Lê o feed SSE até o fim e devolve [(tipo, dados), ...]."""
    eventos, tipo = [], None
    with client.stream("GET", f"/simulacoes/{id_}/stream") as resposta:
        assert resposta.headers["content-type"].startswith("text/event-stream")
        for linha in resposta.iter_lines():
            if linha.startswith("event: "):
                tipo = linha[7:]
            elif linha.startswith("data: "):
                eventos.append((tipo, linha[6:]))
    return eventos


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_personas(client):
    personas = client.get("/personas").json()
    assert [p["id"] for p in personas] == list(PERSONAS)


def test_simulacao_demo_completa(client):
    criada = client.post("/simulacoes?demo=true", json=NEGOCIOS["barbearia"])
    assert criada.status_code == 201
    id_ = criada.json()["id"]

    eventos = ler_eventos(client, id_)
    mensagens = [json.loads(d) for t, d in eventos if t == "mensagem"]
    assert len(mensagens) == len(PERSONAS)  # 1 opinião por consumidor (sem debate)
    pareceres = [json.loads(d) for t, d in eventos if t == "parecer"]
    assert len(pareceres) == 6 and criada.json()["especialistas"][0] == "precificacao"
    assert criada.json()["personas"] == list(PERSONAS)
    assert eventos[-1][0] == "fim"
    assert eventos[-2] == ("etapa", '{"etapa": "analise"}')  # aviso antes do relatório
    # Pesquisa de mercado vem antes da primeira fala
    assert eventos[0] == ("etapa", '{"etapa": "pesquisa"}')
    assert eventos[1][0] == "pesquisa" and json.loads(eventos[1][1])["total_precos"] > 0
    assert eventos[2][0] in ("mensagem", "parecer")
    final = json.loads(eventos[-1][1])
    assert final["rodadas"] == 1 and len(final["pareceres"]) == 6
    assert final["relatorio"]["analise"]["recomendacoes"]
    assert final["relatorio"]["indicadores"]["preco_ofertado"] == NEGOCIOS["barbearia"]["preco"]

    estado = client.get(f"/simulacoes/{id_}").json()
    assert estado["status"] == "concluida"
    assert len(estado["mensagens"]) == len(PERSONAS) and len(estado["pareceres"]) == 6

    # Quem conecta depois do fim recebe tudo de novo (ex.: recarregou a página)
    assert len(ler_eventos(client, id_)) == len(eventos)


def test_simulacao_inexistente(client):
    assert client.get("/simulacoes/naoexiste").status_code == 404
    assert client.get("/simulacoes/naoexiste/stream").status_code == 404


def test_validacao_do_formulario(client):
    negocio = dict(NEGOCIOS["barbearia"])
    assert client.post("/simulacoes?demo=true", json={**negocio, "preco": -1}).status_code == 422
    quatro = [{"nome": f"C{i}", "preco": 10} for i in range(4)]
    assert client.post("/simulacoes?demo=true", json={**negocio, "concorrentes": quatro}).status_code == 422


def test_cors_libera_o_vite(client):
    resposta = client.options(
        "/simulacoes",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert resposta.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_escolhe_quais_personas(client):
    rota = "/simulacoes?demo=true&personas=critico&personas=economico&personas=fiel_regiao"
    criada = client.post(rota, json=NEGOCIOS["barbearia"]).json()
    assert criada["personas"] == ["economico", "critico", "fiel_regiao"]  # na ordem padrão
    mensagens = [json.loads(d) for t, d in ler_eventos(client, criada["id"]) if t == "mensagem"]
    assert len(mensagens) == 3 and {m["persona_id"] for m in mensagens} == {"economico", "critico", "fiel_regiao"}
    # só 1 persona ou id inexistente → 422
    assert client.post("/simulacoes?demo=true&personas=critico", json=NEGOCIOS["barbearia"]).status_code == 422
    assert client.post("/simulacoes?demo=true&personas=critico&personas=xyz", json=NEGOCIOS["barbearia"]).status_code == 422


def test_entrega_no_formulario(client):
    negocio = {**NEGOCIOS["barbearia"], "entrega": {"disponivel": True, "modelo": "app_delivery", "taxa": 5, "prazo": "40 min"}}
    assert client.post("/simulacoes?demo=true", json=negocio).status_code == 201
    negocio["entrega"]["modelo"] = "drone"
    assert client.post("/simulacoes?demo=true", json=negocio).status_code == 422


def test_api_nao_mostra_nem_aceita_personas_nao_aprovadas(client):
    ids = [p["id"] for p in client.get("/personas").json()]
    assert ids == ["economico", "exigente", "ocupado", "critico", "fiel_regiao"]
    rota = "/simulacoes?demo=true&personas=economico&personas=conectado"
    assert client.post(rota, json=NEGOCIOS["barbearia"]).status_code == 422


def test_relatorio_financeiro_no_resultado(client):
    custos = {"custo_fixo_mensal": 3500, "custo_variavel_unitario": 11, "taxa_plataforma_pct": 23,
              "lucro_esperado_pct": 30, "investimento_inicial": 20000}
    criada = client.post("/simulacoes?demo=true", json={**NEGOCIOS["barbearia"], "custos": custos}).json()
    fim = [json.loads(d) for t, d in ler_eventos(client, criada["id"]) if t == "fim"][0]
    fin = fim["relatorio"]["financeiro"]
    assert fin["lucro_por_venda"] > 0 and fin["cenarios"] and "impostos" in fin["aviso_custos"]
    # só lucro esperado e investimento vazios também valem (campos opcionais)
    minimo = {"custo_variavel_unitario": 30}
    assert client.post("/simulacoes?demo=true", json={**NEGOCIOS["barbearia"], "custos": minimo}).status_code == 201



def test_escolhe_agentes_dos_dois_grupos(client):
    criada = client.post("/simulacoes?demo=true&agentes=critico&agentes=marketing&agentes=precificacao",
                         json=NEGOCIOS["barbearia"]).json()
    assert criada["personas"] == ["critico"] and criada["especialistas"] == ["precificacao", "marketing"]
    eventos = ler_eventos(client, criada["id"])
    assert sum(t == "mensagem" for t, _ in eventos) == 1 and sum(t == "parecer" for t, _ in eventos) == 2
    # só especialistas também vale; menos de 2 agentes ou id inexistente, não
    assert client.post("/simulacoes?demo=true&agentes=marketing&agentes=mercado", json=NEGOCIOS["barbearia"]).status_code == 201
    assert client.post("/simulacoes?demo=true&agentes=marketing", json=NEGOCIOS["barbearia"]).status_code == 422
    assert client.post("/simulacoes?demo=true&agentes=marketing&agentes=xyz", json=NEGOCIOS["barbearia"]).status_code == 422


def test_lista_especialistas(client):
    ids = [e["id"] for e in client.get("/especialistas").json()]
    assert ids == ["precificacao", "marketing", "operacoes", "mercado", "experiencia", "consultor"]
