"""Limites numéricos, fronteiras, unidades, valores inválidos, preferências relativas e revogação."""
import math

import pytest
from pydantic import ValidationError

from util import ids


@pytest.mark.parametrize("frase,campo,op,valor", [
    ("menos de 500 calorias", "calorias", "<", 500),
    ("até 500 kcal", "calorias", "<=", 500),
    ("no máximo 500 calorias", "calorias", "<=", 500),
    ("abaixo de 400 kcal", "calorias", "<", 400),
    ("sódio até 500 mg", "sodio_mg", "<=", 500),
    ("menos de 1 g de sódio", "sodio_mg", "<", 1000),
    ("menos de 1,5 g de sódio", "sodio_mg", "<", 1500),
    ("até 600 mg", "sodio_mg", "<=", 600),
    ("açúcar abaixo de 10 g", "acucar_g", "<", 10),
    ("pelo menos 20 g de proteína", "proteina_g", ">=", 20),
    ("mais de 30 g de proteína", "proteina_g", ">", 30),
    ("não mais que 300 calorias", "calorias", "<=", 300),
])
def test_leitura_de_limites(nb, frase, campo, op, valor):
    a = nb["analisar_mensagem"](frase, nb["base"])
    assert a.limites[campo] == (op, pytest.approx(valor))


def test_limite_sem_nutriente_e_ambiguo(conversa):
    a, r = conversa(["quero lanche com menos de 500"])
    assert a.estado.limites == {}
    assert "Não apliquei o limite 'menor que 500'" in r[-1]


def test_limite_ambiguo_resolvido_pelo_llm_mantem_operador(conversa):
    llm = {"quero lanche com menos de 500": dict(consulta="lanche", categoria_desejada="lanche",
                                                  restricoes_informadas=True, max_calorias=500)}
    a, r = conversa(["quero lanche com menos de 500"], llm=llm)
    assert a.estado.limites == {"calorias": ("<", 500.0)}
    assert "Não apliquei" not in r[-1]


def test_fronteira_menos_de_exclui_e_ate_inclui(conversa, nb):
    df = nb["base"].df
    exatamente_500 = set(df.index[df["calorias"] == 500])
    assert exatamente_500
    a, _ = conversa(["sem restrições"])
    a.estado.limites = {"calorias": ("<", 500.0)}
    assert all(nb["avaliar_item"](nb["base"], a.estado, i)[0] for i in exatamente_500)
    a.estado.limites = {"calorias": ("<=", 500.0)}
    assert not any(nb["avaliar_item"](nb["base"], a.estado, i)[0] for i in exatamente_500)


def test_recomendacao_respeita_limite_e_mostra_valores_do_csv(conversa, nb):
    a, r = conversa(["quero lanche com no máximo 400 kcal", "sem alergias"])
    assert ids(r[-1])
    for i in ids(r[-1]):
        kcal = nb["base"].df.loc[i, "calorias"]
        assert kcal <= 400
        assert f"{kcal:g} kcal" in r[-1]


def test_adicao_por_id_respeita_limite(conversa):
    a, r = conversa(["quero lanche com no máximo 100 kcal", "adicione ID 42"])
    assert a.estado.pedido == []
    assert "530 kcal não atende ao limite (até 100 kcal)" in r[-1]


@pytest.mark.parametrize("frase", ["menos de -5 calorias", "até -100 kcal"])
def test_limite_negativo_rejeitado(conversa, frase):
    a, r = conversa([frase])
    assert a.estado.limites == {}
    assert "negativos não são aceitos" in r[-1]


def test_unidade_incompativel(conversa):
    a, r = conversa(["menos de 300 mg de calorias"])
    assert a.estado.limites == {}
    assert "não é unidade de energia" in r[-1]


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), -1.0])
def test_esquema_rejeita_nan_infinito_negativo(nb, valor):
    with pytest.raises(ValidationError):
        nb["Interpretacao"](max_calorias=valor)


def test_saida_invalida_do_llm_cai_no_fallback(conversa):
    def llm(m):
        return {"max_calorias": math.inf}
    a, r = conversa(["quero lanche"], llm=llm)
    assert "modelo de linguagem não respondeu" in r[-1]
    assert a.estado.limites == {}


