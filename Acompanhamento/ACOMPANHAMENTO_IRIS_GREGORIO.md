# Acompanhamento — Iris Gregorio

## 14/09/2026

## 16/09/2026

### Relato individual — Iris Gregorio

Nesse dia fiquei mais na parte de entender a atividade e pesquisar os documentos disponíveis para o cenário. Fui analisando o material para entender melhor a proposta do projeto, os requisitos e quais documentos seriam importantes para as próximas etapas.

## 21/09/2026

### Relato individual — Iris Gregorio

Hoje fiquei responsável por fazer uma melhoria no pipeline, voltada para guardar o histórico das interações do RAG. Fiz a alteração no `src/pipeline.py` para salvar cada execução em um arquivo JSONL, com informações como a pergunta, a resposta, as fontes utilizadas, o tempo de execução e se houve recusa.

Usei o ChatGPT para me ajudar a entender a estrutura do pipeline e pensar na melhor forma de fazer essa gravação do histórico. A partir disso, fiz os ajustes no código e validei a alteração no projeto.

Depois sincronizei meu trabalho com o `main` usando `git pull --rebase` e fiz o push das alterações para o repositório.

### Resumo do dia

Hoje consegui concluir a parte que estava trabalhando no pipeline e deixar a alteração sincronizada com o repositório. O próximo passo é continuar com as próximas tarefas definidas para o cenário.

## 23/09/2026

### Relato individual — Iris Gregorio

Hoje continuei trabalhando na parte técnica do RAG. Fiz alguns ajustes na ingestão das bases estruturada e agregada, principalmente nos metadados de publicação e financiamento, e implementei os filtros por metadados/ano.

Também configurei o Cross-Encoder para o reranking e corrigi a recuperação cross-source, para garantir que as consultas que precisam de mais de uma base realmente recuperem informações das bases envolvidas.

Depois fiz os testes no cenário da Profa. Ana, sobre trabalhos de saúde digital e financiamento externo, e a recuperação funcionou corretamente com as bases necessárias.

Por fim, fiz o commit `599c59f` com as alterações e subi minha parte para o GitHub.

## 25/09/2026

### Relato individual — Iris Gregorio

Hoje dei continuidade às atividades do projeto, verificando o que já havia sido desenvolvido e o que ainda precisava ser validado.

Revisei o arquivo `eval/benchmark.py` e confirmei que as questões Q07 a Q20 do benchmark já estavam incluídas. Também verifiquei o `src/ingest.py` e confirmei que a função `ingest_producao_estruturada()` já estava implementada, não sendo necessário criar uma nova versão.

Trabalhei na ampliação da fixture `tests/fixtures/chunks_sample.json`, acrescentando exemplos para representar melhor as diferentes bases e estruturas do cenário. Depois validei o arquivo e executei o teste `python -m pytest -q tests/test_chunks.py`, que foi concluído com 1 teste aprovado.

Também conferi o `git status` para identificar quais alterações realmente deveriam ser enviadas ao repositório e quais arquivos eram apenas temporários.

Após isso, fiz o commit `4f01301` — `test: amplia fixture de chunks`.

Como havia alterações mais recentes no GitHub, atualizei primeiro o repositório local com `git pull --rebase origin main`, conferi o histórico e, depois, fiz o `git push origin main`.

O envio foi concluído com sucesso e a minha contribuição ficou registrada no GitHub. Os arquivos temporários utilizados durante as verificações (`funcao_temp.txt` e `q07_q20.txt`) não foram incluídos no commit.
## 28/09/2026

### Relato individual — Iris Gregorio

Hoje continuei acompanhando o estado atual do projeto e fiz uma validação da suíte de testes automatizados.

Primeiro conferi o status do repositório e confirmei que minha branch `main` estava sincronizada com o GitHub e sem alterações pendentes nos arquivos do projeto.

Depois executei a suíte completa de testes com `python -m pytest -v`. Foram executados 10 testes, abrangendo validação dos chunks e metadados, guardrails e regras de LGPD, roteamento das consultas, cálculo do RRF e contrato de recuperação.

Todos os 10 testes foram aprovados, sem falhas.

Essa validação ajudou a confirmar que os principais componentes já implementados no projeto continuam funcionando corretamente.

## 30/09/2026

### Relato individual — Iris Gregorio

Hoje continuei verificando o estado atual do projeto e conferindo alguns pontos que ainda precisavam ser validados.

