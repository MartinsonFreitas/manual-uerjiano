import sqlite3
import os
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

# Obter o caminho do banco de dados a partir das variáveis de ambiente ou usar o padrão
SQLITE_DB_PATH = os.environ.get("SQLITE_DB_PATH", "../data/manual_uerjiano.db")

# Garantir que a pasta de dados existe
os.makedirs(os.path.dirname(os.path.abspath(SQLITE_DB_PATH)), exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
