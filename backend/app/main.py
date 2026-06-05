import os
import sys
import threading
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Adicionar o diretório atual ao path para garantir importações
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_db_connection, insert_qa_test, get_all_qa_tests, get_chat_history
from crawler import run_ingest
from rag import generate_rag_response

# Carregar variáveis de ambiente do arquivo .env (caso exista)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.env"))

app = FastAPI(title="Manual do Uerjiano API", version="1.0.0")

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
        cursor.execute("SELECT id, titulo, tipo, numero, ano, url, revogado, revogado_por, data_cadastro FROM documentos")
        rows = cursor.fetchall()
        conn.close()
        return {"documentos": [dict(row) for row in rows]}
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
            ("O que acontece se eu reprovar 3 vezes na mesma matéria?", "O aluno será desligado da UERJ (jubilamento).", "Desligamento"),
            ("Qual o valor atual da Bolsa de Apoio à Vulnerabilidade Social?", "O valor atual é de R$ 700,00 mensais segundo o AEDA 045/2024.", "Bolsas"),
            ("Quanto custa a refeição no bandejão para cotistas?", "A refeição é gratuita para alunos bolsistas PR4 / Cotistas.", "Serviços")
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
        # Em produção, poderíamos usar um LLM avaliador (LLM-as-a-judge)
        # Para esta PoC, usaremos uma verificação básica de compatibilidade de termos
        esperado_palavras = esperado.lower().replace(",", "").replace(".", "").split()
        match_count = sum(1 for w in esperado_palavras if w in resposta_gerada.lower())
        match_ratio = match_count / len(esperado_palavras) if esperado_palavras else 0
        
        passed = match_ratio > 0.4 # Pelo menos 40% de correspondência de palavras-chave
        if passed:
            correct_count += 1
            
        results.append({
            "id": test["id"],
            "pergunta": pergunta,
            "resposta_esperada": esperado,
            "resposta_gerada": resposta_gerada,
            "taxa_correspondencia": round(match_ratio, 2),
            "status": "PASS" if passed else "FAIL"
        })
        
    accuracy = correct_count / len(tests) if tests else 0
    return {
        "acuracia": round(accuracy, 2),
        "total_testes": len(tests),
        "testes_aprovados": correct_count,
        "detalhes": results
    }

# Servir arquivos estáticos do Frontend
# O frontend deve estar em 'c:\manual-uerjiano\frontend'
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static_frontend")
else:
    print(f"AVISO: Pasta do frontend não encontrada em {frontend_path}. O app servirá apenas a API.")
