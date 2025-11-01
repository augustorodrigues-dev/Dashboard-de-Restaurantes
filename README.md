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
