"""Reproduz, sem chamar o LLM, os achados da auditoria anterior no notebook ORIGINAL.

Uso:
    git show f2b4553:projeto_pln.ipynb > /tmp/original.ipynb
    python evidencias/reproduzir_original.py /tmp/original.ipynb menu.csv

O LLM é substituído por uma função que devolve a interpretação CORRETA de cada
mensagem (como um modelo perfeito faria). Assim, qualquer falha observada é da
lógica determinística do notebook, não do modelo.
"""
import json
import sys
from unittest import mock

import pandas as pd


def carregar(caminho_nb, caminho_csv):
    nb = json.load(open(caminho_nb, encoding="utf-8"))
    codigo = []
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        fonte = "".join(c["source"])
        if i in (2, 4, 5, 25):  # pip, getpass, ChatOpenAI e loop interativo
            continue
        fonte = "\n".join(l for l in fonte.splitlines() if not l.lstrip().startswith(("!", "%")))
        codigo.append(fonte)
    ns = {"display": lambda *a, **k: None}
    texto_csv = open(caminho_csv, encoding="utf-8").read()
    resp = mock.Mock(text=texto_csv, content=texto_csv.encode(), status_code=200)
    resp.raise_for_status = lambda: None

    class ModeloFalso:
        def with_structured_output(self, schema):
            from langchain_core.runnables import RunnableLambda
            return RunnableLambda(lambda _: schema(consulta="frango", restricoes_informadas=True,
                                                   prefere_frango=True, prefere_menos_sodio=True,
                                                   max_sodio_mg=500))
    ns["modelo"] = ModeloFalso()
    import nltk
    with mock.patch("requests.get", return_value=resp), mock.patch.object(nltk, "download", return_value=True):
        try:
            exec(compile("\n\n".join(codigo), caminho_nb, "exec"), ns)
        except LookupError:
            # wordnet indisponível neste ambiente: substitui o lematizador e reexecuta
            ns2 = {"display": lambda *a, **k: None, "modelo": ModeloFalso()}
            codigo[3] = codigo[3].replace("lematizador.lemmatize(t)", "t")
            exec(compile("\n\n".join(codigo), caminho_nb, "exec"), ns2)
            ns = ns2
    return ns


