import re

BOVINOS_LANCHE = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55]


def ids(texto):
    """IDs listados como opções/itens numa resposta."""
    return [int(x) for x in re.findall(r"\[ID (\d+)\]", texto)]
