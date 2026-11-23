# Melhorias sugeridas (não são defeitos)

Prioridade em ordem decrescente de impacto para o usuário.

1. **Fonte de ingredientes e alergênicos.** Associar cada item a uma tabela oficial (de preferência do cardápio brasileiro atual, com data e URL) em um arquivo separado, por exemplo `composicao.csv` com `id_menu`, ingrediente e fonte. Com isso, `avaliar_item` passaria a usar o estado `confirmado_sem` em vez de `nao_indicado`. Sem essa fonte, o assistente deve continuar dizendo que a composição não foi verificada.
2. **ID estável no `menu.csv` da `main`.** Hoje o `id_menu` é a posição da linha. Uma coluna `id` fixa evita que uma reordenação ou inclusão no CSV mude o significado de “ID 42” em pedidos já salvos. A mudança afeta a `main` e precisa de acordo da equipe.
3. **Cardápio brasileiro.** O dataset é histórico e dos EUA. Para a apresentação, convém deixar isso explícito ou trocar a fonte, com acordo do grupo.
4. **Quantidades.** “quero 2 Big Macs” hoje gera a pergunta “ID 2 ou opção 2?”. Um campo `quantidade` na análise local resolveria.
5. **Avaliação do LLM.** Montar de 50 a 100 frases rotuladas (intenção, exclusões, limites) e medir a acurácia do `gpt-6-luna` contra `analisar_mensagem`, em uma execução única e com orçamento autorizado. O teste `tests/test_llm_real.py` é o ponto de partida.
6. **Busca semântica multilíngue.** O TF-IDF trabalha sobre nomes em inglês. A expansão PT→EN cobre os termos comuns, mas embeddings multilíngues melhorariam consultas livres. Isso exige revisar o custo, porque embeddings de API são pagos.
7. **Unidades de porção.** Converter “fl oz” para ml (1 fl oz ≈ 29,57 ml) permitiria limites por volume.
8. **Interface.** Um `ipywidgets` com caixa de texto e histórico deixaria a demonstração no Colab mais fluida que o `input()`.
9. **CI.** Um workflow do GitHub Actions rodando `pytest` (sem LLM) a cada push protegeria as regressões. Não foi criado para não mexer na configuração do repositório sem acordo da equipe.
