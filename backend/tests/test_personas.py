"""Testes das personas e dos textos do debate (sem chave nem internet)."""

import random

from app.agents.debate import pedido_rodada_2
from app.agents.personas import PERSONAS
from app.models.schemas import MensagemDebate, Opiniao


def test_ids_batem_com_as_chaves():
    assert all(chave == p.id for chave, p in PERSONAS.items())
    assert len({p.nome for p in PERSONAS.values()}) == len(PERSONAS)


def test_prompt_tem_os_campos_novos_e_a_regua():
    for p in PERSONAS.values():
        prompt = p.prompt_sistema()
        for texto in (p.perfil_vida, p.jeito_de_falar, p.convence_se_com, p.contradicao, p.discorda_de):
            assert texto and texto in prompt
        assert "Régua da nota" in prompt
        assert "NÃO compra de um negócio novo" in prompt


def _fala(nome: str) -> MensagemDebate:
    return MensagemDebate(
        persona_id=nome, persona_nome=nome, rodada=1, origem="teste", duracao_segundos=0,
        opiniao=Opiniao(fala=f"fala de {nome}", interesse=5, compraria="talvez"),
    )


def test_rodada_2_pede_discordancia():
    pedido = pedido_rodada_2([_fala("A"), _fala("B")], random.Random(0))
    assert "MAIS DISCORDA" in pedido
    assert 'NÃO comece a fala com "Concordo"' in pedido


def test_embaralhamento_reproduzivel_com_semente():
    falas = [_fala(n) for n in "ABCDE"]
    assert pedido_rodada_2(falas, random.Random(42)) == pedido_rodada_2(falas, random.Random(42))
    # Não altera a lista original
    assert [f.persona_nome for f in falas] == list("ABCDE")


def test_personas_sao_genericas():
    """Nenhuma persona pode assumir um ramo (ex.: delivery), pois o usuário escolhe o negócio."""
    proibidas = ("entrega", "delivery", "aplicativo", "app ", "cupom", "pedido em")
    for p in PERSONAS.values():
        campos = " ".join([p.descricao, p.prioridades, p.desiste_quando, p.convence_se_com,
                           p.contradicao, p.discorda_de]).lower()
        for palavra in proibidas:
            assert palavra not in campos, f"{p.id} menciona '{palavra}'"
        # discorda_de descreve um comportamento, não uma persona fixa
        assert "Consumidor" not in p.discorda_de


def test_rodada_2_mostra_objecao_e_sugestao_dos_outros():
    outro = _fala("A")
    outro.opiniao.objecoes = ["caro"]
    outro.opiniao.o_que_mudaria = "primeira compra com desconto"
    pedido = pedido_rodada_2([outro], random.Random(0))
    assert "Principal objeção: caro" in pedido
    assert "Sugestão ao dono: primeira compra com desconto" in pedido


def test_contexto_mostra_a_entrega():
    from app.agents.contexto import formatar_negocio
    base = {"tipo": "Marmitaria", "preco": 20}
    assert "Entrega: não informada" in formatar_negocio(base)
    assert "não faz entrega" in formatar_negocio({**base, "entrega": {"disponivel": False}})
    texto = formatar_negocio({**base, "entrega": {"disponivel": True, "modelo": "proprio", "taxa": 0,
                                                  "prazo": "40 min", "area": "até 3 km", "garantias": "bolsa térmica"}})
    assert "entregador próprio" in texto and "entrega grátis" in texto and "40 min" in texto and "bolsa térmica" in texto


def test_escolher_personas():
    from app.agents.personas import escolher_personas
    assert len(escolher_personas()) == 5
    assert [p.id for p in escolher_personas(2)] == ["economico", "exigente"]
    assert len(escolher_personas(8)) == len(PERSONAS) == 8
    assert len(escolher_personas(50)) == 8 and len(escolher_personas(0)) == 2


def test_nenhuma_persona_pede_certificado():
    for p in PERSONAS.values():
        assert "certifica" not in p.prompt_sistema().split("Regras:")[0].lower()
    assert "Não exija certificados" in PERSONAS["exigente"].prompt_sistema()
