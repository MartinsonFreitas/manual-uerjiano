# Changelog

Todas as mudanças relevantes deste projeto serão documentadas aqui.

## [Unreleased]

### Adicionado
- Adicionada rota `POST /api/retrieve` para consultar diretamente os trechos mais relevantes do banco vetorial.
- Adicionada rota `GET /api/admin/vector-stats` para inspecionar estatísticas do banco vetorial, como total de chunks e documentos indexados.
- Incluído retorno com metadados mais completos na busca, incluindo título, tipo, número, ano, URL, status de revogação, score e trecho recuperado.

### Melhorado
- Melhorada a etapa de recuperação de contexto usada pelo RAG antes da chamada ao LLM.
- A busca vetorial agora permite filtros por tipo de documento, ano, documentos revogados e score mínimo.
- As fontes retornadas pelo chatbot ficaram mais detalhadas, facilitando a validação das respostas.
- Melhorado o chunking dos documentos para preservar sobreposição entre trechos e reduzir perda de contexto.

### Técnico
- A busca combina similaridade vetorial com uma pontuação textual simples, melhorando a recuperação em perguntas com termos específicos.
- A lógica de consulta ao banco foi separada para poder ser usada tanto pelo chatbot quanto por rotas administrativas de depuração.