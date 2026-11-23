"""Exclusões de proteína: regressão P0 (carne bovina), negação, polaridade, frango, porco, peixe, dietas."""
import pytest

from util import BOVINOS_LANCHE, ids


def test_regressao_conversa_carne_de_vaca(conversa, nb):
    a, r = conversa(["quero lanche", "eu nao como carne de vaca"])
    assert "Antes de recomendar" in r[0]
    recomendados = ids(r[1])
    assert recomendados, r[1]
    for i in recomendados:
        assert nb["base"].df.loc[i, "proteina_bovino"] not in ("indicado", "possivel")
    assert not set(recomendados) & {42, 48, 49, 50, 51}
    assert a.estado.exclusoes == {"bovino"}
    assert a.estado.subtipo_atual == ""  # 'carne' negada não vira preferência
    assert "ingredientes não foram verificados" in r[1]


def test_regressao_com_llm_que_erra_subtipo(conversa):
    """Mesmo se o LLM devolver subtipo 'bovino' para a frase negada, nada bovino é recomendado."""
    llm = {"quero lanche": dict(consulta="lanche", categoria_desejada="lanche"),
           "eu nao como carne de vaca": dict(consulta="carne", restricoes_informadas=True,
                                              subtipo_lanche="bovino", evita_carne_bovina=False)}
    a, r = conversa(["quero lanche", "eu nao como carne de vaca"], llm=llm)
    assert not set(ids(r[1])) & set(BOVINOS_LANCHE)
    assert "bovino" in a.estado.exclusoes


@pytest.mark.parametrize("frase", [
    "eu não como carne de vaca", "eu nao como carne de vaca", "não como carne bovina", "sem carne bovina",
    "Não Como Boi", "evito carne de boi", "nada de beef", "nunca como carne bovina", "NAO COMO CARNE DE VACA!",
])
def test_variantes_negacao_bovina(nb, frase):
    a = nb["analisar_mensagem"](frase, nb["base"])
    assert "bovino" in a.excluir
    assert a.subtipo is None


def test_todos_os_bovinos_conhecidos_bloqueados_inclusive_sem_beef_no_nome(nb, novo):
    a = novo()
    a.estado.exclusoes = {"bovino"}
    df = nb["base"].df
    for i in df.index[df["categoria"] == "Beef & Pork"]:
        bloqueios, _ = nb["avaliar_item"](nb["base"], a.estado, i)
        assert bloqueios, df.loc[i, "item"]
    for i in [5, 18, 26]:  # Steak & Egg (café da manhã)
        assert nb["avaliar_item"](nb["base"], a.estado, i)[0]


def test_ausencia_de_beef_no_nome_nao_e_prova(nb):
    df = nb["base"].df
    # Hamburger / Cheeseburger / Big Mac / McDouble não têm 'beef' no nome e ainda assim são indicados
    for nome in ["Hamburger", "Cheeseburger", "Big Mac", "McDouble", "Daily Double"]:
        assert df.loc[df["item"] == nome, "proteina_bovino"].item() == "indicado"
    # McRib: categoria compartilhada, bovino não pode ser descartado
    assert df.loc[df["item"] == "McRib", "proteina_bovino"].item() == "possivel"
    # Egg McMuffin: sanduíche sem recheio descrito => possível
    assert df.loc[df["item"] == "Egg McMuffin", "proteina_bovino"].item() == "possivel"


def test_ranking_nao_reintroduz_bovino_com_consulta_explicita(conversa):
    a, r = conversa(["não como carne bovina", "quero big mac hamburger cheeseburger"])
    assert not set(ids(r[-1])) & set(BOVINOS_LANCHE)


def test_adicionar_bovino_bloqueado_por_id_nome_e_posicao(conversa):
    a, r = conversa(["não como carne bovina", "adicione ID 48", "quero o Big Mac", "adicione o Hamburger"])
    assert a.estado.pedido == []
    assert all("Não adicionei" in x for x in r[1:]), r
    a.estado.ultimas_recomendacoes = [57, 48]
    r2 = a.responder("adicione o segundo")
    assert "Não adicionei" in r2 and a.estado.pedido == []


