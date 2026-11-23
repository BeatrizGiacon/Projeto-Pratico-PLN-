"""Alergias e intolerâncias: nunca alegar segurança; confirmação só para o item específico."""
from util import ids


def test_alergia_extraida_com_sinonimos(nb):
    an = nb["analisar_mensagem"]
    assert an("tenho alergia a leite e ovo", nb["base"]).alergias == {"leite", "ovo"}
    assert an("sou alérgico a glúten", nb["base"]).alergias == {"trigo"}
    assert an("tenho doença celíaca", nb["base"]).alergias == {"trigo"}
    assert an("sou intolerante à lactose", nb["base"]).intolerancias == {"leite"}
    assert an("sem alergias", nb["base"]).sem_alergias
    assert an("não tenho alergia", nb["base"]).sem_alergias
    assert an("tenho alergia a abacate", nb["base"]).alergias == {"abacate"}
    assert an("tenho alergia", nb["base"]).alergia_nao_especificada


def test_alergia_a_peixe_nao_vira_preferencia_por_peixe(nb):
    a = nb["analisar_mensagem"]("tenho alergia a peixe", nb["base"])
    assert a.subtipo is None and a.alergias == {"peixe"}


def test_recomendacao_com_alergia_sempre_tem_aviso_e_bloqueia_indicados(conversa):
    a, r = conversa(["tenho alergia a leite", "quero sobremesa"])
    assert "Não é possível afirmar que qualquer item seja seguro" in r[-1]
    for i in ids(r[-1]):
        assert "leite" not in a.base.df.loc[i, "alergenos_nome"]
    assert "seguro para" not in r[-1].lower()


def test_item_com_alergeno_no_nome_e_rejeitado(conversa):
    a, r = conversa(["tenho alergia a leite", "adicione ID 49"])  # Cheeseburger
    assert "Não adicionei" in r[-1] and a.estado.pedido == []


def test_confirmacao_e_por_item_e_nao_reutilizavel(conversa):
    a, r = conversa(["tenho alergia a ovo", "adicione ID 101"])
    assert a.estado.pedido == [] and a.estado.confirmacao_pendente == 101
    assert "confirmo adicionar ID 101" in r[-1]
    # confirmação para outro ID não adiciona
    assert "pendente é para o ID 101" in a.responder("confirmo adicionar ID 96")
    assert a.estado.pedido == []
    a.responder("confirmo adicionar ID 101")
    assert a.estado.pedido == [101]
    # a confirmação foi consumida: novo item exige nova confirmação
    r2 = a.responder("adicione ID 96")
    assert a.estado.pedido == [101] and "confirmo adicionar ID 96" in r2


def test_ciencia_para_visualizar_nao_autoriza_adicao(conversa):
    a, r = conversa(["tenho alergia a leite, estou ciente de que não há garantia, quero só ver",
                     "adicione ID 101"])
    assert a.estado.pedido == []
    assert "confirmo adicionar ID 101" in r[-1]


def test_confirmacao_sem_pendencia_nao_adiciona(conversa):
    a, r = conversa(["tenho alergia a leite", "estou ciente"])
    assert a.estado.pedido == []
    assert "não torna nenhum item seguro" in r[-1]


def test_mudanca_de_restricao_cancela_confirmacao_pendente(conversa):
    a, _ = conversa(["tenho alergia a ovo", "adicione ID 101", "não como carne bovina"])
    assert a.estado.confirmacao_pendente is None
    a.responder("confirmo adicionar ID 101")
    assert a.estado.pedido == []


def test_sem_alergias_limpa(conversa):
    a, _ = conversa(["tenho alergia a leite", "na verdade não tenho alergias"])
    assert a.estado.alergias == set() and a.estado.sem_alergias_declaradas


def test_llm_nao_pode_remover_alergia(conversa):
    llm = {"quero bebida": dict(consulta="bebida", categoria_desejada="bebida", sem_alergias=True)}
    a, _ = conversa(["tenho alergia a leite", "quero bebida"], llm=llm)
    assert a.estado.alergias == {"leite"}


def test_llm_pode_acrescentar_alergia(conversa):
    llm = {"quero algo, sou alérgico àquilo de vaca": dict(alergias=["lactose"], restricoes_informadas=True)}
    a, _ = conversa(["quero algo, sou alérgico àquilo de vaca"], llm=llm)
    assert "leite" in a.estado.alergias


def test_pergunta_seguranca_responde_aviso(conversa):
    a, r = conversa(["tenho alergia a amendoim", "a batata frita é segura para mim?"])
    assert "Não é possível afirmar" in r[-1]
    r2 = a.responder("o ID 98 contém amendoim?")
    assert "Large French Fries" in r2 and "Não é possível afirmar" in r2


def test_intolerancia_bloqueia_indicado_sem_exigir_confirmacao(conversa):
    a, r = conversa(["sou intolerante a lactose", "adicione ID 101"])
    assert a.estado.pedido == [101]
    assert "Não é possível afirmar" in r[-1]
    assert "Não adicionei" in a.responder("adicione ID 49")
