# Auditoria técnica: assistente de pedidos McDonald's (PLN)

**Branch:** `leticia-freitas` · **Revisão auditada:** `f2b45535e01ba4e78bd4a1cb0275a69406cdf0b3`. É o merge do PR #1 da `main`, com notebook e `menu.csv` idênticos aos da `main` em `d33ffbbf2815e76ad3493a6ec648b679c422d7c2`.
**Data:** 23/11/2026 · **Escopo:** `projeto_pln.ipynb` (26 células: Markdown, código e saídas salvas) e `menu.csv` (260 linhas).

> Esta auditoria foi refeita do zero nesta execução. Os achados da auditoria local anterior, que nunca foi publicada, entraram apenas como **hipóteses** e foram reproduzidos no código antes de serem tratados como confirmados. A reprodução está em `evidencias/reproduzir_original.py`, com a saída em `evidencias/reproducao_original_saida.txt`.

## 1. Estado encontrado

| Item | Valor observado |
|---|---|
| Arquivos na branch | `menu.csv`, `projeto_pln.ipynb` (sem `tests/` nem relatórios) |
| `main` | `d33ffbb` (o mesmo SHA antes e depois deste trabalho) |
| Notebook | 26 células, com saídas salvas de uma execução no Colab, incluindo a conversa que reproduz o P0 |
| Fonte do CSV | `raw.githubusercontent.com/.../main/menu.csv`, mantida. O arquivo baixado da `main` tem o mesmo SHA-256 do `menu.csv` local |
| Modelo | `ChatOpenAI(model="gpt-6-luna")`, mantido |

**Limitação do ambiente:** as ferramentas do plugin de integração com o Chrome não estavam disponíveis nesta sessão. O GitHub foi inspecionado pelo `git`, com clone, `ls-remote` e `show`. O Colab **não** pôde ser aberto no navegador, então não foi possível verificar se há alterações não salvas no Colab que divirjam do arquivo do GitHub. Ver a seção 6.

## 2. Bugs reproduzidos no código original

Na reprodução, o LLM foi substituído por uma função que devolve a interpretação **correta** de cada mensagem. Assim, cada falha listada abaixo é da lógica determinística, não do modelo. Resultado: **19 de 19 comportamentos reproduzidos**.

| # | Sev. | Bug | Causa raiz |
|---|---|---|---|
| B1 | **P0** | “eu nao como carne de vaca” recomenda os IDs 42, 48, 49, 50 e 51 (Big Mac, Hamburger, Cheeseburger, Double Cheeseburger, Bacon Clubhouse Burger) | `extrair_subtipo(mensagem)` encontra “carne” dentro da negação e define `subtipo_atual='bovino'`. O filtro `evita_carne_bovina` só exclui nomes com `beef\|angus\|quarter pounder`, então Hamburger, Big Mac etc. passam. As duas falhas se somam. A saída salva do próprio notebook mostra o bug |
| B2 | P0 | Adicionar por ID ignora exclusão e limite (ID 48 com “sem carne bovina”; ID 42 com 530 kcal e limite de 100 kcal) | `responder()` adiciona sem validar o item contra o estado |
| B3 | P0 | A ciência dada para *visualizar* produtos sem garantia autoriza *adicionar* qualquer item (ID 49, Cheeseburger, com alergia a leite) | `ciente_limitacao_alergias` é global e reutilizável |
| B4 | P1 | Uma preferência revogada (`False`) não é removida | `_preferencias` descarta valores `False` |
| B5 | P1 | A preferência por frango persiste ao pedir bebidas, e o resultado fica vazio | `prefere_frango` é um filtro global |
| B6 | P1 | Filet-O-Fish (ID 83) classificado como frango | `subtipo_produto` usa `'chicken' in cat` na categoria compartilhada “Chicken & Fish” |
| B7 | P1 | Itens “(without Chicken)” aparecem em busca por frango (IDs 84 e 87, primeiros na saída salva) | o regex `chicken` casa com “without Chicken” |
| B8 | P1 | “menos de 500” vira “≤ 500” | o esquema só tem `max_*`, aplicado com `<=` |
| B9 | P1 | O esquema aceita NaN e valores negativos | `Optional[float]` sem validação |
| B10 | P1 | “ID -1” → 1, “ID 1.5” → 1, “2 no pedido” → ID 2 | o regex `\d+` ignora o sinal e o decimal |
| B11 | P1 | “quero o segundo” não seleciona a 2ª opção | não há tratamento de ordinais |
| B12 | P1 | A lista anterior continua ativa depois de uma consulta sem resultados | `ultimas_recomendacoes` não é limpa |
| B13 | P1 | Uma nova restrição não reavalia o pedido (ID 43 continua no pedido sem aviso, e o Big Mac volta a ser recomendado) | não há checagem de conflito, e há o efeito de B1 |
| B14 | P2 | Consulta sem correspondência sugere itens com escore 0 | o ranking não tem limiar |
| B15 | P1 | “sem restrições” não persiste: a pergunta volta no turno seguinte | o estado só guarda preferências “verdadeiras” *(novo, não constava da auditoria anterior)* |
| B16 | P2 | “quantas calorias tem o Big Mac?” vira busca genérica | não há resposta por campo |
| B17 | P1 | “ver meu pedido” falha se o LLM falhar (`TimeoutError` propagado) | `interpretar()` é chamado antes de qualquer comando local |
| B18 | P1 | Reordenar o `df` sem reconstruir o TF-IDF não gera erro, e os resultados ficam desalinhados | a verificação de alinhamento só roda na célula 18 |
| B19 | P2 | O loop `conversar()` roda automaticamente em “Executar tudo” | chamada não comentada (o comentário dizia “descomente”) |
| B20 | P2 | O Markdown afirma que “o agente usa ferramentas LangChain”, mas a conversa não as invoca | documentação inconsistente |

