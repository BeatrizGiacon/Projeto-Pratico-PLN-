"""Fluxo multi-turno, categorias, referências (ID, nome, posição) e operações do pedido."""
import pytest

from util import ids


def test_pergunta_restricao_apenas_uma_vez(conversa):
    a, r = conversa(["quero lanche", "quero de frango"])
    assert "Antes de recomendar" in r[0]
    assert "Sigo sem restrições" in r[1] and ids(r[1])


def test_sem_restricoes_persiste(conversa):
    a, r = conversa(["sem restrições e sem alergias", "quero bebida", "quero sobremesa"])
    assert "Antes de recomendar" not in r[1] + r[2]
    assert ids(r[1]) and ids(r[2])


def test_pede_categoria_quando_falta(conversa):
    a, r = conversa(["sem restrições"])
    assert "Você prefere lanche" in r[-1]


def test_mudanca_de_categoria_limpa_subtipo(conversa, nb):
    a, r = conversa(["sem restrições", "quero lanche de frango", "agora quero bebida"])
    assert a.estado.categoria_atual == "bebida" and a.estado.subtipo_atual == ""
    assert ids(r[-1]) and all(nb["base"].df.loc[i, "grupo"] == "bebida" for i in ids(r[-1]))


def test_exclusao_persiste_entre_categorias(conversa, nb):
    a, r = conversa(["não como carne bovina", "quero café da manhã"])
    for i in ids(r[-1]):
        assert nb["base"].df.loc[i, "proteina_bovino"] not in ("indicado", "possivel")


@pytest.mark.parametrize("frase,pos", [("quero o segundo", 2), ("adicione a segunda opção", 2), ("adiciona o 3º", 3),
                                        ("pode ser o primeiro", 1), ("adicione o último", 5), ("adicione a opção 4", 4)])
def test_selecao_por_posicao(conversa, frase, pos):
    a, r = conversa(["sem restrições", "quero lanche de frango"])
    lista = list(a.estado.ultimas_recomendacoes)
    a.responder(frase)
    assert a.estado.pedido == [lista[pos - 1]]


def test_posicao_inexistente(conversa):
    a, r = conversa(["sem restrições", "quero lanche de frango", "adicione a opção 9"])
    assert a.estado.pedido == [] and "não existe a opção 9" in r[-1]


@pytest.mark.parametrize("frase,erro", [("adicione ID -1", "não é um ID válido"), ("adicione ID 1.5", "não é um ID válido"),
                                         ("adicione ID 9999", "não existe"), ("adicione 2 no pedido", "ID 2 ou a opção 2")])
def test_referencias_invalidas_ou_ambiguas(conversa, frase, erro):
    a, r = conversa(["sem restrições", frase])
    assert a.estado.pedido == [] and erro in r[-1]


def test_adicionar_por_nome_exato_e_ambiguo(conversa):
    a, r = conversa(["sem restrições", "adicione o McChicken"])
    assert a.estado.pedido == [66]
    r2 = a.responder("adicione Chicken McNuggets")
    assert "mais de um item" in r2 and a.estado.pedido == [66]
    a.responder("adicione Chicken McNuggets (10 piece)")
    assert a.estado.pedido == [66, 80]


def test_duplicatas_remocao_e_pedido_vazio(conversa):
    a, r = conversa(["sem restrições", "ver meu pedido", "adicione ID 66", "adicione ID 66", "ver meu pedido",
                     "remover ID 66", "remover ID 66", "remover ID 66"])
    assert "vazio" in r[1]
    assert "2x [ID 66]" in r[4]
    assert "Total (CSV): calorias 720 kcal; sódio 1600 mg" in r[4]
    assert "Removido" in r[5] and "Removido" in r[6]
    assert "não está no seu pedido" in r[7]


def test_reiniciar(conversa):
    a, r = conversa(["não como frango", "adicione ID 42", "reiniciar pedido"])
    assert a.estado.pedido == [] and a.estado.exclusoes == set()
    assert "reiniciado" in r[-1]


def test_llm_nao_reinicia_sozinho(conversa):
    llm = {"esquece": dict(intencao="reiniciar")}
    a, r = conversa(["adicione ID 42", "esquece"], llm=llm)
    assert a.estado.pedido == [42]
    assert "reiniciar pedido" in r[-1]


def test_nova_restricao_reavalia_pedido(conversa):
    a, r = conversa(["sem restrições", "adicione ID 43", "não como carne bovina"])
    assert "Quarter Pounder with Cheese (ID 43)" in r[-1] and "não atendem às restrições" in r[-1]
    assert a.estado.pedido == [43]  # não remove sem pedido explícito
    assert "não atendem" in a.responder("ver meu pedido")