Primeiro revisei o `src/pipeline.py`, o `src/schema.py` e o `src/generate.py` para confirmar se as fontes utilizadas nas respostas estavam sendo registradas corretamente. Verifiquei que o `sources_used` está sendo preenchido e que a estrutura do `RAGResponse` está correta.

Depois conferi os resultados do benchmark e confirmei que existem 20 resultados, correspondentes às questões Q01 a Q20.

Também verifiquei os guardrails. Os casos Q05, Q06 e Q20 foram analisados e os três retornaram `is_refusal: True`, mostrando que as solicitações previstas para recusa estão sendo bloqueadas corretamente.

Na sequência, conferi a parte de mascaramento de e-mails. O código já possui essa proteção por meio da função `mask_sensitive_emails`, porém nenhum dos 20 resultados atuais do benchmark acionou esse caso, então essa parte ainda não foi validada por um caso específico.

Também pesquisei no código se já existiam métricas do RAG Triad, como faithfulness, context relevance e answer relevance, mas não encontrei essa implementação.

Por fim, confirmei que o arquivo `RELATORIO.md` ainda não foi criado.

Com essas verificações, consegui identificar melhor o que já está funcionando no projeto e quais pontos ainda precisam ser trabalhados antes da finalização.

## 02/10/2026

### Relato individual — Iris Gregorio

Hoje realizei testes no projeto para verificar o funcionamento dos componentes já implementados. Ao final da execução, todos os 10 testes foram aprovados, sem falhas.

Essa validação permitiu confirmar que os principais componentes do projeto continuavam funcionando corretamente.

## 05/10/2026

### Relato individual — Iris Gregorio

Hoje realizei novos testes no projeto para verificar o funcionamento dos testes automatizados. Primeiro executei a suíte completa com `pytest`, mas a execução foi interrompida durante a coleta do arquivo `tests/test_unitarios.py` por um erro relacionado à biblioteca `grpc`, mais especificamente à DLL `cygrpc`, que foi bloqueada por uma política de Controle de Aplicativo do Windows.

Para separar o problema do ambiente dos testes do projeto, executei o teste `tests/test_chunks.py` de forma isolada. Nesse caso, o teste foi executado normalmente e apresentou o resultado de 1 teste passado, confirmando que o contrato dos chunks e seus metadados obrigatórios continuam funcionando.

Também tentei verificar especificamente o teste relacionado ao RRF. Porém, a importação de `src.retrieve` continua dependendo do `chromadb` e do `grpc`, impedindo que o teste seja coletado. Tentei ainda isolar a função `compute_rrf`, mas a função utiliza tipos definidos no próprio módulo, como `DocumentChunk`, o que exigiria reproduzir parte do contexto do arquivo apenas para o teste.

Com isso, mantive o código do projeto sem alterações desnecessárias. Os testes realizados ajudaram a identificar que o bloqueio atual está relacionado ao ambiente de execução do Windows e não a uma falha identificada na lógica do RAG. O teste de chunks permanece aprovado.

## 07/10/2026

### Relato individual — Iris Gregorio

Hoje continuei os testes do projeto para verificar se estava tudo funcionando corretamente. Durante a execução dos testes, apareceu um erro no arquivo `src/retrieve.py`, relacionado ao uso do `Any`, que não estava importado.

Fiz a correção diretamente no arquivo e executei novamente os testes. Dessa vez, os 10 testes foram aprovados, sem nenhum erro.

Depois disso, fiz o commit da correção no Git. Na hora de enviar para o GitHub, percebi que o repositório já tinha recebido novos commits do grupo. Então atualizei meu repositório utilizando `pull --rebase`, que foi concluído sem conflitos e manteve minha correção.

Ao final, o projeto ficou atualizado com as alterações mais recentes do grupo e com a correção que realizei.


## 09/10/2026

### Relato individual — Iris Gregorio

Hoje continuei a validação do projeto Adaptive RAG, do Cenário 3 — Inteligência sobre Pesquisa Acadêmica. Executei os testes `tests/test_chunks.py`, `tests/test_guardrails.py` e `tests/test_router.py`, obtendo 8 testes aprovados.

Também investiguei uma inconsistência na resposta da questão Q01 do benchmark, relacionada à identificação de publicações sobre saúde digital e seus financiamentos. Durante a análise, identifiquei que a rotina de carga SQL em `src/db_sql.py` consultava o campo `grants`, mas não contemplava adequadamente o campo `funders` presente nos dados sintéticos.

