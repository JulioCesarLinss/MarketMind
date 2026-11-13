"""Testes da calculadora financeira (contas feitas pelo código, sem IA)."""

from app.models.pesquisa import FaixaMercado, PesquisaMercado
from app.models.schemas import IndicadorPersona, Indicadores
from app.services import financeiro as fin


def _negocio(preco=26, fixo=4000, custo=11, taxa=23, meta=None, investimento=None, entrega=None):
    custos = {"custo_fixo_mensal": fixo, "custo_variavel_unitario": custo, "taxa_plataforma_pct": taxa}
    if meta is not None:
        custos["lucro_esperado_pct"] = meta
    if investimento is not None:
        custos["investimento_inicial"] = investimento
    return {"preco": preco, "custos": custos, "entrega": entrega}


def test_sem_custos_nao_ha_relatorio():
    assert fin.calcular_financeiro({"preco": 26}) is None
    assert fin.calcular_financeiro({"preco": 26, "custos": None}) is None


def test_contas_basicas():
    f = fin.calcular_financeiro(_negocio())
    assert f.receita_liquida_venda == 20.02          # 26 × (1 − 0,23)
    assert f.lucro_por_venda == 9.02                 # 20,02 − 11
    assert f.margem_pct == 34.7
    assert f.avaliacao_preco == "sem_meta"
    # o ponto de equilíbrio é só interno: não aparece no relatório
    assert "equilibrio" not in " ".join(f.model_dump().keys())
    assert fin.ponto_equilibrio_mes(4000, 9.02) == 444   # 4000 ÷ 9,02 = 443,5 → para cima


def test_aviso_de_impostos_e_funcionarios():
    f = fin.calcular_financeiro(_negocio())
    assert "impostos" in f.aviso_custos and "funcionários" in f.aviso_custos
    assert any("funcionários" in item for item in f.nao_considerado)
    assert f.aviso_custos in fin.formatar_financeiro(f)


def test_lucro_esperado_dentro_e_abaixo():
    assert fin.calcular_financeiro(_negocio(meta=30)).avaliacao_preco == "dentro_do_esperado"
    f = fin.calcular_financeiro(_negocio(meta=40))
    assert f.avaliacao_preco == "abaixo_do_esperado"
    # preço que deixa 40% de lucro: 11 ÷ (1 − 0,23 − 0,40) = 29,73
    assert f.preco_para_lucro_esperado == 29.73
    assert "29,73" in f.resumo_preco
    # e o preço sugerido entra na comparação de preços
    assert any(c.rotulo.startswith("Preço para 40%") for c in f.cenarios_preco)


def test_preco_que_da_prejuizo():
    f = fin.calcular_financeiro(_negocio(preco=12, custo=11, taxa=23))
    assert f.lucro_por_venda < 0 and f.avaliacao_preco == "prejuizo"
    assert f.cenarios == []
    assert "prejuízo" in f.resumo_preco


def test_cenarios_de_clientes_por_dia_e_investimento():
    f = fin.calcular_financeiro(_negocio(investimento=25000))
    dias = [c.clientes_dia for c in f.cenarios]
    assert dias == [10, 15, 20, 30]                  # 2 com prejuízo e 2 com lucro (equilíbrio ≈ 18, não mostrado)
    dez = f.cenarios[0]
    assert dez.vendas_mes == 260 and dez.lucro_mes == round(260 * 9.02 - 4000, 2)
    assert dez.lucro_mes < 0 and dez.meses_para_pagar is None   # com prejuízo, não se paga
    trinta = f.cenarios[-1]
    assert trinta.meses_para_pagar == round(25000 / trinta.lucro_mes, 1)


def test_sem_custo_fixo():
    f = fin.calcular_financeiro(_negocio(fixo=0))
    assert [c.clientes_dia for c in f.cenarios] == [5, 10, 20, 30]
    assert any("Custo fixo mensal igual a zero" in a for a in f.alertas)


def test_texto_dos_meses():
    assert fin.texto_meses(0.4) == "cerca de 1 mês"
    assert fin.texto_meses(8.2) == "cerca de 9 meses"
    assert fin.texto_meses(12) == "cerca de 1 ano"
    assert fin.texto_meses(30) == "cerca de 2 anos e 6 meses"


def test_alertas_de_entrega():
    app = fin.calcular_financeiro(_negocio(taxa=0, entrega={"disponivel": True, "modelo": "app_delivery"}))
    assert any("12% a 30%" in a for a in app.alertas)
    propria = fin.calcular_financeiro(_negocio(entrega={"disponivel": True, "modelo": "proprio"}))
    assert any("custo da entrega" in a for a in propria.alertas)


def test_compara_com_agentes_e_mercado():
    personas = [IndicadorPersona(persona_id=str(i), persona_nome=str(i), interesse_r1=5, interesse_r2=5,
                                 compraria_r1="talvez", compraria_r2="talvez", mudou=False, preco_maximo=pm)
                for i, pm in enumerate([20, 22, 30])]
    ind = Indicadores(preco_ofertado=26, interesse_medio_r1=5, interesse_medio_r2=5, decisoes_r2={}, preco_maximo_medio=24,
                      mudaram_de_posicao=0, por_persona=personas, avaliacao_preco="acima_do_aceito", preco_referencia=22)
    pesquisa = PesquisaMercado(media_geral=22.44, faixas=[FaixaMercado(faixa="premium", quantidade=2, media=28.4,
                                                                       dados_suficientes=True)])
    f = fin.calcular_financeiro(_negocio(), ind, pesquisa)
    rotulos = {c.rotulo: c for c in f.cenarios_preco}
    assert rotulos["Seu preço"].aceitam == 1                     # só quem aceita até 30
    assert rotulos["O que os agentes pagariam"].preco == 22
    assert rotulos["Média do mercado na região"].lucro_por_venda == round(22.44 * 0.77 - 11, 2)
    assert rotulos["Faixa premium do mercado"].aceitam == 1


def test_relatorio_do_analista_traz_o_financeiro():
    import asyncio

    from app.agents.analista import analisar
    from app.models.schemas import MensagemDebate, Opiniao, ResultadoSimulacao

    msgs = [MensagemDebate(persona_id="a", persona_nome="A", rodada=r, origem="t", duracao_segundos=0,
                           opiniao=Opiniao(fala="ok", interesse=7, compraria="sim", preco_maximo=30)) for r in (1, 2)]
    resultado = ResultadoSimulacao(mensagens=msgs, rodadas=2, provedor_principal="t", tokens_usados=0, duracao_segundos=0)
    rel = asyncio.run(analisar(None, _negocio(), resultado))
    assert rel.financeiro is not None and rel.financeiro.lucro_por_venda == 9.02
    assert asyncio.run(analisar(None, {"preco": 26}, resultado)).financeiro is None
