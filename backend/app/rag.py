import os
from typing import Any, Dict, List

import google.generativeai as genai
from dotenv import load_dotenv

from database import get_chat_history, get_db_connection, save_message
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
    verificar status de vigência e formata o contexto para o LLM.
    """
    if not hits:
        return "Nenhum documento oficial encontrado no banco de dados para esta busca."

    doc_ids = list({hit["metadata"].get("doc_id") for hit in hits if hit.get("metadata", {}).get("doc_id")})
    doc_status: Dict[int, Dict[str, Any]] = {}

    if doc_ids:
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in doc_ids)
        cursor.execute(
            f"""
            SELECT id, titulo, tipo, numero, ano, url, revogado, revogado_por
            FROM documentos
            WHERE id IN ({placeholders})
            """,
            doc_ids,
        )
        doc_status = {row["id"]: dict(row) for row in cursor.fetchall()}
        conn.close()

    context_parts = []
    for hit in hits:
        metadata = hit["metadata"]
        doc_id = metadata.get("doc_id")
        texto_chunk = hit["texto"]
        titulo = metadata.get("titulo") or "Documento sem título"
        status = doc_status.get(doc_id, {})
        is_revogado = bool(status.get("revogado", metadata.get("revogado", False)))
        revogado_por = status.get("revogado_por") or metadata.get("revogado_por") or "documento não informado"
        numero = status.get("numero") or metadata.get("numero")
        ano = status.get("ano") or metadata.get("ano")
        url = status.get("url") or metadata.get("url")
        score = round(hit.get("score", hit.get("similarity", 0.0)), 4)

        detalhes = [f"Título: {titulo}"]
        if numero:
            detalhes.append(f"Número: {numero}")
        if ano:
            detalhes.append(f"Ano: {ano}")
        if url:
            detalhes.append(f"URL: {url}")
        detalhes.append(f"Score de recuperação: {score}")

        if is_revogado:
            context_parts.append(
                "--- DOCUMENTO REVOGADO (NÃO UTILIZAR COMO REGRA VIGENTE) ---\n"
                + "\n".join(detalhes)
                + f"\nStatus: Inativo/Revogado por {revogado_por}\n"
                + f"Trecho de referência antigo:\n{texto_chunk}\n"
                + "----------------------------------------------------------"
            )
        else:
            context_parts.append(
                "--- DOCUMENTO VIGENTE ---\n"
                + "\n".join(detalhes)
                + f"\nTrecho:\n{texto_chunk}\n"
                + "-------------------------"
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
    # Recuperar mais trechos melhora a chance de o contexto incluir a norma correta.
    hits = query_vector_db(query, n_results=6, include_revoked=True)

    # Resolver conflitos e formatar contexto
    context = format_context_and_resolve_conflicts(hits)

    # Obter histórico da conversa
    history_list = get_chat_history(sessao_id)
    history_str = ""
    for msg in history_list:
        papel_label = "Estudante" if msg["papel"] == "user" else "Assistente"
        history_str += f"{papel_label}: {msg['conteudo']}\n"

    # Construir o prompt do sistema e do usuário
    system_instruction = (
        "Você é o 'Manual do Uerjiano', um assistente de inteligência artificial amigável da UERJ "
        "(Universidade do Estado do Rio de Janeiro) criado para ajudar estudantes de graduação a navegarem pelas regras "
        "acadêmicas, direitos e serviços estudantis.\n\n"
        "Suas diretrizes fundamentais:\n"
        "1. RESPONDA DE FORMA CLARA, direta e acolhedora, em português brasileiro.\n"
        "2. SEMPRE CITE os documentos e artigos de apoio fornecidos no contexto "
        "(ex: 'De acordo com o AEDA 038/2007...').\n"
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
    seen_doc_ids = set()

    # Extrair fontes para exibir na UI, agora com metadados úteis para depuração.
    for hit in hits:
        meta = hit["metadata"]
        doc_key = meta.get("doc_id") or meta.get("titulo")
        if doc_key in seen_doc_ids:
            continue
        seen_doc_ids.add(doc_key)
        sources.append(
            {
                "doc_id": meta.get("doc_id"),
                "titulo": meta.get("titulo"),
                "tipo": meta.get("tipo"),
                "numero": meta.get("numero"),
                "ano": meta.get("ano"),
                "url": meta.get("url"),
                "revogado": meta.get("revogado", False),
                "score": round(hit.get("score", hit.get("similarity", 0.0)), 4),
            }
        )

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        response_text = (
            "⚠️ **Aviso: GEMINI_API_KEY não configurada.**\n\n"
            "Esta é uma resposta fictícia de teste (PoC) para demonstrar a estrutura do RAG. "
            "Para obter respostas reais, configure a chave de API no arquivo `.env`.\n\n"
            "**Contexto que seria analisado:**\n"
            + context[:500]
            + "..."
        )
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            response_text = response.text
        except Exception as e:
            response_text = f"Ocorreu um erro ao chamar a API do Gemini: {e}"

    # Salvar a interação no banco de dados SQLite
    save_message(sessao_id, "user", query)
    save_message(sessao_id, "model", response_text)

    return {"resposta": response_text, "fontes": sources}
