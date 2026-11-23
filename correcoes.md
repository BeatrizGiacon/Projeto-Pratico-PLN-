# Plano de correções (status desta execução)

Todas as correções foram feitas **no próprio notebook** `projeto_pln.ipynb`, para manter a compatibilidade com o Colab, sem módulo externo. O modelo (`gpt-6-luna`) e a URL do `menu.csv` na `main` foram mantidos.

## Arquitetura resultante

```
mensagem ─► analisar_mensagem (regras PT, sem LLM)
             │  comando local? ──► ver pedido / adicionar / remover / confirmar / nutriente / composição
             ▼
           interpretar_llm (opcional; falha => segue só com a análise local, pedido intacto)
             ▼
           _aplicar_restricoes: exclusões, dieta, alergias, intolerâncias, limites, preferências
             │  (o LLM só acrescenta restrições; mudança => invalida lista, cancela confirmação e reavalia o pedido)
             ▼
           _recomendar: filtro de grupo/subtipo ► avaliar_item (bloqueia) ► TF-IDF só entre permitidos ► ordenação
```

`avaliar_item(base, estado, id)` é a **regra única** usada na recomendação, no ranking (aplicada antes dele), na adição por ID, nome, posição ou LLM, e na revisão do pedido.

## Correções por bug

| Bug | Correção | Status | Testes |
|---|---|---|---|
| B1 P0 bovino | (a) negação analisada por cláusula: palavras negadas nunca viram subtipo; (b) estado por proteína (`indicado`, `possivel`, `ausencia_indicada`, `nao_indicado`) a partir de um léxico curado. Categoria compartilhada ou sanduíche sem recheio descrito = `possivel`, que também é bloqueado; (c) subtipo do LLM ignorado se contradiz uma exclusão | **Corrigido** | `test_restricoes_proteina.py` (regressão com LLM correto e com LLM errado) |
| B2 | `_adicionar` chama `avaliar_item` para qualquer forma de referência | **Corrigido** | `test_adicionar_bovino_bloqueado_por_id_nome_e_posicao`, `test_adicao_por_id_respeita_limite` |
| B3 | confirmação **por item** (`confirmo adicionar ID N`), consumida no uso e cancelada por mudança de estado; a ciência para visualizar não autoriza adição; o texto diz que a confirmação não significa segurança | **Corrigido** | `test_alergias.py` |
| B4 | preferências com três estados (`None`/`True`/`False`); revogação local e via LLM | **Corrigido** | `test_revogacao_de_preferencia_*` |
| B5 | o frango virou subtipo de navegação, limpo ao trocar de categoria; exclusões rígidas persistem | **Corrigido** | `test_mudanca_de_categoria_limpa_subtipo`, `test_exclusao_persiste_entre_categorias` |
| B6 | subtipo derivado do **nome** (prioridade nuggets > peixe > frango > bovino > porco) | **Corrigido** | `test_filet_o_fish_nao_e_frango` |
| B7 | `without chicken` → `ausencia_indicada`; a busca por frango exige `indicado` | **Corrigido** | `test_without_chicken_*` |
| B8 | limites guardados como `(operador, valor)` com `<`, `<=`, `>`, `>=`; conversão g↔mg para sódio e açúcar | **Corrigido** | `test_leitura_de_limites`, `test_fronteira_menos_de_exclui_e_ate_inclui` |
| B9 | `Field(ge=0)` e `allow_inf_nan=False`; números negativos no texto recusados com mensagem | **Corrigido** | `test_esquema_rejeita_nan_infinito_negativo`, `test_limite_negativo_rejeitado` |
| B10 | ID só com o prefixo “ID”, inteiro e dentro do intervalo; número solto gera pergunta (“ID 2 ou opção 2?”) | **Corrigido** | `test_referencias_invalidas_ou_ambiguas` |
| B11 | ordinais (primeiro…quinto, último, 2º, “opção 3”) | **Corrigido** | `test_selecao_por_posicao` |
| B12 | a lista é invalidada após uma consulta sem resultado ou uma mudança de restrição, com o motivo informado | **Corrigido** | `test_lista_invalidada_*` |
| B13 | conflitos no pedido são listados quando uma restrição muda e ao ver o pedido; nada é removido sem pedido explícito | **Corrigido** | `test_nova_restricao_reavalia_pedido` |
| B14 | consulta específica com escore máximo 0 → “Não encontrei 'x'”; termos genéricos não contam como consulta; expansão PT→EN (frango→chicken, batata→fries…) | **Corrigido** | `test_consulta_sem_correspondencia_*`, `test_busca_pt_para_nomes_em_ingles` |
| B15 | `restricoes_respondidas` persiste; a pergunta é feita uma única vez | **Corrigido** | `test_sem_restricoes_persiste`, `test_pergunta_restricao_apenas_uma_vez` |
| B16 | resposta determinística por campo (calorias, sódio, açúcar, proteína, gordura, colesterol, carboidratos, cálcio, porção) | **Corrigido** | `test_pergunta_nutriente_*` |
| B17 | comandos locais antes do LLM; falha do LLM vira um aviso e o fluxo segue com a análise local | **Corrigido** | `test_falha_do_llm_*`, `test_pergunta_nutriente_nao_chama_llm` |
| B18 | `construir_base` cria tabela, documentos e TF-IDF juntos; `verificar_base` roda na criação do assistente e em cada turno | **Corrigido** | `test_dados_base.py` |
| B19 | `conversar()` comentado; célula de demonstração sem LLM | **Corrigido** | `test_loop_interativo_nao_executa_automaticamente` |
| B20 | Markdown reescrito: as ferramentas existem, mas não são invocadas por *tool calling* | **Corrigido** | `test_markdown_nao_afirma_tool_calling` |

## Itens bloqueados ou dependentes de terceiros

| Item | Motivo |
|---|---|
| Garantia de ausência de ingrediente ou alergênico | Impossível com este CSV. Exige uma fonte oficial de ingredientes (ver `MELHORIAS_PROJETO.md`) |

## Decisões conservadoras (e seu custo)

- Sob uma exclusão, itens `possivel` são bloqueados. Quem exclui frango não vê o Filet-O-Fish, e quem exclui bovino não vê o McRib, porque a categoria compartilhada não permite descartar a outra proteína.
- O léxico de alergênicos só **bloqueia** quando o nome indica. Itens não indicados continuam aparecendo, sempre com o aviso. Exemplo: smoothies aparecem para quem tem alergia a leite, porque o nome não indica laticínio.
