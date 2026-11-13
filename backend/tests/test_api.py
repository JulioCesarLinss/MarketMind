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
    assert len(mensagens) == 2 * len(PERSONAS)
    assert criada.json()["personas"] == list(PERSONAS)
    assert eventos[-1][0] == "fim"
    assert eventos[-2] == ("etapa", '{"etapa": "analise"}')  # aviso antes do relatório
    # Pesquisa de mercado vem antes da primeira fala
    assert eventos[0] == ("etapa", '{"etapa": "pesquisa"}')
    assert eventos[1][0] == "pesquisa" and json.loads(eventos[1][1])["total_precos"] > 0
    assert eventos[2][0] == "mensagem"
    final = json.loads(eventos[-1][1])
    assert final["rodadas"] == 2
    assert final["relatorio"]["analise"]["recomendacoes"]
    assert final["relatorio"]["indicadores"]["preco_ofertado"] == NEGOCIOS["barbearia"]["preco"]

    estado = client.get(f"/simulacoes/{id_}").json()
    assert estado["status"] == "concluida"
    assert len(estado["mensagens"]) == 2 * len(PERSONAS)

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
    assert len(mensagens) == 6 and {m["persona_id"] for m in mensagens} == {"economico", "critico", "fiel_regiao"}
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
