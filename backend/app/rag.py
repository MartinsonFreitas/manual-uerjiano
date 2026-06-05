import os
import google.generativeai as genai
from typing import List, Dict, Any
from dotenv import load_dotenv
from database import get_db_connection, save_message, get_chat_history
from vector_db import query_vector_db

# Carregar variáveis de ambiente
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.env"))

# Configurar API do Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def format_context_and_resolve_conflicts(hits: List[Dict[str, Any]]) -> str:
    """
    Analisa os trechos retornados do banco vetorial, consulta o SQLite para
    verificar o status de vigência de cada documento e formata o contexto
    com tratamento de conflito de leis (leis revogadas).
    """
    if not hits:
        return "Nenhum documento oficial encontrado no banco de dados para esta busca."
        
    doc_ids = list(set([hit["metadata"]["doc_id"] for hit in hits]))
    
    # Consultar SQLite para verificar se os documentos estão revogados
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in doc_ids)
    cursor.execute(f"SELECT id, titulo, tipo, numero, ano, revogado, revogado_por FROM documentos WHERE id IN ({placeholders})", doc_ids)
    doc_status = {row["id"]: dict(row) for row in cursor.fetchall()}
    conn.close()
    
    context_parts = []
    
    for hit in hits:
        metadata = hit["metadata"]
        doc_id = metadata["doc_id"]
        texto_chunk = hit["texto"]
        titulo = metadata["titulo"]
        
        status = doc_status.get(doc_id, {})
        is_revogado = status.get("revogado", 0) == 1
        revogado_por = status.get("revogado_por", "")
        
        if is_revogado:
            # Em vez de omitir, avisamos explicitamente ao modelo que o documento foi revogado
            context_parts.append(
                f"--- DOCUMENTO REVOGADO (NÃO UTILIZAR COMO REGRA VIGENTE) ---\n"
                f"Título: {titulo}\n"
                f"Status: Inativo/Revogado por {revogado_por}\n"
                f"Trecho de referência antigo:\n{texto_chunk}\n"
                f"----------------------------------------------------------"
            )
        else:
            context_parts.append(
                f"--- DOCUMENTO VIGENTE ---\n"
                f"Título: {titulo}\n"
                f"Trecho:\n{texto_chunk}\n"
                f"-------------------------"
            )
            
    return "\n\n".join(context_parts)

def generate_rag_response(sessao_id: str, query: str) -> Dict[str, Any]:
    """
    Executa o fluxo completo do RAG:
    1. Busca trechos no banco vetorial.
    2. Resolve conflitos de leis consultando o SQLite.
    3. Recupera o histórico de chat da sessão.
    4. Envia para o Gemini gerar a resposta humanizada.
    5. Salva a interação no histórico.
    """
    # 1. Recuperar trechos do ChromaDB
    hits = query_vector_db(query, n_results=4)
    
    # 2. Resolver conflitos e formatar contexto
    context = format_context_and_resolve_conflicts(hits)
    
    # 3. Obter histórico da conversa
    history_list = get_chat_history(sessao_id)
    history_str = ""
    for msg in history_list:
        papel_label = "Estudante" if msg["papel"] == "user" else "Assistente"
        history_str += f"{papel_label}: {msg['conteudo']}\n"
        
    # 4. Construir o prompt do sistema e do usuário
    system_instruction = (
        "Você é o 'Manual do Uerjiano', um assistente de inteligência artificial amigável da UERJ "
        "(Universidade do Estado do Rio de Janeiro) criado para ajudar estudantes de graduação a navegarem pelas regras "
        "acadêmicas, direitos e serviços estudantis.\n\n"
        "Suas diretrizes fundamentais:\n"
        "1. RESPONDA DE FORMA CLARA, direta e acolhedora, em português brasileiro.\n"
        "2. SEMPRE CITE os documentos e artigos de apoio fornecidos no contexto (ex: 'De acordo com o AEDA 038/2007...').\n"
        "3. TRATAMENTO DE LEIS REVOGADAS: Se o contexto indicar que um documento foi revogado ou atualizado, você "
        "deve alertar o estudante de que a regra antiga não está mais em vigor e apresentar a nova regra descrita "
        "no documento vigente.\n"
        "4. LIMITAÇÃO DE INFORMAÇÃO: Se a resposta não puder ser extraída do contexto fornecido, diga educadamente "
        "que não possui essa informação cadastrada nos documentos da universidade e sugira procurar o DAA "
        "(Departamento de Administração Acadêmica) ou a coordenação do curso. Não invente regras acadêmicas.\n"
    )
    
    prompt = f"""
{system_instruction}

Aqui estão as informações oficiais da UERJ recuperadas para esta consulta:
{context}

Histórico da conversa recente:
{history_str}

Pergunta do Estudante: {query}
"""

    response_text = ""
    sources = []
    
    # Extrair fontes não revogadas para exibir na UI
    for hit in hits:
        meta = hit["metadata"]
        doc_id = meta["doc_id"]
        # Filtrar duplicatas de títulos
        font_info = {"titulo": meta["titulo"], "tipo": meta["tipo"]}
        if font_info not in sources:
            sources.append(font_info)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        response_text = (
            "⚠️ **Aviso: GEMINI_API_KEY não configurada.**\n\n"
            "Esta é uma resposta fictícia de teste (PoC) para demonstrar a estrutura do RAG. "
            "Para obter respostas reais, configure a chave de API no arquivo `.env`.\n\n"
            "**Contexto que seria analisado:**\n" + context[:500] + "..."
        )
    else:
        try:
            # Configurar API
            genai.configure(api_key=api_key)
            # Usando gemini-2.5-flash que é suportado pela API
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            response_text = response.text
        except Exception as e:
            response_text = f"Ocorreu um erro ao chamar a API do Gemini: {e}"
            
    # 5. Salvar a interação no banco de dados SQLite
    save_message(sessao_id, "user", query)
    save_message(sessao_id, "model", response_text)
    
    return {
        "resposta": response_text,
        "fontes": sources
    }
