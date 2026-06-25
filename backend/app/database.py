import sqlite3
import os
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

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

# Garantir que a pasta de dados existe
os.makedirs(SQLITE_DB_PATH.parent, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(str(SQLITE_DB_PATH), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,))
    return cursor.fetchone() is not None


def migrate_legacy_database():
    """Mescla dados do banco legado em backend/data para o banco canônico na raiz."""
    current_conn = get_db_connection()
    current_cursor = current_conn.cursor()

    try:
        for legacy_path in LEGACY_DB_PATHS:
            if legacy_path.resolve() == SQLITE_DB_PATH.resolve() or not legacy_path.exists():
                continue

            legacy_conn = sqlite3.connect(str(legacy_path), timeout=10.0, check_same_thread=False)
            legacy_conn.row_factory = sqlite3.Row
            legacy_cursor = legacy_conn.cursor()

            try:
                if table_exists(legacy_conn, "documentos"):
                    legacy_cursor.execute("SELECT id, titulo, tipo, numero, ano, url, texto, revogado, revogado_por, data_cadastro FROM documentos")
                    for row in legacy_cursor.fetchall():
                        current_cursor.execute("SELECT id FROM documentos WHERE titulo = ? OR (url = ? AND url IS NOT NULL)", (row["titulo"], row["url"]))
                        existing = current_cursor.fetchone()
                        if existing:
                            current_cursor.execute(
                                """
                                UPDATE documentos
                                SET tipo = ?, numero = ?, ano = ?, url = ?, texto = ?, revogado = ?, revogado_por = ?
                                WHERE id = ?
                                """,
                                (row["tipo"], row["numero"], row["ano"], row["url"], row["texto"], row["revogado"], row["revogado_por"], existing[0]),
                            )
                        else:
                            current_cursor.execute(
                                """
                                INSERT INTO documentos (id, titulo, tipo, numero, ano, url, texto, revogado, revogado_por, data_cadastro)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (row["id"], row["titulo"], row["tipo"], row["numero"], row["ano"], row["url"], row["texto"], row["revogado"], row["revogado_por"], row["data_cadastro"]),
                            )

                if table_exists(legacy_conn, "mensagens"):
                    legacy_cursor.execute("SELECT id, sessao_id, papel, conteudo, timestamp FROM mensagens")
                    for row in legacy_cursor.fetchall():
                        current_cursor.execute(
                            """
                            SELECT 1 FROM mensagens
                            WHERE sessao_id = ? AND papel = ? AND conteudo = ? AND timestamp = ?
                            """,
                            (row["sessao_id"], row["papel"], row["conteudo"], row["timestamp"]),
                        )
                        if not current_cursor.fetchone():
                            current_cursor.execute(
                                """
                                INSERT INTO mensagens (sessao_id, papel, conteudo, timestamp)
                                VALUES (?, ?, ?, ?)
                                """,
                                (row["sessao_id"], row["papel"], row["conteudo"], row["timestamp"]),
                            )

                if table_exists(legacy_conn, "avaliacao_qa"):
                    legacy_cursor.execute("SELECT id, pergunta, resposta_esperada, categoria FROM avaliacao_qa")
                    for row in legacy_cursor.fetchall():
                        current_cursor.execute(
                            """
                            SELECT 1 FROM avaliacao_qa
                            WHERE pergunta = ? AND resposta_esperada = ? AND COALESCE(categoria, '') = COALESCE(?, '')
                            """,
                            (row["pergunta"], row["resposta_esperada"], row["categoria"]),
                        )
                        if not current_cursor.fetchone():
                            current_cursor.execute(
                                """
                                INSERT INTO avaliacao_qa (id, pergunta, resposta_esperada, categoria)
                                VALUES (?, ?, ?, ?)
                                """,
                                (row["id"], row["pergunta"], row["resposta_esperada"], row["categoria"]),
                            )
            finally:
                legacy_conn.close()

        current_conn.commit()
    finally:
        current_conn.close()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de Documentos (Legislação, AEDAs, etc.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL, -- AEDA, Regulamento, Carta de Servico, Resolucao, etc.
        numero TEXT,
        ano INTEGER,
        url TEXT,
        texto TEXT NOT NULL,
        revogado INTEGER DEFAULT 0, -- 0 = Vigente, 1 = Revogado
        revogado_por TEXT,          -- ID ou título do documento que o revogou
        data_cadastro TEXT NOT NULL
    )
    """)
    
    # Tabela de Histórico de Conversas (Mensagens do Chatbot)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sessao_id TEXT NOT NULL,
        papel TEXT NOT NULL, -- 'user' ou 'model'
        conteudo TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)
    
    # Tabela de Avaliação Q&A (Base de Teste)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacao_qa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pergunta TEXT NOT NULL,
        resposta_esperada TEXT NOT NULL,
        categoria TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    migrate_legacy_database()
    print(f"Banco de dados SQLite inicializado com sucesso em: {SQLITE_DB_PATH}")

# Operações de Documentos
def insert_document(titulo: str, tipo: str, numero: Optional[str], ano: Optional[int], url: Optional[str], texto: str, revogado: int = 0, revogado_por: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Evitar duplicatas pelo título ou url
    cursor.execute("SELECT id FROM documentos WHERE titulo = ? OR (url = ? AND url IS NOT NULL)", (titulo, url))
    existing = cursor.fetchone()
    
    now = datetime.now().isoformat()
    if existing:
        doc_id = existing["id"]
        cursor.execute("""
        UPDATE documentos 
        SET tipo = ?, numero = ?, ano = ?, url = ?, texto = ?, revogado = ?, revogado_por = ?
        WHERE id = ?
        """, (tipo, numero, ano, url, texto, revogado, revogado_por, doc_id))
    else:
        cursor.execute("""
        INSERT INTO documentos (titulo, tipo, numero, ano, url, texto, revogado, revogado_por, data_cadastro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (titulo, tipo, numero, ano, url, texto, revogado, revogado_por, now))
        doc_id = cursor.lastrowid
        
    conn.commit()
    conn.close()
    return doc_id

def get_active_documents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documentos WHERE revogado = 0")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_as_revoked(titulo_or_numero: str, revogado_por: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE documentos 
    SET revogado = 1, revogado_por = ? 
    WHERE titulo LIKE ? OR numero = ?
    """, (revogado_por, f"%{titulo_or_numero}%", titulo_or_numero))
    changes = conn.total_changes
    conn.commit()
    conn.close()
    return changes > 0

# Operações de Mensagens
def save_message(sessao_id: str, papel: str, conteudo: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO mensagens (sessao_id, papel, conteudo, timestamp)
    VALUES (?, ?, ?, ?)
    """, (sessao_id, papel, conteudo, now))
    conn.commit()
    conn.close()

def get_chat_history(sessao_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT papel, conteudo FROM mensagens 
    WHERE sessao_id = ? 
    ORDER BY timestamp ASC
    """, (sessao_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Operações de Avaliação Q&A
def insert_qa_test(pergunta: str, resposta_esperada: str, categoria: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO avaliacao_qa (pergunta, resposta_esperada, categoria)
    VALUES (?, ?, ?)
    """, (pergunta, resposta_esperada, categoria))
    conn.commit()
    conn.close()

def get_all_qa_tests():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM avaliacao_qa")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
