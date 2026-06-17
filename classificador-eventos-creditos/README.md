# Classificador de Eventos de Crédito para CRA e CRI

## Visão Geral

O Classificador de Eventos de Crédito é uma ferramenta desenvolvida para identificar e categorizar automaticamente eventos relevantes em operações de securitização de recebíveis no mercado brasileiro, abrangendo:

* CRA (Certificados de Recebíveis do Agronegócio)
* CRI (Certificados de Recebíveis Imobiliários)

A solução classifica fatos relevantes em três categorias de risco:

| Classificação | Peso |
| ------------- | ---- |
| Positivo      | +1   |
| Neutro        | 0    |
| Negativo      | -1   |

Os pesos atribuídos permitem a construção de indicadores agregados de risco para acompanhamento contínuo das operações.

---

## Objetivo

O projeto foi desenvolvido como parte de um case técnico para empresa C2P, para vaga de Estágio em Crédito.

Entre os principais objetivos estão:

* Monitorar continuamente carteiras de CRA e CRI.
* Identificar eventos de deterioração de crédito.
* Gerar alertas para eventos críticos, como inadimplência, recuperação judicial e rebaixamentos de rating.
* Calcular indicadores agregados de risco a partir da frequência dos eventos observados.
* Reduzir o esforço manual na análise de documentos e comunicados ao mercado.

A metodologia de classificação foi inspirada nos critérios utilizados por agências de rating como S&P Global Ratings, Moody’s Ratings e Fitch Ratings.

---

## Tecnologias Utilizadas

### Linguagem Principal

| Tecnologia | Versão |
| ---------- | ------ |
| Python     | 3.11   |

### Bibliotecas

| Biblioteca | Finalidade                               |
| ---------- | ---------------------------------------- |
| pandas     | Manipulação e análise de dados tabulares |

### Bibliotecas Nativas

| Biblioteca | Finalidade                                    |
| ---------- | --------------------------------------------- |
| logging    | Registro de execução e depuração              |
| re         | Processamento de texto e expressões regulares |
| pathlib    | Manipulação de caminhos e arquivos            |

### Ferramentas de Desenvolvimento

* Git
* GitHub
* Visual Studio Code (opcional)

---

## Estrutura do Projeto

```text
classificador-eventos-credito/
│
├── main.py
├── EventosCredito.csv
├── Fatos_Relevantes.csv
├── README.md
├── .gitignore
│
└── outputs/
    ├── EventosCredito_Classificados.csv
    ├── FatosRelevantes_Classificados.csv
    ├── Consolidado.csv
    ├── TopEventos.csv
    └── Metricas.csv
```

### Arquivos de Entrada

| Arquivo              | Descrição                                                    |
| -------------------- | ------------------------------------------------------------ |
| EventosCredito.csv   | Base mestre contendo os eventos e respectivas classificações |
| Fatos_Relevantes.csv | Fatos relevantes a serem analisados                          |

### Arquivos Gerados

| Arquivo                           | Descrição                             |
| --------------------------------- | ------------------------------------- |
| EventosCredito_Classificados.csv  | Eventos identificados e classificados |
| FatosRelevantes_Classificados.csv | Resultado detalhado da classificação  |
| Consolidado.csv                   | Base consolidada de resultados        |
| TopEventos.csv                    | Ranking dos eventos identificados     |
| Metricas.csv                      | Métricas consolidadas da execução     |

--- 

## Execução

Execute o classificador com:

```bash
python3 main.py
```

Ao final da execução, a pasta `outputs/` será criada automaticamente contendo todos os arquivos de resultado.

---

## Metodologia de Classificação

O mecanismo de classificação é baseado em regras determinísticas e utiliza um conjunto de palavras-chave e sinônimos associados a eventos de crédito previamente definidos.

O fluxo de processamento é composto pelas seguintes etapas:

### 1. Normalização do Texto

O conteúdo dos fatos relevantes passa por um processo de padronização:

* Conversão para letras minúsculas.
* Remoção de acentos.
* Normalização de termos equivalentes.
* Redução de variações linguísticas frequentes.

Exemplos:

| Termo Original       | Forma Normalizada    |
| -------------------- | -------------------- |
| fluxo de pagamentos  | fluxo pagamento      |
| recuperação judicial | recuperacao judicial |

### 2. Aplicação das Regras

Cada regra contém:

* Palavras obrigatórias.
* Palavras de exclusão.
* Evento associado.

A primeira regra que satisfaz todos os critérios é utilizada para classificação.

Exemplo:

```python
(
    ["aditamento", "repactuacao"],
    ["sem alteracoes", "correcao", "erro material", "sem modificacoes"],
    "Aditamento com repactuação do fluxo de pagamento"
)
```

### 3. Classificação

Após a identificação do evento, o sistema atribui:

* Categoria (Positivo, Neutro ou Negativo)
* Peso (+1, 0 ou -1)

### 4. Consolidação

São geradas métricas consolidadas contendo:

* Frequência dos eventos.
* Distribuição das classificações.
* Ranking dos eventos mais recorrentes.
* Score agregado de risco.