## 3. Riscos não reproduzidos ou fora do código

- **Comportamento do LLM real (`gpt-6-luna`).** Não foi avaliado: não havia credencial nesta sessão e não houve autorização de consumo. O código novo trata a saída do LLM como não confiável. Ela só pode **acrescentar** exclusões e alergias, nunca removê-las nem reiniciar o pedido. Isso está coberto por testes com o modelo simulado.
- **Diferença entre o Colab e o GitHub.** Não verificada (ver a seção 6).
- **Disponibilidade do NLTK.** Neste ambiente, `nltk.download` recusa downloads através do proxy. A célula agora tem uma alternativa (stopwords mínimas, sem lematização). No Colab, o download costuma funcionar.

## 4. Limitações do dataset (não são bugs)

Auditoria do `menu.csv` completo:

| Verificação | Resultado |
|---|---|
| Dimensão | 260 linhas × 24 colunas; 9 categorias |
| Nulos / linhas duplicadas / nomes duplicados | 0 / 0 / 0 |
| Tipos | 18 int64, 3 float64, 3 texto; nenhum valor negativo |
| Codificação | UTF-8 válido, sem BOM, sem `\r`; “Jalapeño”, “Frappé” e “M&M’s” preservados; nenhum “®” ou “™” no arquivo atual |
| Coerência | kcal ≈ 4·carb + 4·prot + 9·gord dentro de 25% em todos os itens; gordura saturada ≤ gordura total; açúcar ≤ carboidratos |
| Porção | 118 itens com gramas, 138 em “fl oz cup”, 2 “carton”, 2 “fl oz” (só 3 trazem ml). Sem conversão confiável entre fl oz e g |
| IDs | sem coluna de ID. O `id_menu` é a posição da linha, então qualquer reordenação ou filtragem muda os IDs |
| Abrangência | cardápio histórico dos **EUA**. Não representa o cardápio brasileiro atual |
| Composição | **não há ingredientes, alergênicos nem contaminação cruzada**. Exemplos do impacto: a categoria “Beef & Pork” mistura bovino e suíno (McRib); “Egg McMuffin” não indica proteína no nome; smoothies não indicam laticínio no nome. Nenhum item pode ser declarado seguro ou livre de um ingrediente com base no CSV |
| Zeros | 16 itens com 0 kcal (Diet Coke, Diet Dr Pepper, Dasani, Iced Tea, Coffee). São valores plausíveis, não ausências |

## 5. Sugestões que não são defeitos

Estão em `MELHORIAS_PROJETO.md`: fonte oficial de alergênicos, ID estável no CSV, quantidades (“2 Big Macs”), avaliação do LLM com um conjunto rotulado e embeddings multilíngues.

## 6. O que não foi possível verificar

| Etapa pedida | Situação |
|---|---|
| Abrir o Colab e o GitHub pelo plugin do Chrome | **Bloqueado.** As ferramentas do plugin não estavam disponíveis nesta sessão na nuvem. Também não usei um navegador remoto de terceiros, que exigiria login Google e serviço pago |
| Comparar o notebook aberto no Colab com o do GitHub | **Pendente.** Depende do acesso ao Colab |
| Executar com o `gpt-6-luna` | **Pendente.** Sem credencial e sem autorização de consumo. Teste opcional em `tests/test_llm_real.py` |
| “Executar tudo” num ambiente novo | **Feito localmente** com um kernel Jupyter novo (`nbclient`), baixando o CSV real da `main`, sem as 3 células `@colab-only`. Nenhum erro. Saídas em `evidencias/notebook_executado_sem_llm.ipynb` |

O roteiro de conferência manual no Colab está em `COLAB_EXECUCAO.md`.
