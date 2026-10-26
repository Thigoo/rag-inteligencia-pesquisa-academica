# Encontro 1 14/09/2026
    
# Resumo do dia em conjunto: o que a equipe entregou, o que travou, qual o próximo passo.

* Foi feita a criação da organização no GitHub de Projeto de Inteligência sobre Pesquisa Acadêmica.
* Criação do Grupo do Whatsapp.
* Separação das funções ainda não foi realizada. 

# Encontro 2 16/09/2026

* Foi criado o arquivo `requirements.txt`, reunindo e organizando as dependências necessárias para o projeto.
* Foram adicionados os arquivos `fetch_corpus`, `obs` e `schema`, estruturando os componentes iniciais do projeto.
* No início do desenvolvimento, foi criado um repositório para centralizar o projeto e disponibilizá-lo aos integrantes da equipe. Posteriormente, optou-se pela criação de uma organização no GitHub para facilitar o gerenciamento e a colaboração entre os membros.
* Durante o dia, foi identificado um problema de acesso ao repositório, que apresentava a mensagem “Page Not Found” ao ser acessado.

# Encontro 4 21/09/26

* Fiz um levantamento de documentos relacionados à Inteligência Artificial e à pesquisa acadêmica, buscando materiais que pudessem contribuir para o enriquecimento da base utilizada no RAG.
* Após a pesquisa, selecionei os conteúdos pertinentes e realizei a organização dos arquivos na pasta `data/raw/v1/editais_normativo`, deixando os documentos estruturados para dar continuidade ao processo de alimentação da base.

# Encontro 5 23/09/26

* Foram realizadas algumas alterações e implementações no código, além de ajustes necessários no projeto.
* Realizei os testes dos arquivos e funcionalidades desenvolvidos.
* Instalei e configurei as dependências necessárias para executar o projeto corretamente no meu ambiente.
* Após os ajustes, refiz os testes e as funcionalidades apresentaram o comportamento esperado.
* Também identifiquei que a execução dos testes está ocorrendo de forma mais lenta, possivelmente devido à utilização simultânea do ambiente/vídeo da PUC-Rio por várias pessoas, o que pode estar gerando maior demanda de recursos e impactando o tempo de execução.

# Encontro 6 25/09/26

* Foram realizados testes nos componentes do projeto para validar o funcionamento e possibilitar o avanço para as próximas etapas.
* Durante os testes, ocorreram alguns casos de Request Timeout, principalmente durante a etapa de busca e avaliação das questões, devido à demora na resposta do servidor LLM remoto.
* Eu e Ellen também trabalhamos na criação de um automatizador para busca de arquivos, com o objetivo de facilitar a coleta dos materiais necessários.
* Após os testes, optamos por utilizar o automatizador desenvolvido pelo Marcos, que apresentou um funcionamento satisfatório e atendeu bem à necessidade do projeto.
* Com isso, foi possível validar as soluções e definir os componentes que serão utilizados para dar continuidade ao desenvolvimento.

# Encontro 7 28/09/26

* Instalei e corrigi as dependências necessárias para executar o Streamlit no ambiente.
* Executei a aplicação streamlit_app.py e validei o funcionamento da interface web localmente.
* Realizei testes funcionais na interface, verificando o comportamento da aplicação e o processamento das consultas.
* Testei a geração e recuperação das respostas, avaliando se o RAG estava retornando as informações de forma adequada.
* Pesquisei sobre bancos de dados vetoriais e sua utilização em aplicações RAG, buscando entender melhor o armazenamento, geração de embeddings e recuperação de informações por similaridade.
* A partir da pesquisa e das discussões realizadas com a equipe, entramos em consenso pela utilização do ChromaDB como banco de dados vetorial do projeto.

# Encontro 8 30/09/26

* Hoje, o foco foi **entender melhor a estrutura do projeto**, observando como os arquivos e módulos estão organizados e como acontece o fluxo de execução.
* Também estudei a integração dos bancos **SQL e ChromaDB**, buscando compreender melhor como eles funcionam dentro do projeto e como se relacionam com as demais partes do sistema.
* Aproveitei o dia para **explorar melhor o código-fonte**, entendendo a organização dos arquivos, a função de cada parte e como as informações percorrem o sistema.
* Além disso, continuei **me familiarizando com o projeto e com as tecnologias utilizadas**, buscando entender melhor seu funcionamento e as próximas etapas de desenvolvimento.
* Por fim, instalei as dependências necessárias para o funcionamento do ChromaDB, deixando o ambiente preparado para a utilização e realização dos próximos testes.

# Encontro 9 02/10/26

* Estudei novamente as implementações para entender melhor, passo a passo, o funcionamento do código.
* Participei de uma pequena apresentação do projeto com o Felipe, onde foram levantadas possíveis melhorias e ajustes.
* Testei novamente as aplicações para validar o funcionamento.

# Encontro 10 05/10/26

* Testei a funcionalidade para entender melhor seu funcionamento.
* Instalei as dependências necessárias para rodar o projeto.
* Estudei o código para entender melhor cada parte e como as funcionalidades estão sendo implementadas.
* Tivemos um alinhamento sobre a apresentação do projeto, organizando os pontos que serão apresentados e o que precisa ser ajustado.

# Encontro 11 07/10/26

* Dei continuidade aos testes da aplicação, validando o funcionamento das funcionalidades e observando possíveis comportamentos.
* Aprofundei meus estudos sobre a funcionalidade de histórico de pesquisa, buscando compreender melhor seu fluxo e comportamento dentro da aplicação.
* Realizei uma análise mais detalhada do código relacionado à funcionalidade, destrinchando sua estrutura, lógica e integração com as demais partes do sistema.

# Encontro 12 09/10/26

* Continuei os estudos voltados ao código do projeto, buscando compreender melhor o funcionamento de cada parte da aplicação.
* Realizei novos testes para verificar o funcionamento das funcionalidades implementadas.
* Dei continuidade aos estudos relacionados à funcionalidade pela qual fiquei responsável, buscando entender melhor sua implementação e como ela se integra ao restante do sistema.

# Encontro 13 14/10/26

* Dediquei o dia ao estudo das funcionalidades do sistema, buscando compreender melhor seu funcionamento e comportamento.
* Explorei a área de histórico, pela qual fiquei responsável, realizando testes para verificar suas funcionalidades e entender melhor como o código está estruturado.
* Continuei aprofundando meus conhecimentos sobre o sistema, identificando pontos importantes para a continuidade dos testes e dos estudos.

# Encontro 14 16/10/26

* Analisei com mais atenção os recursos disponíveis no sistema, buscando compreender melhor suas aplicações.
* Realizei testes na área do histórico, observando seu comportamento e examinando aspectos do código relacionados a essa funcionalidade.
* Comecei a estruturar o roteiro da apresentação, selecionando os pontos mais relevantes para explicar a minha parte no projeto.
* Organizei os conhecimentos adquiridos durante os estudos, destacando informações importantes para a apresentação e para a continuidade do desenvolvimento.

# Encontro 15 16/10/26

* Continue organizando o meu roteiro de apresentação, para deixar tudo alinhado. 

# Encontro 16 21/10/26

* Eu e Ellen ajustamos a estrutura e a organização dos slides.
* Adicionei minha parte do conteúdo à apresentação.
* Organizei as informações e melhorei o visual dos slides para deixar o material mais claro e agradável.
* Participei da apresentação ao professor para receber feedbacks.
* Identifiquei possíveis melhorias a partir das sugestões recebidas.
