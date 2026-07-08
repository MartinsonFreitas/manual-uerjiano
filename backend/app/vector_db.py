import json
import math
import os
import re
import sqlite3
import time  # controle de limite da API
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv

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
    """Abre conexão SQLite e garante a existência da tabela vetorial."""
    os.makedirs(SQLITE_DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_DB_PATH), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            doc_id INTEGER,
            titulo TEXT,
            tipo TEXT,
            texto TEXT,
            chunk_idx INTEGER,
            embedding TEXT
        )
        """
    )
    conn.commit()
    migrate_legacy_vector_db()
    return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def migrate_legacy_vector_db():
    """Mescla os chunks vetoriais do banco legado em backend/data para o banco canônico."""
    current_conn = sqlite3.connect(str(SQLITE_DB_PATH), timeout=10.0, check_same_thread=False)
    current_conn.row_factory = sqlite3.Row
    current_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            doc_id INTEGER,
            titulo TEXT,
            tipo TEXT,
            texto TEXT,
            chunk_idx INTEGER,
            embedding TEXT
        )
        """
    )
    current_conn.commit()
    current_cursor = current_conn.cursor()

    for legacy_path in LEGACY_DB_PATHS:
        if legacy_path.resolve() == SQLITE_DB_PATH.resolve() or not legacy_path.exists():
            continue

        legacy_conn = sqlite3.connect(str(legacy_path), timeout=10.0, check_same_thread=False)
        legacy_conn.row_factory = sqlite3.Row
        legacy_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                doc_id INTEGER,
                titulo TEXT,
                tipo TEXT,
                texto TEXT,
                chunk_idx INTEGER,
                embedding TEXT
            )
            """
        )
        legacy_conn.commit()

        if table_exists(legacy_conn, "document_chunks"):
            legacy_cursor = legacy_conn.cursor()
            legacy_cursor.execute(
                "SELECT id, doc_id, titulo, tipo, texto, chunk_idx, embedding FROM document_chunks"
            )
            for row in legacy_cursor.fetchall():
                current_cursor.execute(
                    """
                    INSERT OR IGNORE INTO document_chunks
                    (id, doc_id, titulo, tipo, texto, chunk_idx, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["doc_id"],
                        row["titulo"],
                        row["tipo"],
                        row["texto"],
                        row["chunk_idx"],
                        row["embedding"],
                    ),
                )
        legacy_conn.close()

    current_conn.commit()
    current_conn.close()


