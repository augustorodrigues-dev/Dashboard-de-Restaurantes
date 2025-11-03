# Dashboard de Restaurantes

> Um sistema de análise operacional e estratégica para restaurantes, desenvolvido em **Python + Streamlit**.  
> Este projeto foi desenvolvido no processo seletivo da **Nola God Level**.  
> Para mais informações, acesse o repositório oficial do desafio:  
> [Nola God Level - Repositório Base](https://github.com/lucasvieira94/nola-god-level/tree/main)

---

## 🚀 Demonstração Ao Vivo (Deploy)

🎯 **[CLIQUE AQUI PARA ACESSAR O DASHBOARD AO VIVO](https://dashboard-de-restaurantes-4rescxo3zdqshpyfzgdefx.streamlit.app/)**

---

## 📑 Sumário
1. [Visão Geral](#-visão-geral)
2. [Principais Funcionalidades](#-principais-funcionalidades)
3. [Tecnologias Utilizadas](#-tecnologias-utilizadas)
4. [Estrutura do Projeto](#-estrutura-do-projeto)
5. [Como Executar o Projeto Localmente](#-como-executar-o-projeto-localmente)

---

## Visão Geral

O **Dashboard de Restaurantes** é uma aplicação web interativa que permite a gestores de restaurantes acompanhar métricas de desempenho em tempo real.  
A aplicação conecta-se a um banco de dados **PostgreSQL (NeonDB)** e exibe análises de vendas, operações, descontos e comportamento de clientes através de **gráficos dinâmicos e interativos**.

---

## Principais Funcionalidades

- **Visão Geral:** Faturamento total, ticket médio, tempo médio de entrega e preparo.
- **Análise Operacional:** Identifica gargalos de produção com mapas de calor.
- **Análise Detalhada (Explorer):** Permite criar relatórios personalizados por produto, canal, categoria, etc.
- **Análise de Clientes (RFM):** Mede recência, frequência e valor gasto pelos clientes.
- **Análise de Descontos e Taxas:** Mostra impacto financeiro dos descontos aplicados.
- **Exportação CSV:** Baixe relatórios diretamente da interface.

---

## Tecnologias Utilizadas

| Tecnologia | Finalidade |
|-------------|-------------|
| **Python** | Linguagem principal do projeto |
| **Streamlit** | Framework para criação da interface web |
| **Pandas** | Manipulação e análise de dados |
| **Plotly Express** | Criação de gráficos interativos |
| **SQLAlchemy** | Conexão e execução de queries SQL |
| **PostgreSQL (NeonDB)** | Armazenamento dos dados |
| **Git + GitHub** | Controle de versão e hospedagem do código |

---

## Estrutura do Projeto

## Este projeto foi feito no processo seletivo da nola god level, para mais informações acesse o link abaixo:

[Github](https://github.com/lucasvieira94/nola-god-level/tree/main)

## 🚀 Demonstração Ao Vivo (Deploy)

**[CLIQUE AQUI PARA ACESSAR O DASHBOARD AO VIVO](https://dashboard-de-restaurantes-4rescxo3zdqshpyfzgdefx.streamlit.app/)**

---

## Como Executar o Projeto Localmente

Estas instruções são para caso o deploy não esteja funcionando ou tenha a curiosidade de testar a performance localmente, caso o contrário, recomendo que use o link do aplicativo em nuvem acima.

### 1. Clonar o Repositório
```bash
git clone https://github.com/augustorodrigues-dev/Dashboard-de-Restaurantes
cd Dashboard-de-Restaurantes
````

### 2. Criar e Ativar o Ambiente Virtual (.venv)
```bash
# Criar o ambiente
python -m venv .venv

# Ativar no Windows (CMD)
.\.venv\Scripts\activate.bat

# Ativar no macOS/Linux
source .venv/bin/activate
```

### 3. Instalar as Dependências
Este projeto requer um arquivo `requirements.txt` (que você deve gerar)
```bash

### Use este comanndo para instalar as dependencias
pip install -r requirements.txt
```

### 4. Configurar o Banco de Dados (Passo Crucial)
Você precisa de um banco PostgreSQL com os dados de exemplo que estão armazenados em backup.dump.

1.  **Crie um Banco Vazio:** No pgAdmin (ou Neon), crie um novo banco de dados (ex: `banco_avaliacao`).
2.  **Baixe os Dados:** Baixe o arquivo de backup de dados (`.dump`) aqui:
    * **[Drive](https://drive.google.com/drive/folders/1c0q1xaMU4um7eFmzFgxrPwTgWDLoiSE2?usp=drive_link)**
3.  **Restaure os Dados:** Use o `pg_restore` para carregar os dados no seu banco vazio.
    * *Navegue até a pasta `bin` da sua instalação do PostgreSQL (ex: `C:\Program Files\PostgreSQL\17\bin`)*
    * *Execute o comando (substitua usuário, banco e o caminho do arquivo):*
    ```bash
    pg_restore -U postgres -d banco_avaliacao "C:\caminho\para\dados_restaurante.dump"
    ```

### 5. Configurar as Credenciais
1.  Na pasta raiz do projeto (`ProjetoEstagio/`), crie uma pasta `.streamlit`.
2.  Dentro dela, crie um arquivo `secrets.toml`.
3.  Adicione as credenciais do **seu** banco `banco_avaliacao`.

**Arquivo: `.streamlit/secrets.toml`**
```toml
[connections]
# Lembre-se de usar 'postgresql://' (com 'sql' no final)
neon_db = "postgresql://postgres:sua_senha_local@localhost:5432/banco_avaliacao"
```

### 6. Executar o Dashboard
Com o ambiente virtual (`.venv`) ativo, execute:
```bash
streamlit run Pagina_Principal.py
```
O aplicativo abrirá automaticamente no seu navegador.