Realizei uma alteração na rotina para incluir a leitura alternativa de `funders` e criei uma cópia de segurança do banco SQLite antes de continuar a investigação.

Na verificação do banco, constatei que a tabela `artigos` possui 157 registros, todos de origem OpenAlex, sem os registros sintéticos esperados. Por esse motivo, a consulta por financiamento da FAPERJ retornou uma lista vazia.

A correção do código ainda precisa ser validada com a carga dos dados sintéticos e uma nova consulta SQL. Também permanecem pendentes a investigação da resposta contraditória da Q01, a validação final das alterações e a atualização do acompanhamento no Git.

Utilizei a IA como apoio para analisar o código, interpretar os resultados dos comandos no PowerShell e orientar os testes. Não considerei a correção concluída, pois ainda é necessário validar o carregamento dos dados.

## 14/10/2026
### Relato individual — Iris Gregorio

Na atividade registrada para esta data, foi realizada a análise da consistência do índice utilizado pelo projeto Adaptive RAG, com foco na recuperação de informações sobre editais, financiamento e produção científica.

A comparação entre os chunks atuais e os registros do índice ativo identificou divergências de conteúdo, registros ausentes e documentos adicionais. Também foram encontrados registros contendo dados brutos de arquivos PDF, em vez do conteúdo textual esperado.

Para investigar o problema sem substituir o índice ativo, foi preparada uma versão candidata separada, composta por 779 chunks únicos, com conteúdo preenchido e legível, além de vetores de embeddings válidos e documentos preparados para a busca BM25.

Foram verificadas as buscas densa e BM25 e a combinação dos resultados pelo método Reciprocal Rank Fusion (RRF), utilizando uma consulta sobre publicações com menção de financiamento da FAPERJ. Os resultados recuperaram documentos relacionados à produção científica e aos editais normativos. Essa verificação é preliminar e não confirma, por si só, a correção da resposta final do sistema.

O índice candidato foi mantido separado, sem substituir o índice ativo. Permanecem necessárias a verificação da origem dos registros recuperados e a validação dos resultados antes de qualquer alteração definitiva no pipeline.

## 16/10/2026

### Relato individual — Iris Gregorio

Hoje continuei a verificação do funcionamento do Adaptive RAG, retomando os testes de recuperação de documentos utilizados no projeto. Analisei a busca densa e a busca BM25, além da combinação dos resultados pelo método Reciprocal Rank Fusion (RRF).

O foco foi verificar a recuperação de informações relacionadas a editais, financiamento e produção científica. Também retomei a análise da consulta sobre financiamento da FAPERJ, considerando a necessidade de conferir se os documentos recuperados realmente correspondem ao assunto pesquisado.

A análise reforçou que a recuperação dos documentos precisa ser validada em conjunto com os dados da base, principalmente para evitar respostas que não estejam sustentadas pelas informações disponíveis.

## 19/10/2026

### Relato individual — Iris Gregorio

Hoje dei continuidade à análise dos resultados do projeto, com atenção à recuperação de documentos e à consulta relacionada ao financiamento da FAPERJ.

Retomei a verificação do funcionamento do RRF na combinação dos resultados da busca densa e do BM25, considerando os testes anteriores realizados no pipeline. Também revisei os pontos que ainda precisam de validação, principalmente a consistência dos dados recuperados e sua relação com a resposta gerada pelo modelo.

A investigação da questão Q01 e a validação da carga dos dados sintéticos continuam entre os pontos pendentes. O objetivo é garantir que as respostas estejam de acordo com as informações efetivamente disponíveis na base.

## 21/10/2026

### Relato individual — Iris Gregorio

Hoje, dei continuidade à análise da parte de Gestão do Corpus e Ingestão do projeto. Identifiquei divergências entre o inventário do corpus, o manifesto e os caminhos de origem registrados nos chunks, tanto na documentação local quanto na versão disponível no GitHub.

Após a análise, compartilhei essas observações no grupo, solicitando a verificação da versão oficial do corpus e a conferência dos arquivos de origem, para que possamos alinhar a documentação e os dados utilizados pelo sistema.

Como próximo passo, aguardo o alinhamento com o grupo para confirmar as divergências identificadas e definir os ajustes necessários, sem alterar o código ou regenerar os chunks antes dessa validação.

