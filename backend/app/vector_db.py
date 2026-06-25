import os
import json
import math
import sqlite3
import time # Adicionado para o controle de limite da API
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List, Dict, Any
from pathlib import Path

# Carregar variáveis de ambiente
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.env"))

# Obter configurações das variáveis de ambiente
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "manual_uerjiano.db"
LEGACY_DB_PATHS = [
    PROJECT_ROOT / "backend" / "data" / "manual_uerjiano.db",
    Path(PROJECT_ROOT.anchor) / "data" / "manual_uerjiano.db",
]


def resolve_db_path() -> Path:
    """Resolve o caminho do SQLite de forma estável a partir da raiz do projeto."""
    env_path = os.environ.get("SQLITE_DB_PATH")
    if env_path:
        path = Path(env_path).expanduser()
        if path.is_absolute():
            return path
    return DEFAULT_DB_PATH


SQLITE_DB_PATH = resolve_db_path()

# Configurar API do Gemini para embeddings
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_db_connection():
    # Garantir que a pasta de dados existe
    os.makedirs(SQLITE_DB_PATH.parent, exist_ok=True)
    # CORREÇÃO: Adicionado timeout e check_same_thread para evitar "database is locked"
    conn = sqlite3.connect(str(SQLITE_DB_PATH), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Garantir que a tabela existe
    conn.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        doc_id INTEGER,
        titulo TEXT,
        tipo TEXT,
        texto TEXT,
        chunk_idx INTEGER,
        embedding TEXT
    )
    """)
    conn.commit()
    migrate_legacy_vector_db()
    return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,))
    return cursor.fetchone() is not None


def migrate_legacy_vector_db():
    """Mescla os chunks vetoriais do banco legado em backend/data para o banco canônico."""
    current_conn = sqlite3.connect(str(SQLITE_DB_PATH), timeout=10.0, check_same_thread=False)
    current_conn.row_factory = sqlite3.Row
    current_conn.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        doc_id INTEGER,
        titulo TEXT,
        tipo TEXT,
        texto TEXT,
        chunk_idx INTEGER,
        embedding TEXT
    )
    """)
    current_conn.commit()

    current_cursor = current_conn.cursor()
    for legacy_path in LEGACY_DB_PATHS:
        if legacy_path.resolve() == SQLITE_DB_PATH.resolve() or not legacy_path.exists():
            continue

        legacy_conn = sqlite3.connect(str(legacy_path), timeout=10.0, check_same_thread=False)
        legacy_conn.row_factory = sqlite3.Row
        legacy_conn.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            doc_id INTEGER,
            titulo TEXT,
            tipo TEXT,
            texto TEXT,
            chunk_idx INTEGER,
            embedding TEXT
        )
        """)
        legacy_conn.commit()

        if table_exists(legacy_conn, "document_chunks"):
            legacy_cursor = legacy_conn.cursor()
            legacy_cursor.execute("SELECT id, doc_id, titulo, tipo, texto, chunk_idx, embedding FROM document_chunks")
            for row in legacy_cursor.fetchall():
                current_cursor.execute(
                    """
                    INSERT OR IGNORE INTO document_chunks (id, doc_id, titulo, tipo, texto, chunk_idx, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (row["id"], row["doc_id"], row["titulo"], row["tipo"], row["texto"], row["chunk_idx"], row["embedding"]),
                )

        legacy_conn.close()

    current_conn.commit()
    current_conn.close()

def get_embedding(text: str, task_type: str = "retrieval_document") -> List[float]:
    """Gera o embedding do texto usando a API do Gemini."""
    # Obter a chave dinamicamente para garantir que lê o env atualizado
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("AVISO: GEMINI_API_KEY não definida. Retornando embedding vazio para testes.")
        return [0.0] * 768
        
    try:
        # Configurar se não estiver configurado ou se mudou
        genai.configure(api_key=api_key)
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type=task_type
        )
        return response['embedding']
    except Exception as e:
        print(f"Erro ao gerar embedding: {e}")
        return [0.0] * 768

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Divide o texto em blocos (chunks) mantendo integridade dos parágrafos quando possível."""
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        if len(current_chunk) + len(paragraph) < chunk_size:
            current_chunk += "\n" + paragraph if current_chunk else paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            # Se um único parágrafo for maior que o chunk_size, divide por palavras
            if len(paragraph) > chunk_size:
                words = paragraph.split(" ")
                temp = ""
                for w in words:
                    if len(temp) + len(w) < chunk_size:
                        temp += " " + w if temp else w
                    else:
                        chunks.append(temp)
                        temp = w
                current_chunk = temp
            else:
                current_chunk = paragraph
                
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def add_document_to_vector_db(doc_id: int, titulo: str, tipo: str, texto: str):
    """Divide o documento em chunks, gera embeddings e insere no SQLite."""
    chunks = chunk_text(texto)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Remover chunks antigos do mesmo documento
    cursor.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
    
    for idx, chunk in enumerate(chunks):
        chunk_id = f"doc_{doc_id}_chunk_{idx}"
        
        # CORREÇÃO: Pausa de 1 segundo para não estourar a cota gratuita do Gemini (100 req/min)
        time.sleep(1) 
        
        emb = get_embedding(chunk, task_type="retrieval_document")
        
        cursor.execute("""
        INSERT INTO document_chunks (id, doc_id, titulo, tipo, texto, chunk_idx, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (chunk_id, doc_id, titulo, tipo, chunk, idx, json.dumps(emb)))
        
    conn.commit()
    conn.close()
    print(f"Indexados {len(chunks)} chunks para o documento '{titulo}' no SQLite.")

def dot_product(v1: List[float], v2: List[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))

def norm(v: List[float]) -> float:
    return math.sqrt(sum(a * a for a in v))

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    d = dot_product(v1, v2)
    n1 = norm(v1)
    n2 = norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return d / (n1 * n2)

def query_vector_db(query_text: str, n_results: int = 4) -> List[Dict[str, Any]]:
    """Busca os trechos mais relevantes no SQLite usando busca vetorial local."""
    query_emb = get_embedding(query_text, task_type="retrieval_query")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id, titulo, tipo, texto, chunk_idx, embedding FROM document_chunks")
    rows = cursor.fetchall()
    conn.close()
    
    hits = []
    for row in rows:
        emb_list = json.loads(row["embedding"])
        sim = cosine_similarity(query_emb, emb_list)
        hits.append({
            "texto": row["texto"],
            "metadata": {
                "doc_id": row["doc_id"],
                "titulo": row["titulo"],
                "tipo": row["tipo"],
                "chunk_idx": row["chunk_idx"]
            },
            "similarity": sim
        })
        
    # Ordenar por similaridade de cosseno em ordem decrescente
    hits.sort(key=lambda x: x["similarity"], reverse=True)
    return hits[:n_results]

def get_or_create_collection():
    """Dummy class para compatibilidade de API se necessário."""
    class DummyCollection:
        @property
        def name(self):
            return "manual_uerjiano"
        def count(self):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            c = cursor.fetchone()[0]
            conn.close()
            return c
    return DummyCollection()