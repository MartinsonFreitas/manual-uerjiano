import os
import sys
import threading
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Adicionar o diretório atual ao path para garantir importações
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawler import run_ingest
from database import (
    get_all_qa_tests,
    get_chat_history,
    get_db_connection,
    init_db,
    insert_qa_test,
)
from rag import generate_rag_response
from vector_db import get_vector_db_stats, retrieve_context_for_query

# Carregar variáveis de ambiente do arquivo .env (caso exista)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.env"))

app = FastAPI(title="Manual do Uerjiano API", version="1.1.0")

# Configurar CORS para permitir acessos locais do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modelos Pydantic para validação
class ChatRequest(BaseModel):
    sessao_id: str
    mensagem: str


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="Pergunta ou termo que será buscado no banco vetorial.")
    top_k: int = Field(5, ge=1, le=20, description="Quantidade máxima de trechos retornados.")
    tipo: Optional[str] = Field(None, description="Filtro opcional por tipo de documento, ex.: AEDA.")
    ano: Optional[int] = Field(None, description="Filtro opcional por ano do documento.")
    incluir_revogados: bool = Field(
        False,
        description="Quando falso, remove documentos revogados da consulta direta.",
    )
    score_minimo: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Score mínimo combinado para retornar um trecho.",
    )


class QARequest(BaseModel):
    pergunta: str
    resposta_esperada: str
    categoria: Optional[str] = None


# Evento de inicialização do sistema
@app.on_event("startup")
def startup_event():
    # Inicializa tabelas do SQLite
    init_db()

    # Se a base estiver zerada, executa a semente automática em segundo plano
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM documentos")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        print("Banco de dados sem documentos. Iniciando indexação inicial de semente em segundo plano...")
        thread = threading.Thread(target=run_ingest)
        thread.start()


# Rotas do Chatbot
@app.post("/api/chat")
def api_chat(request: ChatRequest):
    if not request.mensagem.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode ser vazia.")

    try:
        response = generate_rag_response(request.sessao_id, request.mensagem)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history/{sessao_id}")
def api_history(sessao_id: str):
    try:
        history = get_chat_history(sessao_id)
        return {"historico": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/retrieve")
def api_retrieve(request: RetrieveRequest):
    """
    Consulta direta ao banco vetorial/SQLite.

    Essa rota permite ver quais trechos seriam enviados como contexto para o LLM,
    com score, metadados, filtros e status de vigência do documento.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="A consulta não pode ser vazia.")

    try:
        return retrieve_context_for_query(
            query_text=request.query,
            top_k=request.top_k,
            tipo=request.tipo,
            ano=request.ano,
            incluir_revogados=request.incluir_revogados,
            score_minimo=request.score_minimo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Rotas de Administração e Crawler
@app.post("/api/admin/ingest")
def api_admin_ingest(background_tasks: BackgroundTasks):
    """Executa o crawler e indexação em segundo plano."""
    try:
        background_tasks.add_task(run_ingest)
        return {"status": "success", "message": "Processo de ingestão iniciado em segundo plano."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/documents")
def api_admin_documents():
    """Lista todos os documentos salvos no banco SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, titulo, tipo, numero, ano, url, revogado, revogado_por, data_cadastro
            FROM documentos
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return {"documentos": [dict(row) for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/vector-stats")
def api_admin_vector_stats():
    """Mostra estatísticas do banco vetorial para depuração do RAG."""
    try:
        return get_vector_db_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Rotas de Avaliação Q&A
@app.post("/api/admin/qa_test")
def api_add_qa_test(request: QARequest):
    """Adiciona uma pergunta/resposta padrão para avaliação."""
    try:
        insert_qa_test(request.pergunta, request.resposta_esperada, request.categoria)
        return {"status": "success", "message": "Pergunta de teste cadastrada com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/qa_tests")
def api_get_qa_tests():
    """Retorna todas as perguntas de avaliação cadastradas."""
    try:
        tests = get_all_qa_tests()
        return {"testes": tests}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/eval")
def api_run_eval():
    """Compara as respostas do RAG contra o dataset Q&A cadastrado."""
    tests = get_all_qa_tests()

    if not tests:
        # Se não houver testes salvos, insere alguns padrões
        default_tests = [
            ("Qual a média para aprovação direta na UERJ?", "Média Semestral igual ou superior a 7,0.", "Avaliação"),
            (
                "O que acontece se eu reprovar 3 vezes na mesma matéria?",
                "O aluno será desligado da UERJ (jubilamento).",
                "Desligamento",
            ),
            (
                "Qual o valor atual da Bolsa de Apoio à Vulnerabilidade Social?",
                "O valor atual é de R$ 700,00 mensais segundo o AEDA 045/2024.",
                "Bolsas",
            ),
            (
                "Quanto custa a refeição no bandejão para cotistas?",
                "A refeição é gratuita para alunos bolsistas PR4 / Cotistas.",
                "Serviços",
            ),
        ]
        for q, r, cat in default_tests:
            insert_qa_test(q, r, cat)
        tests = get_all_qa_tests()

    results = []
    correct_count = 0

    # Realiza a avaliação
    for test in tests:
        pergunta = test["pergunta"]
        esperado = test["resposta_esperada"]

        # Gerar resposta com RAG (usando sessão de avaliação dedicada)
        rag_res = generate_rag_response("sessao_de_avaliacao_qa", pergunta)
        resposta_gerada = rag_res["resposta"]

        # Avaliação de acerto básica semântica (verificação de termos chave no texto)
        esperado_palavras = esperado.lower().replace(",", "").replace(".", "").split()
        match_count = sum(1 for w in esperado_palavras if w in resposta_gerada.lower())
        match_ratio = match_count / len(esperado_palavras) if esperado_palavras else 0
        passed = match_ratio > 0.4  # Pelo menos 40% de correspondência de palavras-chave

        if passed:
            correct_count += 1

        results.append(
            {
                "id": test["id"],
                "pergunta": pergunta,
                "resposta_esperada": esperado,
                "resposta_gerada": resposta_gerada,
                "taxa_correspondencia": round(match_ratio, 2),
                "status": "PASS" if passed else "FAIL",
            }
        )

    accuracy = correct_count / len(tests) if tests else 0
    return {
        "acuracia": round(accuracy, 2),
        "total_testes": len(tests),
        "testes_aprovados": correct_count,
        "detalhes": results,
    }


# Servir arquivos estáticos do Frontend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static_frontend")
else:
    print(f"AVISO: Pasta do frontend não encontrada em {frontend_path}. O app servirá apenas a API.")
