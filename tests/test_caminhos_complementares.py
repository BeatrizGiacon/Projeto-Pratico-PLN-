"""Caminhos de integração LLM/estado que não eram cobertos pelos testes por requisito."""
from util import ids


def test_llm_acrescenta_exclusao_e_dieta(conversa):
    llm = {"prefiro evitar aquilo": dict(evita_frango=True, restricoes_informadas=True),
           "e também não quero nada animal": dict(vegano=True, restricoes_informadas=True)}
    a, _ = conversa(["prefiro evitar aquilo", "e também não quero nada animal"], llm=llm)
    assert "frango" in a.estado.exclusoes and a.estado.dieta == "vegana"


def test_llm_vegetariano_nao_rebaixa_vegano(conversa):
    llm = {"x": dict(vegetariano=True)}
    a, _ = conversa(["sou vegano", "x"], llm=llm)
    assert a.estado.dieta == "vegana"


def test_llm_intolerancia_e_preferencia(conversa):
    llm = {"me ajuda": dict(intolerancias=["lactose"], prefere_menos_calorias=True, restricoes_informadas=True)}
    a, _ = conversa(["me ajuda"], llm=llm)
    assert a.estado.intolerancias == {"leite"} and a.estado.preferencias == {"prefere_menos_calorias": True}


def test_llm_limite_nao_sobrepoe_limite_local(conversa):
    llm = {"até 300 kcal": dict(max_calorias=999)}
    a, _ = conversa(["até 300 kcal"], llm=llm)
    assert a.estado.limites == {"calorias": ("<=", 300.0)}


def test_llm_subtipo_afirmativo_usado(conversa, nb):
    llm = {"algo com aquele bicho que cacareja": dict(categoria_desejada="lanche", subtipo_lanche="frango", restricoes_informadas=True)}
    a, r = conversa(["algo com aquele bicho que cacareja"], llm=llm)
    assert a.estado.subtipo_atual == "frango"
    assert all(nb["base"].df.loc[i, "subtipo"] == "frango" for i in ids(r[-1]))


def test_llm_categoria_invalida_ignorada(conversa):
    llm = {"sem restrições, me surpreenda": dict(categoria_desejada="xyz", restricoes_informadas=True)}
    a, r = conversa(["sem restrições, me surpreenda"], llm=llm)
    assert a.estado.categoria_atual == ""
    assert "do cardápio" in r[-1] and "de o cardápio" not in r[-1]


def test_llm_ver_pedido(conversa):
    llm = {"o que eu escolhi até agora?": dict(intencao="ver_pedido")}
    a, r = conversa(["o que eu escolhi até agora?"], llm=llm)
    assert "vazio" in r[-1]


def test_nova_exclusao_limpa_subtipo_ativo(conversa):
    a, _ = conversa(["sem restrições", "quero lanche de frango", "não como frango"])
    assert a.estado.subtipo_atual == ""


def test_revoga_subtipo(conversa):
    a, _ = conversa(["sem restrições", "quero lanche de frango", "não precisa ser frango"])
    assert a.estado.subtipo_atual == ""


def test_liberar_com_dieta_avisa(conversa):
    a, r = conversa(["sou vegetariana", "pode incluir frango"])
    assert "não sou mais vegetariano" in r[-1] and a.estado.dieta == "vegetariana"


def test_termos_da_primeira_mensagem_sao_preservados(conversa, nb):
    a, r = conversa(["quero batata frita", "sem restrições"])
    assert ids(r[-1]) and all("Fries" in nb["base"].df.loc[i, "item"] for i in ids(r[-1]))


def test_adicionar_sem_referencia_pergunta(conversa):
    a, r = conversa(["adiciona"])
    assert "Qual produto?" in r[-1] and a.estado.pedido == []


def test_pergunta_nutriente_sem_item_e_sem_lista(conversa):
    a, r = conversa(["quantas calorias tem?"])
    assert "De qual produto?" in r[-1]


def test_pergunta_nutriente_com_referencia_invalida(conversa):
    a, r = conversa(["quantas calorias tem o ID 999?"])
    assert "não existe" in r[-1]


def test_pergunta_composicao_sem_item(conversa):
    a, r = conversa(["quais os ingredientes?"])
    assert "não traz ingredientes" in r[-1]


def test_pergunta_composicao_referencia_invalida(conversa):
    a, r = conversa(["o ID 1.5 contém leite?"])
    assert "não é um ID válido" in r[-1]


def test_nuggets_fora_de_lanche_filtra_por_nome(conversa, nb):
    a, r = conversa(["sem restrições", "quero lanche"])
    a.estado.categoria_atual, a.estado.subtipo_atual = "acompanhamento", "nuggets"
    assert "Não encontrei itens compatíveis" in a._recomendar([], [])
    a.estado.categoria_atual, a.estado.subtipo_atual = "acompanhamento", "frango"
    r2 = a._recomendar([], [])
    assert ids(r2) and all(nb["base"].df.loc[i, "proteina_frango"] == "indicado" for i in ids(r2))


def test_ver_pedido_com_valor_ausente(nb):
    base = nb["construir_base"](__import__("pandas").read_csv(nb["URL_MENU"].replace(nb["URL_MENU"], str(__import__("notebook_loader").CSV_LOCAL))))
    base.df.loc[66, "acucar_g"] = float("nan")
    a = nb["AssistenteMcDonalds"](base)
    a.responder("adicione ID 66")
    r = a.responder("ver meu pedido")
    assert "(+1 sem informação)" in r
    assert "açúcar não informado" in a.responder("quanto açúcar tem o ID 66?")