def test_restricao_e_preferencia_positiva_na_mesma_frase(conversa):
    a, r = conversa(["não como carne de vaca, mas quero frango", "sem alergias"])
    assert a.estado.exclusoes == {"bovino"}
    assert a.estado.subtipo_atual == "frango"
    assert all(a.base.df.loc[i, "subtipo"] == "frango" for i in ids(r[-1]))


def test_carne_generica_negada_pede_esclarecimento(conversa):
    a, r = conversa(["quero lanche", "não como carne"])
    assert a.estado.exclusoes == {"bovino", "porco"}
    assert "frango ou peixe" in r[1]


def test_carne_vermelha(nb):
    assert nb["analisar_mensagem"]("não como carne vermelha", nb["base"]).excluir == {"bovino", "porco"}


def test_so_como_frango(conversa):
    a, r = conversa(["eu só como frango", "quero lanche"])
    assert a.estado.exclusoes == {"bovino", "porco", "peixe"}
    for i in ids(r[-1]):
        row = a.base.df.loc[i]
        assert row["proteina_frango"] == "indicado"
        assert row["proteina_bovino"] not in ("indicado", "possivel")
        assert row["proteina_porco"] not in ("indicado", "possivel")


def test_nao_como_frango_nem_porco(conversa):
    a, r = conversa(["não como frango nem porco", "quero lanche"])
    assert a.estado.exclusoes == {"frango", "porco"}
    for i in ids(r[-1]):
        assert a.base.df.loc[i, "proteina_frango"] not in ("indicado", "possivel")
        assert a.base.df.loc[i, "proteina_porco"] not in ("indicado", "possivel")


def test_sem_bacon_exclui_suino(nb):
    assert "porco" in nb["analisar_mensagem"]("quero lanche sem bacon", nb["base"]).excluir


def test_peixe_excluido(conversa):
    a, r = conversa(["não como peixe", "quero lanche"])
    assert 83 not in ids(r[-1])
    assert "Não adicionei" in a.responder("adicione ID 83")


def test_vegetariano(conversa, nb):
    a, r = conversa(["sou vegetariano", "quero lanche"])
    assert a.estado.dieta == "vegetariana"
    assert "Não encontrei itens compatíveis" in r[-1]  # todos os lanches têm proteína possível/indicada
    r2 = a.responder("quero acompanhamento")
    for i in ids(r2):
        for p in nb["PROTEINAS"]:
            assert a.base.df.loc[i, f"proteina_{p}"] not in ("indicado", "possivel")


def test_vegano_nunca_confirma(conversa, nb):
    a, r = conversa(["sou vegano", "quero bebida"])
    assert a.estado.dieta == "vegana"
    for i in ids(r[-1]):
        assert not set(a.base.df.loc[i, "alergenos_nome"]) & {"leite", "ovo"}
    assert "não permite confirmar que algum item é vegano" in r[-1]
    assert "Não adicionei" in a.responder("adicione ID 135") or "Latte" not in a.base.df.loc[135, "item"]


def test_vegano_bloqueia_mel(nb, novo):
    a = novo()
    a.estado.dieta = "vegana"
    i = int(nb["base"].df.index[nb["base"].df["item"].str.contains("Honey Mustard")][0])
    assert nb["avaliar_item"](nb["base"], a.estado, i)[0]


def test_nao_sou_mais_vegetariano(conversa):
    a, _ = conversa(["sou vegetariano", "não sou mais vegetariano"])
    assert a.estado.dieta is None


def test_filet_o_fish_nao_e_frango(nb):
    df = nb["base"].df
    assert df.loc[83, "subtipo"] == "peixe"
    assert df.loc[83, "proteina_peixe"] == "indicado"


def test_without_chicken_fora_da_busca_por_frango(conversa):
    a, r = conversa(["sem restrições", "quero salada de frango"])
    assert ids(r[-1])
    assert not {84, 87} & set(ids(r[-1]))


def test_without_chicken_tem_estado_de_ausencia(nb):
    assert nb["base"].df.loc[84, "proteina_frango"] == "ausencia_indicada"
    assert nb["base"].df.loc[85, "proteina_frango"] == "indicado"


def test_subtipo_bloqueado_por_exclusao(conversa):
    a, r = conversa(["não como frango", "quero nuggets"])
    assert a.estado.subtipo_atual == ""
    assert not {78, 79, 80, 81, 82} & set(ids(r[-1]))
