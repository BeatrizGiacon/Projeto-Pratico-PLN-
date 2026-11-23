"""Executa as células de código do notebook fora do Colab, sem rede e sem LLM.

- Células cuja primeira linha começa com '# @colab-only' são ignoradas (credencial, chamada paga).
- Linhas de comando mágico ('!pip', '%...') são removidas.
- requests.get é substituído por uma resposta com o conteúdo do menu.csv local.
- nltk.download é neutralizado (a célula tem alternativa se os recursos faltarem).
- O código extraído é gravado em .pytest_build/notebook_extraido.py e compilado com esse nome,
  o que permite medir a cobertura linha a linha do código do notebook.
"""
import json
import os
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
NOTEBOOK = RAIZ / "projeto_pln.ipynb"
CSV_LOCAL = RAIZ / "menu.csv"
DESTINO = RAIZ / ".pytest_build" / "notebook_extraido.py"


def extrair_codigo(caminho=NOTEBOOK):
    nb = json.loads(Path(caminho).read_text(encoding="utf-8"))
    blocos = []
    for i, celula in enumerate(nb["cells"]):
        if celula["cell_type"] != "code":
            continue
        fonte = "".join(celula["source"])
        if fonte.lstrip().startswith("# @colab-only"):
            continue
        linhas = [l for l in fonte.splitlines() if not l.lstrip().startswith(("!", "%"))]
        blocos.append(f"# ---- célula {i} ({celula['metadata'].get('id', '')}) ----\n" + "\n".join(linhas))
    return "\n\n".join(blocos) + "\n"


class RespostaFalsa:
    def __init__(self, conteudo: bytes, status=200):
        self.content = conteudo
        self.text = conteudo.decode("utf-8", errors="replace")
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def executar_notebook(csv_bytes=None, modelo=None, extra=None):
    """Executa o notebook e devolve o namespace global resultante."""
    codigo = extrair_codigo()
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(codigo, encoding="utf-8")
    conteudo = CSV_LOCAL.read_bytes() if csv_bytes is None else csv_bytes
    ns = {"__name__": "notebook", "display": lambda *a, **k: None, "modelo": modelo}
    if extra:
        ns.update(extra)
    import nltk
    with mock.patch("requests.get", return_value=RespostaFalsa(conteudo)) as get, \
            mock.patch.object(nltk, "download", return_value=True), \
            mock.patch("builtins.print"):
        exec(compile(codigo, str(DESTINO), "exec"), ns)
    ns["_requests_get_mock"] = get
    return ns
