# Encontro 1 14/09/2026
    Hoje conversamos como ficaria a divisão das tarefas, escolhi o Marcos pra ser nosso líder do grupo, criei a pasta com o repositório do Grande Desafio IA Generativa RAG, criei um grupo de WhatsApp com os integrantes do grupo pra ter melhor conversa sobre o desenvolvimento, escolhi o cenário 3 e por hoje foi só isso.
# Resumo do dia em conjunto: o que a equipe entregou, o que travou, qual o próximo passo.

# Encontro 2 16/09/2026
Hoje foquei na estruturação da Etapa 1 do nosso projeto e deixei o pipeline de coleta e observabilidade totalmente operacional.

Criei a estrutura de código (`src/`)**: Organizei os módulos centrais da nossa arquitetura no VS Code:
    - Implementei o `src/fetch_corpus.py` com suporte aos subcomandos de CLI (`fetch`, `update`, `inventory`), garantindo a coleta idempotente e o versionamento em disco.
    - Montei o `src/obs.py` para garantir o logging estruturado em `.jsonl` e a medição de latência e consumo de tokens por etapa.
    - Defini os schemas em `src/schema.py` com Pydantic para validar metadados como sensibilidade, natureza das bases e respostas.
Ajustei o manifesto e rodei a coleta**: Corrigi a sintaxe YAML do `corpus_manifest.yaml` (ajustando os comentários com `#`), executei a coleta inicial via terminal e validei a geração automática dos artefatos em `data/inventory/v1.json` e no `CORPUS_INVENTORY.md`.

Sincronizei no GitHub**: Realizei o commit de todas as alterações da estrutura e dos inventários gerados e fiz o `git push` para o repositório.

Próximos passos:

- Avançar para a Etapa 2: implementar o fatiamento (chunking) dos textos e a geração de embeddings para o índice vetorial.

 # Encontro 3 - 18/09/2026

## O que eu fiz hoje:
- Selecionei e baixei os 3 artigos em PDF referentes ao Cenário 3 (Pesquisa Acadêmica / RAG).
- Coloquei os arquivos PDF dentro do diretório `data/raw/v1/editais_normativo/`.
- Configurei o arquivo `corpus_manifest.yaml` adicionando os nomes exatos dos 3 PDFs.
- Executei o comando no terminal para coletar o corpus e gerar o inventário (`data/inventory/v1.json` e `CORPUS_INVENTORY.md`).
- Fiz anotações no meu Notion pessoal.

## Próxima etapa:
- Iniciar a Etapa 2 do projeto: realizar o processamento e a divisão dos textos (chunking) dos arquivos PDF para a base de conhecimento RAG.

# Encontro 4 - 21/09/2026

## O que eu fiz hoje:
- Alinhamento e Pesquisa do Escopo: Realizei pesquisas para alinhar a estrutura do Cenário 3 (Inteligência sobre Pesquisa Acadêmica) ao problema real de cruzamento de dados de fomento.
- Mapeamento de Fontes Oficiais: Identifiquei e mapeei os repositórios oficiais de normas e editais de fomento (como FAPERJ e CNPq) para compor a base `editais_normativo`.
- Revisão da Arquitetura do Corpus: Planejei a substituição do corpus preliminar pelos documentos normativos corretos que serão consumidos na Etapa 1.
- Fiz anotações de pesquisas no Gemini no meu Notion pessoal.

## Próxima etapa:
- Baixar os editais reais em PDF (FAPERJ/CNPq) para a pasta `data/raw/v1/editais_normativo/`.
- Atualizar o manifesto (`corpus_manifest.yaml`) e rodar o script de coleta para consolidar o inventário v1 no VS Code.

# Encontro 5 - 23/09/2026

## O que eu fiz hoje:

- Testes de Ingestão e Processamento: Executei o script de ingestão (`python -m src.ingest`), gerando com sucesso 2145 chunks salvos em `data/chunks_v1.json`.
- Diagnóstico do Pipeline de Embeddings: Iniciei a execução da geração de embeddings (`src.pipeline`/`src.index`), identificando um travamento por timeout na conexão da API (`Connection error` / parada na requisição HTTP).
- Ajuste de Parâmetros de Execução: Mapeei a necessidade de otimizar o tamanho do lote (`BATCH_SIZE`) e o tempo de pausa (`RATE_LIMIT_PAUSE_SEC`) para evitar estouro de limite de requisições.

## Próxima etapa:

- Ajustar os parâmetros no arquivo de configuração (`config.py` / `.env`) reduzindo o lote para requisições menores.
- Rodar novamente o script de indexação e validar a suíte de testes com `python -m pytest`.

