"""Avaliação opcional com o modelo real. Não roda por padrão (consome créditos).

Para executar: OPENAI_API_KEY=... RUN_LLM_TESTS=1 pytest tests/test_llm_real.py -m llm_real
"""
import os

import pytest

pytestmark = [
    pytest.mark.llm_real,
    pytest.mark.skipif(not (os.environ.get("OPENAI_API_KEY") and os.environ.get("RUN_LLM_TESTS") == "1"),
                       reason="Modelo real desativado: defina OPENAI_API_KEY e RUN_LLM_TESTS=1 para autorizar o consumo."),
]


@pytest.fixture(scope="module")
def ns_real():
    from langchain_openai import ChatOpenAI
    from notebook_loader import executar_notebook
    modelo = ChatOpenAI(model="gpt-6-luna", timeout=60, max_retries=1)
    return executar_notebook(modelo=modelo)


def test_conversa_bovina_com_modelo_real(ns_real):
    import re
    a = ns_real["AssistenteMcDonalds"](ns_real["base"], ns_real["interpretar_llm"])
    a.responder("quero lanche")
    r = a.responder("eu nao como carne de vaca")
    recomendados = [int(x) for x in re.findall(r"\[ID (\d+)\]", r)]
    assert not set(recomendados) & {42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55}
