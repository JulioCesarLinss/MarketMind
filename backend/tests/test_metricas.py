"""Testes das métricas de qualidade do debate."""

from app.models.schemas import MensagemDebate, Opiniao, ResultadoSimulacao
from app.services.metricas import calcular_metricas


def _msg(nome, rodada, fala, interesse, compraria, preco=None):
    return MensagemDebate(
        persona_id=nome, persona_nome=f"Consumidor {nome}", rodada=rodada, origem="teste", duracao_segundos=0,
        opiniao=Opiniao(fala=fala, interesse=interesse, compraria=compraria, preco_maximo=preco),
    )


def montar():
    r1 = [
        _msg("Econômico", 1, "Caro.", 2, "nao", 10.0),
        _msg("Exigente", 1, "Bom.", 8, "sim", 25.0),
        _msg("Ocupado", 1, "Depende.", 5, "talvez"),
        _msg("Crítico", 1, "Igual.", 3, "nao", 12.0),
        _msg("Local", 1, "Gostei.", 6, "talvez", 15.0),
    ]
    r2 = [
        _msg("Econômico", 2, "Concordo com o Crítico.", 2, "nao"),
        _msg("Exigente", 2, "Econômico, qualidade custa. Ocupado, calma.", 8, "sim"),
        _msg("Ocupado", 2, "Concordo, mas quero rapidez.", 7, "sim"),
        _msg("Crítico", 2, "Ainda não vi diferencial.", 3, "nao"),
        _msg("Local", 2, "Vou esperar a vizinha.", 6, "talvez"),
    ]
    return ResultadoSimulacao(mensagens=r1 + r2, rodadas=2, provedor_principal="teste",
                              tokens_usados=1000, duracao_segundos=10)


def test_metricas():
    m = calcular_metricas(montar())
    assert m["pct_concordo_r2"] == 40  # 2 de 5
    assert m["pct_cita_outro_r2"] == 40  # Econômico cita Crítico; Exigente cita Econômico e Ocupado
    assert m["pct_cita_2_ou_mais_r2"] == 20
    assert m["mais_citada"]["pct_das_citacoes"] == 33  # 3 citações, cada persona citada 1 vez
    assert m["notas_r1"]["amplitude"] == 6
    assert m["decisoes_distintas_r1"] == 3
    assert m["mudaram_de_posicao"] == 1  # Ocupado: talvez → sim
    assert m["preco_maximo"] == {"respostas": 4, "media": 15.5, "min": 10.0, "max": 25.0}
    assert m["tokens"] == 1000
