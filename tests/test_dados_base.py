"""CSV completo, preparação, alinhamento DataFrame/documentos/TF-IDF e robustez a dados ruins."""
import io

import pandas as pd
import pytest

from notebook_loader import CSV_LOCAL, executar_notebook


def test_csv_original_esquema_e_qualidade():
    bruto = pd.read_csv(CSV_LOCAL)
    assert bruto.shape == (260, 24)
    assert int(bruto.isna().sum().sum()) == 0
    assert int(bruto.duplicated().sum()) == 0
    assert int(bruto["Item"].duplicated().sum()) == 0
    numericas = bruto.select_dtypes("number")
    assert numericas.shape[1] == 21
    assert int((numericas < 0).sum().sum()) == 0
    CSV_LOCAL.read_bytes().decode("utf-8")  # codificação UTF-8 válida


def test_base_preparada(nb):
    df = nb["base"].df
    assert df["id_menu"].tolist() == list(range(260))
    assert not df["item"].str.contains("®|™").any()
    assert df["porcao_g"].notna().sum() == 260 - 142 + df["porcao_texto"].str.contains(r"\(\d+(?:\.\d+)? g\)").sum() - 118
    assert set(df["grupo"]) == {"lanche", "bebida", "cafe", "acompanhamento", "sobremesa"}
    nb["verificar_base"](nb["base"])


def test_documentos_e_tfidf_alinhados(nb):
    b = nb["base"]
    assert [d.metadata["id_menu"] for d in b.documentos] == list(range(len(b.df)))
    assert b.indice.matriz.shape[0] == len(b.df)
    resultado = nb["buscar_similares"](b.indice, "big mac", k=1)
    assert b.df.loc[resultado[0][0], "item"] == "Big Mac"


def test_desalinhamento_detectado(nb):
    b = nb["base"]
    reordenado = b.df.sort_values("calorias").reset_index(drop=True)
    quebrada = nb["BaseMenu"](reordenado, b.documentos, b.indice, b.assinatura)
    with pytest.raises(ValueError, match="desalinhada"):
        nb["verificar_base"](quebrada)
    with pytest.raises(ValueError, match="desalinhada"):
        nb["AssistenteMcDonalds"](quebrada)


def test_mutacao_in_place_detectada_no_turno(nb):
    b = nb["construir_base"](pd.read_csv(CSV_LOCAL))
    a = nb["AssistenteMcDonalds"](b)
    b.df.drop(index=0, inplace=True)
    with pytest.raises(ValueError, match="desalinhada"):
        a.responder("quero lanche")


def test_construir_indice_recusa_documentos_de_outra_tabela(nb):
    b = nb["base"]
    with pytest.raises(ValueError):
        nb["construir_indice"](b.df.iloc[:10], b.documentos)


def test_buscar_ids_fora_do_indice(nb):
    with pytest.raises(IndexError):
        nb["buscar_similares"](nb["base"].indice, "x", ids_permitidos=[-1])
    assert nb["buscar_similares"](nb["base"].indice, "x", ids_permitidos=[]) == []
    assert nb["buscar_similares"](nb["base"].indice, "  ") == []


def test_colunas_ausentes(nb):
    bruto = pd.read_csv(CSV_LOCAL).drop(columns=["Sodium"])
    with pytest.raises(ValueError, match="Colunas ausentes"):
        nb["preparar_menu"](bruto)


def test_csv_vazio_ou_sem_linhas(nb):
    with pytest.raises(ValueError):
        nb["preparar_menu"](pd.DataFrame())
    with pytest.raises(ValueError):
        nb["preparar_menu"](pd.read_csv(CSV_LOCAL).iloc[0:0])
    with pytest.raises(ValueError, match="vazio"):
        executar_notebook(csv_bytes=b"   \n")
    with pytest.raises(ValueError, match="não tem linhas"):
        executar_notebook(csv_bytes=CSV_LOCAL.read_bytes().splitlines()[0] + b"\n")


def test_csv_indisponivel(nb):
    from unittest import mock
    from notebook_loader import RespostaFalsa
    with mock.patch("requests.get", return_value=RespostaFalsa(b"", status=404)):
        with pytest.raises(RuntimeError, match="404"):
            nb["carregar_menu_bruto"]()


def test_valores_nulos_negativos_e_nao_numericos_viram_nan(nb):
    bruto = pd.read_csv(CSV_LOCAL)
    bruto["Calories"] = bruto["Calories"].astype(object)
    bruto.loc[0, "Calories"] = None
    bruto.loc[1, "Calories"] = -10
    bruto.loc[2, "Calories"] = "abc"
    bruto.loc[3, "Calories"] = float("inf")
    bruto.loc[4, "Item"] = None
    df = nb["preparar_menu"](bruto)
    assert len(df) == 259
    assert df.loc[:2, "calorias"].isna().all()
    assert df["id_menu"].tolist() == list(range(259))
    texto = nb["formatar_item"](df.loc[0].to_dict())
    assert "não informado kcal" not in texto and "não informado" in texto


def test_csv_alterado_reconstroi_base_consistente(nb):
    bruto = pd.read_csv(CSV_LOCAL).sample(frac=1, random_state=1).head(50)
    b = nb["construir_base"](bruto)
    nb["verificar_base"](b)
    a = nb["AssistenteMcDonalds"](b)
    r = a.responder("sem restrições")
    assert "Você prefere" in r


def test_bom_utf8(nb):
    from unittest import mock
    from notebook_loader import RespostaFalsa
    with mock.patch("requests.get", return_value=RespostaFalsa(b"\xef\xbb\xbf" + CSV_LOCAL.read_bytes())):
        bruto = nb["carregar_menu_bruto"]()
    assert "Category" in bruto.columns


def test_url_do_csv_continua_na_main(nb):
    assert nb["URL_MENU"] == "https://raw.githubusercontent.com/BeatrizGiacon/Projeto-Pratico-PLN-/main/menu.csv"
    nb["_requests_get_mock"].assert_called_once()
    assert nb["_requests_get_mock"].call_args[0][0] == nb["URL_MENU"]


def test_ferramentas(nb):
    assert "Big Mac" in nb["consultar_item_por_id"].invoke({"id_menu": 42})
    assert "inexistente" in nb["consultar_item_por_id"].invoke({"id_menu": -1})
    assert "inexistente" in nb["consultar_item_por_id"].invoke({"id_menu": 260})
    assert "Nenhum item" in nb["consultar_menu"].invoke({"consulta": "xyzabc"})
    assert "McNuggets" in nb["consultar_menu"].invoke({"consulta": "chicken mcnuggets"})


def test_mostrar_cardapio(nb):
    assert "Filet-O-Fish" in nb["mostrar_cardapio"]("lanche", "peixe")
    assert "Nenhum produto" in nb["mostrar_cardapio"]("lanche", "inexistente")
    assert "e mais" in nb["mostrar_cardapio"]("bebida", limite=3)


def test_normalizar(nb):
    n = nb["normalizar"]
    assert n("  Não   Como ") == "nao como"
    assert n(None) == "" and n(float("nan")) == ""
