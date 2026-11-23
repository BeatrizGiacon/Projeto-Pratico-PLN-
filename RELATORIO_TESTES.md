# Relatório de testes

Resultados **desta execução** (23/11/2026), sobre o notebook corrigido da branch `leticia-freitas`.

## Como rodar

```bash
pip install -r requirements-dev.txt
python -m pytest --cov=.pytest_build --cov-branch --cov-report=term-missing
```

Os testes executam as próprias células de código do notebook (`tests/notebook_loader.py`):
- ignoram as 3 células marcadas `# @colab-only` (chave e chamadas pagas);
- substituem `requests.get` pelo `menu.csv` local e `nltk.download` por um no-op;
- usam o LLM simulado (funções que devolvem `Interpretacao`).

Por isso, os testes **não exigem chave nem rede e não geram custo**. O código extraído é gravado em `.pytest_build/notebook_extraido.py`, o que permite medir a cobertura linha a linha do notebook.

## Ambiente

Python 3.13.18 · pytest 9.1.1 · pytest-cov 7.1.0 · pandas 3.0.5 · scikit-learn 1.9.1 · pydantic 2.13.5 · langchain-core 1.8.4 · nltk 3.10.4 · nbclient 0.11.0 · Linux (container na nuvem).

## Resultado

| Métrica | Valor |
|---|---|
| Testes coletados | 184 |
| Aprovados | **183** |
| Reprovados | **0** |
| Ignorados | **1** (`test_llm_real.py`: modelo real desativado, sem credencial e sem autorização de consumo) |
| Cobertura de linhas (código do notebook) | **99,1%** (966/975) |
| Cobertura de ramos | **96,6%** (452/468) |
| Cobertura combinada (coverage.py) | **98%** |

Saída completa: `evidencias/pytest_saida.txt`.

**Linhas não cobertas (9):** recusa de CSV só com nomes vazios (59); `grupo_produto`/`subtipo_produto` para categorias e nomes que não existem no CSV atual (256–257, 292); conversões raras de unidade (518, 531); retorno antecipado de mensagem vazia na análise (561); dois ramos do fluxo de LLM (956, 1108). A alternativa sem NLTK é coberta por `test_nltk_indisponivel_usa_alternativa`.

## Cobertura por requisito

| Arquivo | Testes | Requisitos cobertos (exemplos de testes) |
|---|---|---|
| `test_restricoes_proteina.py` | 30 | regressão P0 com o LLM correto e com o LLM errado (`test_regressao_*`); 9 variantes de negação com e sem acento ou maiúsculas; bovino sem “beef” no nome; o ranking não reintroduz excluídos; adição por ID, nome e posição bloqueada; frango, porco, peixe, vegetariano, vegano, “só como frango”, “carne” genérica; Filet-O-Fish; “without Chicken” |
| `test_alergias.py` | 13 | sinônimos (glúten, lactose, celíaco, camarão); alergia a peixe não vira preferência; aviso sempre presente; item com alergênico no nome recusado; confirmação por item, não reutilizável, cancelada por mudança de estado; ciência ≠ autorização; o LLM não remove alergia; intolerância |
| `test_limites_preferencias.py` | 36 | 12 formas de limite (operadores e unidades g/mg/kcal); limite ambíguo gera pergunta ou é resolvido pelo LLM mantendo o operador; fronteira “menos de 500” × “até 500”; negativos, NaN, infinito e unidade incompatível; valor ausente; preferências relativas; revogação e substituição sem apagar outras restrições |
| `test_conversa_pedido.py` | 39 | pergunta de restrição única; persistência; troca de categoria; seleção por posição (6 formas); referências inválidas (ID -1, 1.5, 9999, número solto); nome exato e ambíguo; duplicatas, remoção, pedido vazio, reinício; o LLM não reinicia; conflitos após nova restrição; lista invalidada; escore zero; busca PT→EN; perguntas de nutriente sem chamar o LLM; falha ou timeout do LLM |
| `test_caminhos_complementares.py` | 18 | exclusões, dieta, intolerância e subtipo vindos do LLM; limite local prevalece sobre o do LLM; categoria inválida do LLM ignorada; termos da primeira mensagem preservados; perguntas sem referência; valor ausente no total do pedido |
| `test_linguagem_exploratoria.py` | 19 | frases encontradas por exploração adversarial nesta revisão (“café da manhã sem carne”, “pode ser frango”, “nada de origem animal”, “sem glúten”, “menos sal” etc.) |
| `test_dados_base.py` | 17 | esquema e qualidade do CSV; CSV vazio, sem linhas, HTTP 404, colunas ausentes, nulos, negativos, texto e infinito em colunas numéricas, BOM, CSV alterado; alinhamento de DataFrame, documentos e TF-IDF; mutação detectada; URL da `main`; ferramentas |
| `test_notebook_estrutura.py` | 11 | loop não automático; sem chave; `gpt-6-luna` preservado; só 3 células `@colab-only`; Markdown sem alegar *tool calling*; execução em ambiente novo; encadeamento prompt→modelo com modelo falso; alternativa sem NLTK; `conversar()` com entradas simuladas |
| `test_llm_real.py` | 1 | conversa P0 com o modelo real (ignorado sem autorização) |

## Validação determinística × avaliação do modelo real

- **Determinística (executada):** todos os testes acima. Eles verificam as regras de código. O LLM é simulado tanto com respostas corretas quanto com respostas erradas ou inválidas.
- **Modelo real (não executada):** `tests/test_llm_real.py` roda a conversa P0 com o `gpt-6-luna`. Só executa com `OPENAI_API_KEY` definida **e** `RUN_LLM_TESTS=1`. Não foi executado: não havia credencial e não houve autorização de consumo.

## Execução do notebook em ambiente novo

`python evidencias/executar_notebook_kernel.py projeto_pln.ipynb evidencias/notebook_executado_sem_llm.ipynb`

O script executa as células em ordem num kernel Jupyter novo, com o CSV **baixado da `main`** (SHA-256 `59f629b3…`, idêntico ao local) e com as células `@colab-only` substituídas por `modelo = None`. Resultado: **0 erros**. A célula de demonstração mostra:

1. “quero lanche” → pergunta de restrição; “eu nao como carne de vaca” → IDs 57–61 (sanduíches de frango), com o aviso de composição não verificada.
2. “adicione ID 42” → “Não adicionei Big Mac (ID 42): o nome indica carne bovina”.
3. “quero sobremesa com menos de 300 calorias” → IDs 103, 104, 105, 106 e 109, com 250, 160, 150, 45 e 280 kcal (valores do CSV).
4. “adicione o segundo” → Chocolate Chip Cookie (ID 104).
5. “tenho alergia a leite” → itens com leite indicado no nome são removidos e o aviso de alergia aparece; “adicione ID 101” → pede a confirmação por item, sem adicionar.

## Reprodução no código original

`python evidencias/reproduzir_original.py <notebook original> menu.csv`, com o notebook de `f2b4553` obtido por `git show`: **19 de 19** comportamentos reproduzidos (`evidencias/reproducao_original_saida.txt`).

## Não executado

| O quê | Por quê |
|---|---|
| Fluxo no Colab pelo Chrome | Ferramentas do plugin indisponíveis nesta sessão (ver `COLAB_EXECUCAO.md` para o roteiro manual) |
| `gpt-6-luna` real | Sem credencial e sem autorização de consumo |