def main():
    nb, csv = sys.argv[1], sys.argv[2]
    ns = carregar(nb, csv)
    I = ns["Interpretacao"]
    A = ns["AssistenteMcDonalds"]
    df = ns["df"]

    def conversa(turnos):
        a = A()
        saidas = []
        for msg, interp in turnos:
            ns["interpretar"] = lambda m, interp=interp: I(**interp)
            saidas.append((msg, a.responder(msg)))
        return a, saidas

    def ids(texto):
        import re
        return [int(x) for x in re.findall(r"\[ID (\d+)\]", texto)]

    resultados = []

    def registra(nome, confirmado, detalhe):
        resultados.append((nome, confirmado, detalhe))
        print(f"[{'REPRODUZIDO' if confirmado else 'NÃO reproduzido'}] {nome}\n    {detalhe}\n")

    # P0 carne bovina
    a, s = conversa([
        ("quero lanche", dict(consulta="lanche", restricoes_informadas=False, categoria_desejada="lanche")),
        ("eu nao como carne de vaca", dict(consulta="", restricoes_informadas=True, evita_carne_bovina=True)),
    ])
    r = ids(s[-1][1])
    registra("P0 restrição bovina", any(i in r for i in [42, 48, 49, 50, 51]),
             f"IDs recomendados: {r}; subtipo_atual={a.estado.subtipo_atual!r}; categorias="
             f"{sorted(set(df.loc[r, 'categoria']))}")

    # adicionar ID ignora limite
    a, s = conversa([
        ("quero lanche com no máximo 100 kcal", dict(consulta="lanche", restricoes_informadas=True, max_calorias=100, categoria_desejada="lanche")),
        ("adicione ID 42", dict(intencao="adicionar", consulta="", restricoes_informadas=False, item_referido="ID 42")),
    ])
    registra("Adição por ID ignora limite (ID 42, 530 kcal, limite 100)", 42 in a.estado.pedido, s[-1][1][:120])

    a, s = conversa([
        ("nao como carne de vaca", dict(consulta="", restricoes_informadas=True, evita_carne_bovina=True)),
        ("adicione ID 48", dict(intencao="adicionar", consulta="", restricoes_informadas=False, item_referido="ID 48")),
    ])
    registra("Adição por ID ignora exclusão bovina (ID 48 Hamburger)", 48 in a.estado.pedido, s[-1][1][:120])

    # confirmação de visualização reutilizada para adicionar
    a, s = conversa([
        ("tenho alergia a leite, aceito ver sem garantia", dict(consulta="", restricoes_informadas=True, alergias=["leite"], confirmou_risco_alergia=True)),
        ("adicione ID 49", dict(intencao="adicionar", consulta="", restricoes_informadas=False, item_referido="ID 49")),
    ])
    registra("Ciência para visualizar reutilizada para adicionar (ID 49 Cheeseburger, alergia a leite)",
             49 in a.estado.pedido, s[-1][1][:160])

    # revogação de preferência
    a, s = conversa([
        ("quero lanche, menos sódio", dict(consulta="lanche", restricoes_informadas=True, prefere_menos_sodio=True, categoria_desejada="lanche")),
        ("não me importo mais com sódio", dict(consulta="", restricoes_informadas=True, prefere_menos_sodio=False)),
    ])
    registra("Preferência False não revoga", a.estado.preferencias.get("prefere_menos_sodio") is True,
             f"preferencias={a.estado.preferencias}")

    # frango persiste em bebidas
    a, s = conversa([
        ("quero frango", dict(consulta="frango", restricoes_informadas=True, prefere_frango=True, categoria_desejada="lanche", subtipo_lanche="frango")),
        ("agora quero bebida", dict(consulta="bebida", restricoes_informadas=False, categoria_desejada="bebida")),
    ])
    registra("Preferência por frango persiste em bebidas", "Não encontrei" in s[-1][1] or a.estado.preferencias.get("prefere_frango"),
             f"resposta: {s[-1][1][:120]!r}; preferencias={a.estado.preferencias}")

    # Filet-O-Fish como frango
    sub83 = df.loc[83, "subtipo"]
    registra("Filet-O-Fish (ID 83) classificado como frango", sub83 == "frango", f"subtipo={sub83!r}")

    # without chicken numa busca por frango
    p = I(consulta="frango", restricoes_informadas=True, prefere_frango=True)
    nomes = ns["filtrar_cardapio"](p)["item"].tolist()
    sem = [n for n in nomes if "without Chicken" in n]
    registra("Itens 'without Chicken' aparecem em busca por frango", bool(sem), str(sem))

    # menos de 500 como até 500
    p = I(consulta="menu", restricoes_informadas=True, max_calorias=500)
    f = ns["filtrar_cardapio"](p)
    registra("'menos de 500' tratado como '<= 500'", (f["calorias"] == 500).any(),
             f"itens com exatamente 500 kcal aceitos: {f[f.calorias == 500]['item'].tolist()[:3]}")
    try:
        I(consulta="x", restricoes_informadas=True, max_calorias=float("nan"))
        nan_ok = True
    except Exception:
        nan_ok = False
    try:
        I(consulta="x", restricoes_informadas=True, max_calorias=-5)
        neg_ok = True
    except Exception:
        neg_ok = False
    registra("Esquema aceita NaN/negativo", nan_ok or neg_ok, f"NaN aceito={nan_ok}; negativo aceito={neg_ok}")

    # IDs inválidos
    a = A()
    res = {e: a._identificar_item(e) for e in ["ID -1", "ID 1.5", "2 no pedido", "quero o segundo"]}
    registra("Referências inválidas interpretadas como ID", res["ID -1"] is not None or res["ID 1.5"] is not None or res["2 no pedido"] is not None,
             str(res))
    a.estado.ultimas_recomendacoes = [57, 58, 59]
    registra("'quero o segundo' não seleciona a 2ª opção", a._identificar_item("quero o segundo") != 58,
             f"resultado={a._identificar_item('quero o segundo')}")

    # lista anterior utilizável após consulta sem resultados
    a, s = conversa([
        ("quero lanche sem restrições", dict(consulta="lanche", restricoes_informadas=True, categoria_desejada="lanche")),
        ("lanche com no maximo 1 kcal", dict(consulta="lanche", restricoes_informadas=True, max_calorias=1, categoria_desejada="lanche")),
    ])
    registra("Lista anterior continua ativa após consulta sem resultados", bool(a.estado.ultimas_recomendacoes),
             f"resposta={s[-1][1][:80]!r}; ultimas={a.estado.ultimas_recomendacoes}")

    # restrição nova não reavalia pedido
    a, s = conversa([
        ("quero lanche sem restrições", dict(consulta="lanche", restricoes_informadas=True, categoria_desejada="lanche")),
        ("adicione ID 43", dict(intencao="adicionar", consulta="", restricoes_informadas=False, item_referido="ID 43")),
        ("não como carne bovina", dict(consulta="", restricoes_informadas=True, evita_carne_bovina=True)),
    ])
    registra("Restrição nova não reavalia o pedido (ID 43 Quarter Pounder)", 43 in a.estado.pedido and "seu pedido" not in s[-1][1].lower() and "incompat" not in s[-1][1].lower(),
             s[-1][1][:120])

    # escore zero
    a, s = conversa([
        ("quero lanche sem restrições", dict(consulta="xyzabc", restricoes_informadas=True, categoria_desejada="lanche")),
    ])
    sc = ns["buscar_similares"]("xyzabc", k=3)
    registra("Consulta sem correspondência gera sugestões com escore 0", "Encontrei" in s[-1][1] and all(x == 0 for _, x in sc),
             f"escores={sc}")

    # "sem restrições" não persiste entre turnos
    a, s = conversa([
        ("sem restrições", dict(consulta="", restricoes_informadas=True)),
        ("quero bebida", dict(consulta="bebida", restricoes_informadas=False, categoria_desejada="bebida")),
    ])
    registra("'sem restrições' não persiste: pergunta de restrição repetida", "Antes de recomendar" in s[-1][1], s[-1][1][:100])

    # pergunta nutricional cai na busca
    a, s = conversa([
        ("quero lanche com menos sódio", dict(consulta="lanche", restricoes_informadas=True, prefere_menos_sodio=True, categoria_desejada="lanche")),
        ("quantas calorias tem o Big Mac?", dict(intencao="pergunta", consulta="Big Mac", restricoes_informadas=False, item_referido="Big Mac")),
    ])
    registra("Pergunta de nutriente vira busca genérica", "Encontrei" in s[-1][1] or "prefere" in s[-1][1], s[-1][1][:120])

    # comando local depende do LLM
    a = A()
    def falha(m):
        raise TimeoutError("modelo indisponível")
    ns["interpretar"] = falha
    try:
        a.responder("ver meu pedido")
        dep = False
    except TimeoutError:
        dep = True
    registra("'ver meu pedido' depende do LLM", dep, "TimeoutError propagado" if dep else "respondeu localmente")

    # desalinhamento de IDs
    try:
        df2 = df.sort_values("calorias").reset_index(drop=True)
        ns["df"] = df2
        a = A()
        ns["interpretar"] = lambda m: I(consulta="big mac", restricoes_informadas=True, categoria_desejada="lanche")
        out = a.responder("big mac")
        registra("Reordenar df sem reconstruir TF-IDF", True, "nenhum erro levantado; resposta usa índices TF-IDF desalinhados: " + out[:100])
    except Exception as e:
        registra("Reordenar df sem reconstruir TF-IDF", False, f"detectado: {type(e).__name__}")
    finally:
        ns["df"] = df

    print(f"Total reproduzidos: {sum(1 for r in resultados if r[1])}/{len(resultados)}")


if __name__ == "__main__":
    main()
