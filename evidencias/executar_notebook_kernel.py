"""Executa o notebook num kernel Jupyter novo, na ordem das células ("Executar tudo").

As células marcadas '# @colab-only' (getpass, ChatOpenAI e exemplo com chamada paga) são
substituídas por `modelo = None`. O CSV é baixado de verdade da branch main.
Uso: python evidencias/executar_notebook_kernel.py projeto_pln.ipynb evidencias/notebook_executado_sem_llm.ipynb
"""
import sys

import nbformat
from nbclient import NotebookClient

entrada, saida = sys.argv[1], sys.argv[2]
nb = nbformat.read(entrada, as_version=4)
for c in nb.cells:
    if c.cell_type == "code" and c.source.lstrip().startswith("# @colab-only"):
        c.source = "# [célula @colab-only omitida nesta execução local: sem credencial e sem chamada paga]\nmodelo = None"
NotebookClient(nb, timeout=600, kernel_name="python3").execute()
nbformat.write(nb, saida)
print("Execução concluída sem erros:", saida)
