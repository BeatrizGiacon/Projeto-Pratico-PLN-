# Como executar e conferir no Google Colab

## Abrir

Abra o notebook da branch desta integrante:
`https://colab.research.google.com/github/BeatrizGiacon/Projeto-Pratico-PLN-/blob/leticia-freitas/projeto_pln.ipynb`

O `menu.csv` continua sendo baixado da branch `main`, que é a fonte compartilhada.

## Credencial

1. Ícone de chave (Secrets) → adicionar `OPENAI_API_KEY` → ativar o acesso para o notebook.
2. Sem o Secret, a célula pede a chave com `getpass`, que não aparece na tela.
3. Não cole a chave no código e não salve a saída da célula de chave.

## Ordem

`Ambiente de execução → Executar tudo`. A conversa **não** inicia sozinha. No fim:

```python
conversar()
```

A célula “Demonstração sem custo” roda a conversa de auditoria **sem chamar o modelo**. Ela serve para verificar as regras sem consumir créditos.

## Roteiro de conferência manual

Este roteiro ainda não foi executado no navegador. Marque cada item ao conferir.

| # | Digite | Esperado |
|---|---|---|
| 1 | `quero lanche` → `eu nao como carne de vaca` | nenhum dos IDs 42–56; aviso “ingredientes não foram verificados” |
| 2 | `adicione ID 42` | “Não adicionei Big Mac (ID 42): o nome indica carne bovina” |
| 3 | `quero sobremesa com menos de 300 calorias` | todos os itens com kcal < 300; os valores exibidos batem com o CSV |
| 4 | `agora quero bebida` → `adicione o segundo` | a lista muda para bebidas; o 2º item da lista é adicionado |
| 5 | `tenho alergia a leite` → `adicione ID 101` | pedido de confirmação “confirmo adicionar ID 101” e o aviso de alergia; nada é adicionado antes disso |
| 6 | `ver meu pedido` | itens, totais do CSV e aviso de alergia |
| 7 | Ambiente de execução → Desconectar e excluir → Executar tudo | nenhuma célula falha; a conversa não inicia sozinha |

Se algo divergir, registre a mensagem e a resposta e rode `pytest` localmente (ver `RELATORIO_TESTES.md`).
