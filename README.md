# Manual do Uerjiano 🎓

> Assistente Virtual Inteligente para Direitos, Leis e Normas Acadêmicas da UERJ (Universidade do Estado do Rio de Janeiro).

O **Manual do Uerjiano** é um sistema de chatbot inteligente que utiliza a técnica de **RAG (Retrieval-Augmented Generation)** integrada com modelos de linguagem do **Google Gemini** para auxiliar estudantes a navegarem pelas normas de avaliação, trancamentos de matrícula, jubilamento, assistência estudantil (bolsas da PR4), restaurante universitário (bandejão) e outros regulamentos internos da UERJ.

---

## 🚀 Funcionalidades Principais

*   **Chatbot Inteligente (RAG):** Responde a dúvidas em linguagem natural e fluida baseando-se estritamente na base de conhecimento oficial do projeto.
*   **Resolução de Conflitos de Leis:** O sistema identifica se um documento oficial foi revogado ou alterado (ex: o AEDA 045/2024 revogando/atualizando regras do AEDA 023/2021) e alerta explicitamente o estudante sobre a regra atual vigente.
*   **Fontes e Citações Claras:** Cada resposta acompanha links e títulos das resoluções, portarias ou AEDAs oficiais que justificam aquela informação.
*   **Web Crawlers Embutidos:** Coleta e indexa de forma automatizada informações de portais da UERJ (Rede Sirius, Carta de Serviços e Manuais do DEP).
*   **Busca Vetorial Local (SQLite):** Utiliza embeddings gerados pelo modelo `models/gemini-embedding-001` e calcula similaridade de cosseno em memória diretamente no banco SQLite (`document_chunks`), sem dependências externas complexas de infraestrutura.
*   **Painel de Administração e Avaliação (Q&A Benchmark):** 
    *   Força re-indexação/raspagem de dados.
    *   Executa testes automáticos de qualidade das respostas contra uma base de perguntas e respostas padrão, apresentando relatórios de acurácia da PoC.
*   **Interface Fluida e Moderna:** Desenvolvida em HTML5/CSS3 moderno com modo escuro/claro e controle de histórico de sessões.

---

## 📁 Estrutura do Repositório

```text
manual-uerjiano/
├── backend/                  # Código do servidor e lógica de IA
│   ├── app/
│   │   ├── crawler.py        # Raspagem de portais da UERJ e sementes (seed data)
│   │   ├── database.py       # Gerenciamento do banco relacional SQLite e histórico
│   │   ├── main.py           # API FastAPI e montagem do Frontend estático
│   │   ├── rag.py            # Fluxo principal do RAG e integração com Gemini
│   │   └── vector_db.py      # Divisão em chunks, embeddings e busca de similaridade
│   ├── .env.example          # Exemplo de variáveis de ambiente
│   └── requirements.txt      # Dependências Python do backend
├── data/                     # Pasta local para o banco de dados (ignorada no Git)
│   └── manual_uerjiano.db    # Banco SQLite contendo docs, chunks, histórico e Q&A
├── frontend/                 # Interface Web
│   ├── css/
│   │   └── style.css         # Estilização completa (responsiva, tema escuro)
│   ├── js/
│   │   └── app.js            # Lógica de interação com a API, histórico e painel
│   └── index.html            # Estrutura principal da página de chat
├── .gitignore                # Arquivos ignorados pelo Git (.env, data/, .venv/)
└── README.md                 # Documentação do projeto
```

---

## 🛠️ Requisitos e Instalação

### Pré-requisitos
*   **Python 3.10** ou superior instalado.
*   Uma chave de API da Google Gemini (pode ser obtida gratuitamente no [Google AI Studio](https://aistudio.google.com/)).

### Passo 1: Clone do Projeto
Caso já esteja com o projeto no seu computador, pule este passo. Caso contrário, clone o repositório utilizando:
```bash
git clone https://github.com/seu-usuario/manual-uerjiano.git
cd manual-uerjiano
```

### Passo 2: Configuração do Ambiente Virtual (Virtualenv)
Recomenda-se criar um ambiente virtual isolado para as dependências em Python.

**No Windows (PowerShell/CMD):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**No macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Passo 3: Instalação das Dependências
Com o ambiente virtual ativo, instale os pacotes necessários especificados no arquivo do backend:
```bash
pip install -r backend/requirements.txt
```

### Passo 4: Configuração das Variáveis de Ambiente
1. Navegue até a pasta `backend/`.
2. Duplique o arquivo `.env.example` e renomeie-o para `.env`.
3. Abra o arquivo `.env` e configure sua chave da API do Gemini obtida no Google AI Studio:

```ini
# Chave de API do Gemini
GEMINI_API_KEY=AIzaSy...seu_token_aqui

# Configurações de Caminho do SQLite
SQLITE_DB_PATH=../data/manual_uerjiano.db
VECTOR_DB_DIR=../data/chroma_db

# Configurações do Servidor
PORT=8000
HOST=127.0.0.1
```

---

## 🏃 Como Executar o Projeto

1. Com o terminal aberto na pasta do projeto e o `.venv` ativo, navegue até a pasta `backend`:
   ```bash
   cd backend
   ```
2. Inicie o servidor local através do Uvicorn:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
3. O servidor iniciará. Ao detectar que o banco de dados está vazio na primeira execução, o sistema disparará automaticamente o processo de **crawler e ingestão inicial** em segundo plano para semear as informações.
4. Abra o seu navegador e acesse a aplicação em:
   **[http://localhost:8000](http://localhost:8000)**

---

## 📤 Etapas para Fazer o Upload para o GitHub

Para publicar e compartilhar este projeto no seu perfil do GitHub, siga o passo a passo abaixo:

### 1. Criar um Repositório Vazio no GitHub
1. Acesse o [GitHub](https://github.com) e faça login na sua conta.
2. Clique no botão **"New"** (Novo) na aba de repositórios ou acesse [github.com/new](https://github.com/new).
3. Defina um nome para o repositório (ex: `manual-uerjiano`).
4. Selecione se deseja que ele seja **Público** ou **Privado**.
5. **IMPORTANTE:** Não marque as opções de adicionar `README`, `.gitignore` ou `License`, pois o projeto local já possui esses arquivos configurados de forma personalizada.
6. Clique em **"Create repository"** (Criar repositório).

### 2. Inicializar o Git Localmente e Fazer o Push
No seu terminal local (no diretório raiz do projeto `manual-uerjiano`), execute a sequência de comandos a seguir:

```bash
# 1. Inicialize o repositório local do Git
git init

# 2. Adicione todos os arquivos ao estágio de preparação (staging area)
git add .

# 3. Crie o primeiro commit com as alterações atuais
git commit -m "feat: estrutura inicial do Manual do Uerjiano RAG"

# 4. Defina o nome da branch padrão como 'main'
git branch -M main

# 5. Associe o seu repositório local ao repositório remoto criado no GitHub
# (Substitua a URL abaixo pela URL fornecida na página do repositório recém-criado)
git remote add origin https://github.com/seu-usuario/manual-uerjiano.git

# 6. Envie o código do seu repositório local para o GitHub
git push -u origin main
```

> [!WARNING]
> **Segurança de Chaves e Dados:** 
> O arquivo `.gitignore` do projeto já está pré-configurado para ignorar o arquivo de credenciais locais `backend/.env` e o banco de dados gerado em `data/manual_uerjiano.db`. **Nunca** comite chaves de API reais da Google no histórico do Git. Se por acaso alterar as configurações locais do git, verifique com `git status` para garantir que o `.env` e a pasta `data/` não estão listados para upload.