def test_lista_invalidada_apos_consulta_sem_resultado(conversa):
    a, r = conversa(["sem restrições", "quero lanche", "quero lanche com no máximo 1 kcal", "adicione o segundo"])
    assert "Não encontrei itens compatíveis" in r[2]
    assert a.estado.pedido == [] and "Não há lista de opções ativa" in r[-1]


def test_lista_invalidada_apos_mudanca_de_restricao(conversa, nb):
    a, r = conversa(["sem restrições", "quero lanche"])
    antiga = list(a.estado.ultimas_recomendacoes)
    mudou, _ = a._aplicar_restricoes(nb["analisar_mensagem"]("não como carne bovina", a.base))
    assert mudou and a.estado.ultimas_recomendacoes == []
    r2 = a.responder("adicione o primeiro")
    assert "Não há lista de opções ativa (suas restrições mudaram)" in r2 and a.estado.pedido == []
    assert antiga


def test_nova_lista_apos_restricao_e_compativel(conversa, nb):
    a, r = conversa(["sem restrições", "quero lanche", "não como carne bovina", "adicione o primeiro"])
    assert a.estado.pedido and nb["base"].df.loc[a.estado.pedido[0], "proteina_bovino"] not in ("indicado", "possivel")


def test_consulta_sem_correspondencia_nao_sugere_escore_zero(conversa):
    a, r = conversa(["sem restrições", "quero xyzabc"])
    assert "Não encontrei 'xyzabc'" in r[-1]
    assert ids(r[-1]) == [] and a.estado.ultimas_recomendacoes == []


def test_busca_pt_para_nomes_em_ingles(conversa, nb):
    a, r = conversa(["sem restrições", "quero batata frita"])
    assert ids(r[-1]) and all("Fries" in nb["base"].df.loc[i, "item"] for i in ids(r[-1]))


@pytest.mark.parametrize("pergunta,trecho", [
    ("quantas calorias tem o Big Mac?", "Big Mac (ID 42): calorias 530 kcal"),
    ("qual o sódio do ID 42?", "sódio 960 mg"),
    ("quanto de açúcar e proteína tem o McChicken", "açúcar 5 g; proteína 14 g"),
    ("qual a porção do ID 42", "porção 7.4 oz (211 g)"),
])
def test_pergunta_nutriente_responde_campo(conversa, pergunta, trecho):
    a, r = conversa([pergunta])
    assert trecho in r[-1]
    assert "Antes de recomendar" not in r[-1]


def test_pergunta_nutriente_sobre_lista(conversa):
    a, r = conversa(["sem restrições", "quero lanche de frango", "quantas calorias tem cada um?"])
    assert r[-1].count("kcal") == len(a.estado.ultimas_recomendacoes)


def test_pergunta_nutriente_nao_chama_llm(novo):
    a = novo({})
    a.responder("quantas calorias tem o Big Mac?")
    a.responder("adicione ID 42")
    a.responder("ver meu pedido")
    assert a.chamadas_llm == []


def test_falha_do_llm_nao_impede_comandos_locais_nem_altera_pedido(novo):
    def falha(m):
        raise TimeoutError("timeout")
    a = novo(falha)
    assert "vazio" in a.responder("ver meu pedido")
    a.responder("adicione ID 66")
    assert a.estado.pedido == [66]
    r = a.responder("hmm sei lá, algo gostoso")
    assert "TimeoutError" in r and a.estado.pedido == [66]


def test_falha_do_llm_ainda_aplica_restricao_local(novo):
    def falha(m):
        raise ConnectionError("offline")
    a = novo(falha)
    a.responder("quero lanche")
    r = a.responder("eu nao como carne de vaca")
    assert "ConnectionError" in r
    assert a.estado.exclusoes == {"bovino"} and ids(r)


def test_llm_adicionar_por_nome_validado(conversa):
    llm = {"me vê aquele sanduíche de peixe": dict(intencao="adicionar", item_referido="Filet-O-Fish")}
    a, r = conversa(["não como peixe", "me vê aquele sanduíche de peixe"], llm=llm)
    assert a.estado.pedido == [] and "Não adicionei" in r[-1]


def test_llm_categoria_usada_quando_local_nao_encontra(conversa, nb):
    llm = {"algo pra beber": dict(categoria_desejada="bebida", restricoes_informadas=False)}
    a, r = conversa(["sem restrições", "algo pra beber"], llm=llm)
    assert a.estado.categoria_atual == "bebida"


def test_mensagem_vazia(novo):
    assert "Pode escrever" in novo().responder("   ")


def test_tipos_de_lanche(conversa):
    a, r = conversa(["sem restrições", "quero lanche", "quais tipos de lanche?"])
    assert "Divisões de lanches" in r[-1]


def test_busca_nuggets_em_portugues(conversa, nb):
    a, r = conversa(["sem restrições", "quero acompanhamento", "tem nuggets?"])
    assert ids(r[-1]) and all("McNuggets" in nb["base"].df.loc[i, "item"] for i in ids(r[-1]))