def get_embedding(text: str, task_type: str = "retrieval_document") -> List[float]:
    """Gera o embedding do texto usando a API do Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("AVISO: GEMINI_API_KEY não definida. Retornando embedding vazio para testes.")
        return [0.0] * 768

    try:
        genai.configure(api_key=api_key)
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type=task_type,
        )
        return response["embedding"]
    except Exception as e:
        print(f"Erro ao gerar embedding: {e}")
        return [0.0] * 768


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Divide o texto em blocos, mantendo parágrafos e uma pequena sobreposição."""
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    current_words: List[str] = []
    current_size = 0

    for word in words:
        extra_space = 1 if current_words else 0
        if current_size + len(word) + extra_space <= chunk_size:
            current_words.append(word)
            current_size += len(word) + extra_space
            continue

        chunk = " ".join(current_words).strip()
        if chunk:
            chunks.append(chunk)

        # Mantém uma sobreposição aproximada em caracteres, preservando palavras inteiras.
        overlap_words: List[str] = []
        overlap_size = 0
        for previous_word in reversed(current_words):
            if overlap_size + len(previous_word) + 1 > overlap:
                break
            overlap_words.insert(0, previous_word)
            overlap_size += len(previous_word) + 1

        current_words = overlap_words + [word]
        current_size = sum(len(w) for w in current_words) + max(len(current_words) - 1, 0)

    final_chunk = " ".join(current_words).strip()
    if final_chunk:
        chunks.append(final_chunk)

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
        # Pausa para não estourar a cota gratuita do Gemini.
        time.sleep(1)
        emb = get_embedding(chunk, task_type="retrieval_document")
        cursor.execute(
            """
            INSERT INTO document_chunks (id, doc_id, titulo, tipo, texto, chunk_idx, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (chunk_id, doc_id, titulo, tipo, chunk, idx, json.dumps(emb)),
        )

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


def _load_embedding(raw_embedding: str) -> List[float]:
    try:
        emb = json.loads(raw_embedding or "[]")
        if isinstance(emb, list):
            return [float(value) for value in emb]
    except Exception:
        pass
    return [0.0] * 768


def _normalize_terms(text: str) -> List[str]:
    text = (text or "").lower()
    # Mantém letras acentuadas e números, útil para termos como AEDA 038/2007.
    terms = re.findall(r"[a-zà-ú0-9]+", text)
    return [term for term in terms if len(term) > 2]


def _keyword_overlap_score(query_text: str, chunk_text_value: str) -> float:
    """Score textual simples para complementar a busca vetorial."""
    query_terms = set(_normalize_terms(query_text))
    if not query_terms:
        return 0.0

    chunk_terms = set(_normalize_terms(chunk_text_value))
    if not chunk_terms:
        return 0.0

    return len(query_terms.intersection(chunk_terms)) / len(query_terms)


def _clamp_top_k(n_results: int) -> int:
    return max(1, min(int(n_results or 4), 20))


def query_vector_db(
    query_text: str,
    n_results: int = 4,
    tipo: Optional[str] = None,
    ano: Optional[int] = None,
    include_revoked: bool = True,
    min_score: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Busca os trechos mais relevantes no SQLite.

    A busca combina:
    - similaridade vetorial por embedding;
    - um pequeno reforço textual por interseção de palavras-chave;
    - filtros opcionais por tipo, ano e vigência do documento.
    """
    top_k = _clamp_top_k(n_results)
    query_emb = get_embedding(query_text, task_type="retrieval_query")

    conn = get_db_connection()
    has_documents_table = table_exists(conn, "documentos")
    cursor = conn.cursor()

    params: List[Any] = []
    where_clauses: List[str] = []

    if has_documents_table:
        select_sql = """
            SELECT
                dc.doc_id,
                COALESCE(d.titulo, dc.titulo) AS titulo,
                COALESCE(d.tipo, dc.tipo) AS tipo,
                d.numero AS numero,
                d.ano AS ano,
                d.url AS url,
                COALESCE(d.revogado, 0) AS revogado,
                d.revogado_por AS revogado_por,
                dc.texto,
                dc.chunk_idx,
                dc.embedding
            FROM document_chunks dc
            LEFT JOIN documentos d ON d.id = dc.doc_id
        """

        if tipo:
            where_clauses.append("LOWER(COALESCE(d.tipo, dc.tipo)) LIKE LOWER(?)")
            params.append(f"%{tipo}%")
        if ano is not None:
            where_clauses.append("d.ano = ?")
            params.append(ano)
        if not include_revoked:
            where_clauses.append("COALESCE(d.revogado, 0) = 0")
    else:
        select_sql = """
            SELECT
                doc_id,
                titulo,
                tipo,
                NULL AS numero,
                NULL AS ano,
                NULL AS url,
                0 AS revogado,
                NULL AS revogado_por,
                texto,
                chunk_idx,
                embedding
            FROM document_chunks
        """
        if tipo:
            where_clauses.append("LOWER(tipo) LIKE LOWER(?)")
            params.append(f"%{tipo}%")

    if where_clauses:
        select_sql += " WHERE " + " AND ".join(where_clauses)

    cursor.execute(select_sql, params)
    rows = cursor.fetchall()
    conn.close()

    hits: List[Dict[str, Any]] = []
    for row in rows:
        emb_list = _load_embedding(row["embedding"])
        similarity = cosine_similarity(query_emb, emb_list)
        keyword_score = _keyword_overlap_score(query_text, row["texto"])
        combined_score = (0.85 * similarity) + (0.15 * keyword_score)

        if min_score is not None and combined_score < min_score:
            continue

        hits.append(
            {
                "texto": row["texto"],
                "metadata": {
                    "doc_id": row["doc_id"],
                    "titulo": row["titulo"],
                    "tipo": row["tipo"],
                    "numero": row["numero"],
                    "ano": row["ano"],
                    "url": row["url"],
                    "revogado": bool(row["revogado"]),
                    "revogado_por": row["revogado_por"],
                    "chunk_idx": row["chunk_idx"],
                },
                "similarity": similarity,
                "keyword_score": keyword_score,
                "score": combined_score,
            }
        )

    hits.sort(key=lambda item: (item["score"], item["similarity"]), reverse=True)
    return hits[:top_k]


def retrieve_context_for_query(
    query_text: str,
    top_k: int = 5,
    tipo: Optional[str] = None,
    ano: Optional[int] = None,
    incluir_revogados: bool = False,
    score_minimo: Optional[float] = None,
) -> Dict[str, Any]:
    """Retorna uma resposta pronta para API com os chunks recuperados do banco."""
    if not query_text or not query_text.strip():
        raise ValueError("A consulta não pode ser vazia.")

    top_k = _clamp_top_k(top_k)
    hits = query_vector_db(
        query_text=query_text.strip(),
        n_results=top_k,
        tipo=tipo,
        ano=ano,
        include_revoked=incluir_revogados,
        min_score=score_minimo,
    )

    resultados = []
    for hit in hits:
        metadata = hit["metadata"]
        resultados.append(
            {
                "doc_id": metadata.get("doc_id"),
                "titulo": metadata.get("titulo"),
                "tipo": metadata.get("tipo"),
                "numero": metadata.get("numero"),
                "ano": metadata.get("ano"),
                "url": metadata.get("url"),
                "revogado": metadata.get("revogado", False),
                "revogado_por": metadata.get("revogado_por"),
                "chunk_idx": metadata.get("chunk_idx"),
                "score": round(hit.get("score", 0.0), 4),
                "similaridade_vetorial": round(hit.get("similarity", 0.0), 4),
                "score_textual": round(hit.get("keyword_score", 0.0), 4),
                "trecho": hit.get("texto", ""),
            }
        )

    return {
        "query": query_text.strip(),
        "top_k": top_k,
        "filtros": {
            "tipo": tipo,
            "ano": ano,
            "incluir_revogados": incluir_revogados,
            "score_minimo": score_minimo,
        },
        "total_retornado": len(resultados),
        "resultados": resultados,
    }


def get_vector_db_stats() -> Dict[str, Any]:
    """Retorna estatísticas do banco vetorial para depuração/administração."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM document_chunks")
    total_chunks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT doc_id) FROM document_chunks")
    total_documentos_indexados = cursor.fetchone()[0]

    stats_por_tipo = []
    documentos_revogados_indexados = 0

    if table_exists(conn, "documentos"):
        cursor.execute(
            """
            SELECT
                COALESCE(d.tipo, dc.tipo, 'Sem tipo') AS tipo,
                COUNT(DISTINCT dc.doc_id) AS documentos,
                COUNT(dc.id) AS chunks
            FROM document_chunks dc
            LEFT JOIN documentos d ON d.id = dc.doc_id
            GROUP BY COALESCE(d.tipo, dc.tipo, 'Sem tipo')
            ORDER BY documentos DESC, chunks DESC
            """
        )
        stats_por_tipo = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT COUNT(DISTINCT dc.doc_id)
            FROM document_chunks dc
            JOIN documentos d ON d.id = dc.doc_id
            WHERE COALESCE(d.revogado, 0) = 1
            """
        )
        documentos_revogados_indexados = cursor.fetchone()[0]
    else:
        cursor.execute(
            """
            SELECT COALESCE(tipo, 'Sem tipo') AS tipo,
                   COUNT(DISTINCT doc_id) AS documentos,
                   COUNT(id) AS chunks
            FROM document_chunks
            GROUP BY COALESCE(tipo, 'Sem tipo')
            ORDER BY documentos DESC, chunks DESC
            """
        )
        stats_por_tipo = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total_chunks": total_chunks,
        "total_documentos_indexados": total_documentos_indexados,
        "documentos_revogados_indexados": documentos_revogados_indexados,
        "por_tipo": stats_por_tipo,
    }


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