---

## Resultados

### Métricas Gerais

| Indicador                 | Valor       |
| ------------------------- | ----------- |
| Total de fatos analisados | 465         |
| Fatos identificados       | 211 (45,4%) |
| Fatos não identificados   | 254 (54,6%) |
| Eventos positivos         | 13 (2,8%)   |
| Eventos neutros           | 337 (72,5%) |
| Eventos negativos         | 115 (24,7%) |
| Score agregado            | -102        |

### Principais Eventos Identificados

| Evento                                                         | Classificação | Ocorrências |
| -------------------------------------------------------------- | ------------- | ----------- |
| Manutenção de Rating de Agência de Risco                       | Neutro        | 52          |
| Pedido de Recuperação Judicial ou Extrajudicial                | Negativo      | 33          |
| Aprovação das Demonstrações Financeiras do Patrimônio Separado | Neutro        | 30          |
| Aditamento com Repactuação do Fluxo de Pagamento               | Negativo      | 26          |
| Waiver de Não Pagamento de Juros ou Amortização                | Negativo      | 18          |
| Waiver para Não Declarar Vencimento Antecipado                 | Negativo      | 14          |
| Resgate ou Recompra Antecipado Facultativo                     | Positivo      | 12          |

### Principais Eventos Negativos

| Evento                                           | Ocorrências |
| ------------------------------------------------ | ----------- |
| Pedido de Recuperação Judicial ou Extrajudicial  | 33          |
| Aditamento com Repactuação do Fluxo de Pagamento | 26          |
| Waiver de Não Pagamento de Juros ou Amortização  | 18          |
| Waiver para Não Declarar Vencimento Antecipado   | 14          |
| Carência de Pagamento de Juros ou Amortização    | 8           |

### Principais Eventos Positivos

| Evento                                       | Ocorrências |
| -------------------------------------------- | ----------- |
| Resgate ou Recompra Antecipado Facultativo   | 12          |
| Recomposição de Fundo de Reserva ou Liquidez | 1           |

---

## Análise dos Resultados

### Distribuição dos Eventos

A predominância de eventos classificados como neutros reflete a natureza operacional e administrativa da maior parte dos comunicados divulgados pelas operações de securitização.

Os eventos negativos representam aproximadamente um quarto dos fatos classificados, indicando presença relevante de situações de estresse de crédito.

Eventos positivos foram pouco frequentes, demonstrando que medidas efetivamente favoráveis ao risco de crédito ocorreram em menor proporção durante o período analisado.

### Score Agregado

O score agregado de **-102** indica predominância de eventos com impacto negativo sobre a qualidade de crédito das operações monitoradas.

A diferença entre a quantidade de eventos negativos e positivos evidencia um ambiente de maior deterioração do risco observado na amostra analisada.

### Principais Vetores de Risco

Os eventos mais associados à deterioração de crédito foram:

1. Pedidos de recuperação judicial ou extrajudicial.
2. Repactuações de fluxo de pagamento.
3. Waivers relacionados ao não pagamento de obrigações financeiras.

Esses eventos são tradicionalmente considerados indicadores relevantes de fragilidade financeira em operações estruturadas.

### Cobertura do Modelo

A taxa de identificação de 45,4% é considerada satisfatória para um modelo baseado exclusivamente em regras.

Os fatos classificados como não identificados são compostos principalmente por:

* Comunicados administrativos.
* Atualizações operacionais sem impacto de crédito.
* Eventos não contemplados no conjunto atual de regras.

---

## Evolução do Projeto

| Versão | Eventos Identificados | Cobertura | Score |
| ------ | --------------------- | --------- | ----- |
| 1.0    | 134                   | 28,8%     | -78   |
| 2.0    | 211                   | 45,4%     | -102  |

A versão 2.0 ampliou significativamente a cobertura do classificador por meio da inclusão de novos sinônimos e refinamento das regras de detecção.

---

## Possíveis Evoluções

* Ampliação do catálogo de eventos de crédito.
* Integração com fontes externas de dados.
* Consumo automático de informações da CVM e da B3.
* Desenvolvimento de dashboards interativos.
* Criação de séries temporais de risco.
* Aplicação de modelos de Machine Learning para classificação supervisionada.
* Integração com sistemas de monitoramento e geração de alertas.

---

## Conclusão

O Classificador de Eventos de Crédito fornece uma abordagem simples, transparente e eficiente para monitoramento de risco em operações de CRA e CRI.

Os resultados obtidos demonstram capacidade de identificar eventos relevantes para análise de crédito, permitindo acompanhar sinais de deterioração financeira e produzir indicadores consolidados para apoio à tomada de decisão.

A arquitetura baseada em regras facilita a manutenção, auditoria e expansão do modelo, tornando a solução adequada para aplicações de monitoramento contínuo no mercado de securitização.

---

## Contribuições

Contribuições são bem-vindas.

Para sugerir melhorias, reportar problemas ou propor novas funcionalidades, utilize as issues e pull requests do repositório.

---

## Autora

**Raissa Cavalcanti**

Junho de 2026