## Encontro 6 - 25/09/2026

### O que fiz hoje:

Concluí com sucesso a execução, teste, validação e expansão de corpus ponta a ponta de todos os módulos do projeto referentes ao Cenário 3 (Inteligência sobre Pesquisa Acadêmica - FAPERJ/CNPq).

### Atividades e Testes Realizados Hoje

1. Ajuste de Dependências e Ambiente
    - Resolvi a divergência de digitação do arquivo de dependências e validei a presença do requirements.txt na raiz do projeto.
2. Benchmark de Avaliação (eval.benchmark)
    - Executei o script de avaliação com as 20 perguntas do cenário acadêmico (eval.benchmark).
    - Observei a ativação automática do mecanismo de fallback léxico (BM25) devido ao timeout na API remota de embeddings, o que garantiu a conclusão total da avaliação.
    - Confirmei a geração dos resultados salvos em eval/benchmark_results.json.
3. **Interface de Linha de Comando (app.cli)
    - Testei de forma interativa a interface CLI (app.cli), validando a recuperação do contexto, a exibição das fontes e o tempo de resposta do pipeline.
    - Validei o funcionamento dos guardrails éticos/de dados sensíveis e encerrei a sessão normalmente.
4. Testes Unitários (unittest)
    - Rodei a bateria de testes automatizados com `python -m unittest discover tests.
    - Resultado: Obtive 100% de aprovação (`Ran 10 tests in 0.042s` -> OK).
5. **Pipeline de RAG (src.pipeline)
    - Executei o fluxo do pipeline (src.pipeline) para validar a ingestão e recuperação de trechos.
    - Verifiquei a correta citação e mapeamento das 6 fontes dos editais e normativos da FAPERJ e CNPq.
6. **Servidor Web (app.server)
    - Iniciei o servidor web do Adaptive RAG (app.server) e validei a disponibilização do serviço local na porta http://localhost:8000.
7. Descoberta e Ingestão Automática de Corpus (src.auto_discover_corpus)
    - Executei o script de descoberta automática python -m src.auto_discover_corpus --target 160 --auto-ingest.
    - Realizei a varredura e ingestão automática de novos documentos do Cenário 3 até atingir a meta estabelecida, atualizando a base local e os vetores de busca.
    8. Notion
    -Fiz anotações no Notion pessoal.

### Próximos Passos (Para o Próximo Encontro)

- Apresentar ao grupo os resultados obtidos no benchmark e a validação do pipeline com o corpus expandido.
- Discutir refinamentos nas métricas de avaliação do RAG e possíveis otimizações no tempo de resposta (latência) da recuperação vetorial.
- Integrar as contribuições individuais dos membros do grupo para a consolidação da entrega final.
- Atualizar a documentação geral do repositório conforme as orientações combinadas com a equipe.

## Encontro 7 - 28/09/2026

### O que fiz hoje:

Realizei a correção de dependências do ambiente e executei com sucesso os testes funcionais na interface web do Streamlit para o Cenário 3 (Inteligência sobre Pesquisa Acadêmica - FAPERJ/CNPq).

### Atividades Realizadas Hoje:

1. Correção de Dependência no Ambiente
    - Identifiquei a falta do pacote torchvision durante a inicialização da aplicação e realizei a instalação no ambiente via terminal (pip install torchvision).
2. Execução da Interface Web (streamlit_app.py)
    - Iniciei o servidor da aplicação gráfica executando o comando no terminal.
    - Validei a inicialização do serviço local na porta http://localhost:8501.
3. Validação Prática de Consultas
    - Acessei a interface no navegador e submeti perguntas de teste sobre os editais e normativos do Cenário 3 (FAPERJ/CNPq).
    - Confirmei o processamento das requisições e a recuperação de respostas em tempo real.

### Próximos Passos (Para o Próximo Encontro):

- Estruturar a migração da base vetorial para um banco de dados SQL (ex: PostgreSQL com a extensão pgvector ou SQLite/MySQL com suporte a embeddings), conforme orientação do professor.
- Apresentar ao grupo o funcionamento da interface gráfica e as consultas validadas no Streamlit.
- Discutir com a equipe possíveis refinamentos no tempo de resposta das consultas e a nova modelagem das tabelas do banco SQL.
- Alinhar a consolidação dos arquivos e a documentação final do projeto para a entrega do grupo.

## Encontro 8 - 30/09/2026

### O que fiz hoje:

Dediquei o dia ao estudo e análise da estrutura do código do projeto, além da atualização das ferramentas de desenvolvimento no ambiente local.

### Atividades Realizadas Hoje

1. Atualização do Ambiente de Desenvolvimento
    - Realizei a atualização do Visual Studio Code para garantir suporte às últimas extensões e ferramentas de assistência de código.
2. Análise e Estudo do Código-Fonte
    - Estudei a estrutura e o fluxo de execução dos scripts do projeto (`src/db_setup.py`, `src/db_sql.py` e `src/db_chroma.py`).
    - Analisei a integração dos módulos de gestão de dados vetoriais e relacionais (SQL) para preparar a transição solicitada pela orientação do curso.

### Próximos Passos (Para o Próximo Encontro)

- Executar os scripts de banco de dados (`db_setup.py` e `db_sql.py`) para validar a criação e inserção na base SQL.
- Dar início à estruturação das tabelas de vetores/embeddings no SQL (ex: PostgreSQL/`pgvector` ou SQLite).
- Apresentar ao grupo as conclusões da análise do código e alinhar as próximas etapas de implementação do banco SQL.

## Encontro 9 - 02/10/2026

### O que fiz hoje:

Realizei o estudo aprofundado dos módulos do projeto, participei de uma breve apresentação com o professor para demonstrar o progresso do Cenário 3 (FAPERJ/CNPq) e iniciei a organização das etapas de apresentação do grupo.

### Atividades Realizadas Hoje:

1. Apresentação de Progresso ao Professor
    - Participei de uma breve apresentação do projeto ao professor, demonstrando o estado atual da solução e o alinhamento dos logs e módulos para a defesa do grupo.
2. Estudo e Mapeamento da Arquitetura
    - Analisei a estrutura de pastas do projeto (`app/`, `src/`, `data/`, `eval/`), compreendendo a responsabilidade de cada módulo no fluxo do RAG.
    - Mapeei o funcionamento das áreas da interface web em Streamlit (`Consulta RAG & Chat`, `Descoberta Automática`, `Gestão do Corpus`, `Observabilidade & Logs` e `Benchmark & Personas`).
3. Organização da Apresentação Final
    - Iniciei com a equipe a definição da divisão dos tópicos e dos módulos/logs individuais que cada integrante irá explicar durante a apresentação final.

### Próximos Passos (Para o Próximo Encontro):

- Definir exatamente qual módulo/log ficarei responsável por apresentar em detalhe.
- Treinar a explicação técnica do fluxo de dados e da execução do módulo selecionado.
- Estruturar a migração da base vetorial para o banco de dados SQL conforme a orientação acadêmica.

## ENCONTRO 10 - 05/10/2026

Definição oficial da divisão da apresentação do grupo e estudo aprofundado do módulo de Descoberta e Atualização de Arquivos sob minha responsabilidade.

## O que fiz hoje:

### Atividades Realizadas Hoje:

1. Alinhamento da Apresentação do Grupo
    - Confirmada a divisão das etapas da apresentação final, onde assumi a responsabilidade técnica do módulo de Descoberta e Atualização de Arquivos.
2. Mapeamento do Módulo de Descoberta e Atualização
    - Estudei o funcionamento do script de varredura automática (`src/auto_discover_corpus.py`) e a sincronização do inventário do corpus (`corpus_manifest.yaml`).
    - Analisei como o sistema identifica novos documentos (PDFs/editais) na pasta de entrada e trata atualizações de arquivos existentes.
    - Preparei o roteiro de apresentação em 1ª pessoa conectando meu módulo com a entrada de dados e a etapa posterior de ingestão no banco SQL.

### Próximos Passos (Para o Próximo Encontro)

- Testar a execução isolada do script de descoberta no terminal para demonstrar ao vivo durante a apresentação.
- Alinhar com a Iris a transição perfeita dos metadados descobertos para o pipeline de ingestão e banco SQL.

### Encontro 11 - 07/10/2026

#### Módulo: Descoberta e Atualização de Arquivos (Corpus & Ingestão)

Responsável: Irene

#### O que fiz Hoje:

- Estudo e Validação do Módulo: Análise detalhada dos scripts do ecossistema de dados (`src/fetch_corpus.py` e `src/auto_discover_corpus.py`), mapeando a lógica de cálculo de hash `SHA-256`, varredura de editais e controle de integridade do corpus.
- Pesquisa e Apoio Teórico: Consultas às IAs (Gemini e ChatGPT) para aprofundar o entendimento sobre seleção determinística, cálculo de integridade por blocos e estrutura de manifesto declarativo (`corpus_manifest.yaml`).
- Documentação: Organização de anotações e pontos de atenção no Notion pessoal para estruturar o roteiro da explicação técnica para a apresentação do projeto.
- Inspeção do Inventário: Verificação do `CORPUS_INVENTORY.md`, confirmando a consolidação das 4 bases com 12 arquivos (20.69 MB) e divergência zero em relação ao volume alvo.

#### Próximos Passos:

- Visão Holística do Desafio: Estudar o fluxo completo do projeto (integração entre RAG, Banco de Dados, Histórico, Observabilidade e Benchmark) para dominar a arquitetura de ponta a ponta e apoiar os colegas de grupo.
- Treino Oral:Ensaiar a apresentação do fluxo de atualização do corpus focando nas rotinas de `fetch`, `update` e geração do inventário.
- Integração: Alinhar a demonstração prática da aba no Streamlit (`auto_discover_corpus.py`) com os módulos de Ingestão e Consulta.

## Encontro 12 - 09/10/2026

 ## O que fiz hoje:

Dia dedicado integralmente ao estudo teórico, revisão de código e alinhamento do desafio para a apresentação.

### Atividades Realizadas Hoje:

1. Estudo Individual do Projeto e do Desafio
    - Revisão aprofundada dos requisitos do Cenário 3 (Pesquisa Acadêmica - FAPERJ/CNPq) e da arquitetura do projeto.
    - Leitura e análise linha a linha do código-fonte do módulo de Descoberta e Atualização de Arquivos(`src/fetch_corpus.py` e `src/auto_discover_corpus.py`).
2. Pesquisa e Documentação
    - Pesquisa de apoio técnico utilizando assistentes de IA (Gemini e ChatGPT) para consolidar conceitos de seleção determinística e integridade via SHA-256.
    - Organização de notas de estudo e roteiro explicativo no Notion pessoal.
3. Visão Geral do Ecossistema do Grupo
    - Estudo das demais etapas do pipeline (Ingestão, SQL/Histórico, Chat RAG, Observabilidade e Benchmark) para entender a integração completa entre os integrantes do grupo.

### Próximos Passos

- Treinar a apresentação oral do fluxo de atualização do corpus e do inventário (`CORPUS_INVENTORY.md`).
- Simular com o grupo a demonstração prática da aba do Streamlit.

# Encontro 13 - 14/10/2026

## O que fiz Hoje:

Dia dedicado integralmente ao estudo teórico, revisão de código e alinhamento do desafio para apresentação.

### Atividades realizadas hoje:
- Não progredi muito hoje, conversei no grupo de whatsapp com o grupo e estudamos como seria a apresentação.
- Decidimos ter uma breve apresentação pro Felipe antes do dia da apresentação geral.

### Próximos passos:
- Combinar com o Felipe uma breve apresentação.
- Estudar mais o código e treinar a apresentação oral da minha parte do desafio.

### Encontro 14 - 16/10/2026

## O que fiz hoje:

- Hoje fiquei estudando a minha parte pra ter mais segurança para apresentação.
- Fiz anotações no Notion pessoal sobre o src/fetch_corpus.py , auto_discover_corpus.py , ingest.py , CORPUS_INVENTORY.md , corpus_manifest.yaml .
- Dei ideia de colocarmos a logo da residência IA & RAG da trilha Ecoa PUC-Rio no nosso fundo de tela do zoom, para dar destaque na apresentação.
- Fiquei na expectativa de uma breve apresentação com o Felipe , mas não aconteceu.

### Próximos passos:

- Treinar a parte oral pra apresentação.
- Revisar alguns pontos para estar pronta para apresentar o desafio.
- Dar explicação ao email do Felipe da Puc-Rio sobre a instabilidade da internet na quinta-feira e sexta-feira durante a aula.

## Encontro 15 - 19/10/2026

### O que fiz hoje:

- Estudei mais o desafio e os códigos para ter uma boa apresentação.
- Tirei dúvidas com o Felipe para saber melhor como devemos apresentar e o que cada um no grupo vai explicar exatamente.
- Atualizei do GitHub coloquei o meu Acompanhamento.md do encontro de hoje.

#### Próximos passos:

- Fazer uma breve apresentação pro Felipe antes do dia da apresentação final, com as dicas que ele deu hoje.
- Fazer uns slides do desafio e treinar oralmente o que irei apresentar pro Felipe, pra Residência e a banca.

## Encontro 16 - 21/10/2026

### O que fiz hoje:

- Fiz o slide que o Felipe pediu
- Estudei sobre a "Descoberta Automática de Arquivos", com auxilio das IAs do chat gpt e gemini
- Fiz a breve apresentação pro Felipe sobre a minha parte do desafio
- Subi o acompanhamento do dia pro GitHub

### Próximos passos:

- Ajustar os slides do grupo, diminuir a quantidade de slides
- Estudar mais oralmente a apresentação para o dia da apresentação real
