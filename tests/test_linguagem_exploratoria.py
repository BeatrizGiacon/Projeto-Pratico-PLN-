"""Casos encontrados por exploração adversarial durante esta revisão (frases fora dos testes iniciais)."""
import pytest

from util import ids


@pytest.mark.parametrize("frase,esperado", [
    ("eu como carne de vaca", dict(subtipo="bovino", termos_busca=[])),
    ("pode ser frango", dict(subtipo="frango", liberar=set(), termos_busca=[])),
    ("quero cafe da manha sem carne", dict(grupo="cafe", excluir={"bovino", "porco"})),
    ("não como nada de origem animal", dict(dieta="vegana")),
    ("quero algo sem glúten", dict(intolerancias={"trigo"})),
    ("menos sal", dict(preferencias={"prefere_menos_sodio": True}, termos_busca=[])),
    ("quero algo com até 20g de açúcar", dict(limites={"acucar_g": ("<=", 20.0)}, termos_busca=[])),
    ("não quero bebida, quero sobremesa", dict(grupo="sobremesa")),
    ("nao gosto de frango", dict(excluir={"frango"})),
    ("prefiro não comer porco", dict(excluir={"porco"})),
    ("sou alérgico a camarão", dict(alergias={"crustaceos"})),
    ("nada de peixe nem frango", dict(excluir={"peixe", "frango"})),
    ("tira o big mac", dict(comando="remover", nome_ref=42)),
    ("remove o segundo do pedido", dict(comando="remover", ordinal=2)),
    ("adicione id42", dict(comando="adicionar", id_ref=42)),
    ("quero lanche sem bacon", dict(grupo="lanche", excluir={"porco"})),
])
def test_analise_local(nb, frase, esperado):
    a = nb["analisar_mensagem"](frase, nb["base"])
    for campo, valor in esperado.items():
        assert getattr(a, campo) == valor, (frase, campo, getattr(a, campo))


def test_cafe_da_manha_sem_carne_recomenda_cafe(conversa, nb):
    a, r = conversa(["quero cafe da manha sem carne"])
    assert a.estado.categoria_atual == "cafe"
    for i in ids(r[-1]):
        row = nb["base"].df.loc[i]
        assert row["grupo"] == "cafe"
        assert row["proteina_bovino"] not in ("indicado", "possivel")
        assert row["proteina_porco"] not in ("indicado", "possivel")


def test_sem_gluten_bloqueia_indicados_e_avisa(conversa, nb):
    a, r = conversa(["quero lanche sem glúten"])
    for i in ids(r[-1]):
        assert "trigo" not in nb["base"].df.loc[i, "alergenos_nome"]
    assert "Não é possível afirmar" in r[-1]


def test_subtipo_bloqueado_explica_como_liberar(conversa):
    a, r = conversa(["não como carne bovina", "quero lanche de carne"])
    assert "pode incluir carne bovina" in r[-1]