def test_valor_ausente_bloqueia_quando_ha_limite(nb, novo):
    import pandas as pd
    df = nb["base"].df
    sem = df.index[df["calorias"].isna()]
    assert len(sem) == 0  # o CSV atual não tem nulos; verificado também em test_dados.py
    a = novo()
    a.estado.limites = {"calorias": ("<=", 1000.0)}
    linha = df.loc[0].copy()
    linha["calorias"] = float("nan")
    base2 = nb["BaseMenu"](df.copy(), nb["base"].documentos, nb["base"].indice, "x")
    base2.df.loc[0, "calorias"] = float("nan")
    b, _ = nb["avaliar_item"](base2, a.estado, 0)
    assert "não informado" in b[0]
    assert not pd.isna(df.loc[0, "calorias"])


def test_preferencia_relativa_ordena(conversa, nb):
    a, r = conversa(["quero bebida com menos sódio", "sem alergias"])
    valores = [nb["base"].df.loc[i, "sodio_mg"] for i in ids(r[-1])]
    assert valores == sorted(valores)
    assert a.estado.preferencias == {"prefere_menos_sodio": True}
    assert a.estado.limites == {}  # 'menos sódio' não cria limite numérico


def test_mais_proteina_ordena_decrescente(conversa, nb):
    a, r = conversa(["sem restrições", "quero lanche com mais proteína"])
    valores = [nb["base"].df.loc[i, "proteina_g"] for i in ids(r[-1])]
    assert valores == sorted(valores, reverse=True)


def test_revogacao_de_preferencia_local(conversa):
    a, _ = conversa(["quero lanche com menos sódio", "não me importo mais com sódio"])
    assert "prefere_menos_sodio" not in a.estado.preferencias


def test_revogacao_de_preferencia_pelo_llm(conversa):
    llm = {"pode ser qualquer coisa": dict(prefere_menos_sodio=False, restricoes_informadas=True)}
    a, _ = conversa(["quero lanche com menos sódio", "pode ser qualquer coisa"], llm=llm)
    assert "prefere_menos_sodio" not in a.estado.preferencias


def test_revogar_limite_mantem_outras_restricoes(conversa):
    a, _ = conversa(["não como carne bovina", "até 500 kcal", "menos de 800 mg de sódio", "remover limite de calorias"])
    assert a.estado.limites == {"sodio_mg": ("<", 800.0)}
    assert a.estado.exclusoes == {"bovino"}


def test_substituir_limite(conversa):
    a, _ = conversa(["até 500 kcal", "na verdade até 700 kcal"])
    assert a.estado.limites == {"calorias": ("<=", 700.0)}


def test_liberar_proteina_mantem_demais(conversa):
    a, _ = conversa(["não como carne bovina nem frango", "até 600 kcal", "agora eu como frango"])
    assert a.estado.exclusoes == {"bovino"}
    assert a.estado.limites == {"calorias": ("<=", 600.0)}


def test_pode_incluir_carne_bovina(conversa):
    a, _ = conversa(["não como carne de vaca", "pode incluir carne bovina"])
    assert a.estado.exclusoes == set() and a.estado.pedido == []


def test_remover_todas_as_restricoes_preserva_alergia(conversa):
    a, _ = conversa(["tenho alergia a ovo", "não como frango", "até 500 kcal", "remover todas as restrições"])
    assert a.estado.exclusoes == set() and a.estado.limites == {}
    assert a.estado.alergias == {"ovo"}


def test_sem_acucar_vira_limite_zero(conversa, nb):
    a, r = conversa(["quero bebida sem açúcar", "sem alergias"])
    assert a.estado.limites["acucar_g"] == ("<=", 0.0)
    assert all(nb["base"].df.loc[i, "acucar_g"] == 0 for i in ids(r[-1]))


def test_numero_de_opcoes_nao_vira_limite(nb):
    a = nb["analisar_mensagem"]("me mostra até 5 opções de bebida", nb["base"])
    assert a.limites == {} and a.limite_ambiguo == []
