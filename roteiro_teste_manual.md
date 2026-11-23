## Roteiro de teste manual

Este roteiro ainda não foi executado no navegador. 

| # | Digite | Esperado |
|---|---|---|
| 1 | `quero lanche` → `eu nao como carne de vaca` | nenhum dos IDs 42–56; aviso “ingredientes não foram verificados” |
| 2 | `adicione ID 42` | “Não adicionei Big Mac (ID 42): o nome indica carne bovina” |
| 3 | `quero sobremesa com menos de 300 calorias` | todos os itens com kcal < 300; os valores exibidos batem com o CSV |
| 4 | `agora quero bebida` → `adicione o segundo` | a lista muda para bebidas; o 2º item da lista é adicionado |
| 5 | `tenho alergia a leite` → `adicione ID 101` | pedido de confirmação “confirmo adicionar ID 101” e o aviso de alergia; nada é adicionado antes disso |
| 6 | `ver meu pedido` | itens, totais do CSV e aviso de alergia |
| 7 | Ambiente de execução → Desconectar e excluir → Executar tudo | nenhuma célula falha; a conversa não inicia sozinha |

Se algo divergir, registre a mensagem e a resposta e rode `pytest` localmente.
