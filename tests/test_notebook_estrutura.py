"""Estrutura do notebook: ordem de execução, inicialização intencional, ausência de segredos, LLM encadeado."""
import json
import re

from notebook_loader import NOTEBOOK, executar_notebook


def _celulas():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]


def test_loop_interativo_nao_executa_automaticamente():
    fonte = "".join(_celulas()[-1]["source"])
    assert "def conversar" in fonte
    assert not re.search(r"^conversar\(\)", fonte, re.M)


def test_sem_chave_no_notebook():
    texto = NOTEBOOK.read_text(encoding="utf-8")
    assert not re.search(r"sk-[A-Za-z0-9_-]{16,}", texto)


def test_modelo_preservado():
    fonte = "".join("".join(c["source"]) for c in _celulas())
    assert 'ChatOpenAI(model="gpt-6-luna"' in fonte


def test_celulas_colab_only_sao_so_credencial_e_chamadas_pagas():
    marcadas = ["".join(c["source"]) for c in _celulas()
                if c["cell_type"] == "code" and "".join(c["source"]).startswith("# @colab-only")]
    assert len(marcadas) == 3
    assert any("getpass" in m for m in marcadas)
    assert any("ChatOpenAI" in m for m in marcadas)


def test_markdown_nao_afirma_tool_calling():
    md = " ".join("".join(c["source"]) for c in _celulas() if c["cell_type"] == "markdown")
    assert "O agente usa ferramentas LangChain para consultar" not in md
    assert "não as invoca" in md


def test_execucao_em_ordem_em_ambiente_novo():
    ns = executar_notebook()  # novo namespace, todas as células em ordem
    assert ns["assistente"].interpretar_fn is None
    assert "demo" in ns and ns["demo"].estado.pedido  # demonstração sem LLM rodou


def test_interpretador_encadeado_com_modelo_falso():
    """Verifica prompt | modelo.with_structured_output sem chamada paga."""
    from langchain_core.runnables import RunnableLambda

    recebidos = []

    class ModeloFalso:
        def with_structured_output(self, schema):
            def responder(prompt_value):
                recebidos.append(prompt_value.to_messages()[-1].content)
                return schema(intencao="recomendar", consulta="frango", restricoes_informadas=True,
                              prefere_menos_sodio=True, max_sodio_mg=500)
            return RunnableLambda(responder)

    ns = executar_notebook(modelo=ModeloFalso())
    assert ns["interpretador"] is not None
    assert ns["assistente"].interpretar_fn is not None
    r = ns["interpretar_llm"]("Quero frango com pouco sódio, até 500 mg")
    assert r.max_sodio_mg == 500 and recebidos[-1] == "Quero frango com pouco sódio, até 500 mg"


def test_interpretar_llm_sem_modelo(nb):
    import pytest
    with pytest.raises(RuntimeError, match="Modelo não configurado"):
        nb["interpretar_llm"]("oi")


def test_conversar_loop(nb, monkeypatch):
    entradas = iter(["", "ver meu pedido", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    saidas = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: saidas.append(" ".join(map(str, a))))
    nb["conversar"](nb["AssistenteMcDonalds"](nb["base"]))
    assert any("vazio" in s for s in saidas)


def test_conversar_captura_erro(nb, monkeypatch):
    class Quebrado:
        def responder(self, m):
            raise RuntimeError("falhou")
    entradas = iter(["oi", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    saidas = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: saidas.append(" ".join(map(str, a))))
    nb["conversar"](Quebrado())
    assert any("Falha ao responder: RuntimeError" in s for s in saidas)


def test_nltk_indisponivel_usa_alternativa():
    from unittest import mock
    with mock.patch("nltk.corpus.stopwords.words", side_effect=LookupError("sem recurso")):
        ns = executar_notebook()
    assert ns["lematizador"] is None
    assert ns["preprocessar_nome"]("The Big Mac") == ["big", "mac"]
    assert "Big Mac" in ns["base"].df["item"].tolist()
