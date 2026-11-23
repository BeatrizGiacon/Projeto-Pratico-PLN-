import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notebook_loader import executar_notebook  # noqa: E402


def pytest_configure(config):
    config.addinivalue_line("markers", "llm_real: chama o modelo real (requer OPENAI_API_KEY e RUN_LLM_TESTS=1)")


@pytest.fixture(scope="session")
def nb():
    """Namespace do notebook executado uma única vez, sem LLM e com o menu.csv local."""
    return executar_notebook()


@pytest.fixture
def novo(nb):
    """Cria um assistente novo. llm: None, dict {mensagem: kwargs Interpretacao}, callable ou exceção."""
    def _criar(llm=None):
        Interp = nb["Interpretacao"]
        chamadas = []
        if llm is None:
            fn = None
        elif callable(llm):
            def fn(m):
                chamadas.append(m)
                return llm(m)
        else:
            def fn(m):
                chamadas.append(m)
                return Interp(**llm.get(m, {}))
        assistente = nb["AssistenteMcDonalds"](nb["base"], interpretar_fn=fn)
        assistente.chamadas_llm = chamadas
        return assistente
    return _criar


@pytest.fixture
def conversa(novo):
    def _conversa(mensagens, llm=None):
        a = novo(llm)
        respostas = [a.responder(m) for m in mensagens]
        return a, respostas
    return _conversa
