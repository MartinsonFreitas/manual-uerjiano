// Configuração da API - Detecta se está rodando no FastAPI ou localmente
const API_BASE = window.location.hostname === "" || window.location.port === "5500" || window.location.port === "3000"
    ? "http://127.0.0.1:8000"
    : "";

// Estado da Aplicação
let currentSessionId = localStorage.getItem("current_sessao_id") || generateSessionId();
let currentTheme = localStorage.getItem("theme") || "dark";

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
    // Definir tema inicial
    document.documentElement.setAttribute("data-theme", currentTheme);
    updateThemeToggleIcon();
    
    // Configurar ID da sessão padrão
    localStorage.setItem("current_sessao_id", currentSessionId);
    
    // Registrar Eventos da Interface
    setupEventHandlers();
    
    // Carregar histórico se houver
    loadChatHistory();
});

// Auxiliares
function generateSessionId() {
    return "session_" + Math.random().toString(36).substring(2, 9) + "_" + Date.now();
}

function updateThemeToggleIcon() {
    const themeBtn = document.getElementById("theme-toggle-btn");
    if (themeBtn) {
        themeBtn.innerHTML = currentTheme === "dark" 
            ? '<i class="fa-regular fa-sun"></i>' 
            : '<i class="fa-regular fa-moon"></i>';
    }
}

// Configuração de Eventos
function setupEventHandlers() {
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const newChatBtn = document.getElementById("new-chat-btn");
    const clearChatBtn = document.getElementById("clear-chat-btn");
    const themeToggleBtn = document.getElementById("theme-toggle-btn");
    
    // Painel de Administração
    const openAdminBtn = document.getElementById("open-admin-btn");
    const closeAdminBtn = document.getElementById("close-admin-btn");
    const adminModal = document.getElementById("admin-modal");
    const triggerCrawlerBtn = document.getElementById("trigger-crawler-btn");
    const runEvalBtn = document.getElementById("run-eval-btn");
    
    // Monitoramento do Input de Mensagem
    chatInput.addEventListener("input", () => {
        // Redimensionamento automático do textarea
        chatInput.style.height = "auto";
        chatInput.style.height = (chatInput.scrollHeight - 4) + "px";
        
        // Habilitar/desabilitar botão Enviar
        sendBtn.disabled = chatInput.value.trim() === "";
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener("click", sendMessage);

    // Novo Chat
    newChatBtn.addEventListener("click", () => {
        currentSessionId = generateSessionId();
        localStorage.setItem("current_sessao_id", currentSessionId);
        
        // Atualizar lista de sessões na UI (simulação rápida)
        const sessionsList = document.getElementById("sessions-list");
        const activeSession = sessionsList.querySelector(".session-item.active");
        if (activeSession) activeSession.classList.remove("active");
        
        const newSessionItem = document.createElement("div");
        newSessionItem.className = "session-item active";
        newSessionItem.setAttribute("data-id", currentSessionId);
        newSessionItem.innerHTML = `<i class="fa-regular fa-message"></i> <span>Conversa ${new Date().toLocaleTimeString()}</span>`;
        newSessionItem.onclick = () => switchSession(currentSessionId);
        sessionsList.insertBefore(newSessionItem, sessionsList.firstChild);
        
        clearChatUI();
    });

    // Limpar Conversa Atual
    clearChatBtn.addEventListener("click", () => {
        if (confirm("Tem certeza que deseja limpar o histórico desta conversa?")) {
            clearChatUI();
        }
    });

    // Alternador de Temas
    themeToggleBtn.addEventListener("click", () => {
        currentTheme = currentTheme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", currentTheme);
        localStorage.setItem("theme", currentTheme);
        updateThemeToggleIcon();
    });

    // Eventos de Cliques nos Cards de Sugestões
    document.querySelectorAll(".prompt-card").forEach(card => {
        card.addEventListener("click", () => {
            const prompt = card.getAttribute("data-prompt");
            chatInput.value = prompt;
            chatInput.style.height = "auto";
            sendBtn.disabled = false;
            sendMessage();
        });
    });

    // Controles do Modal de Administração
    openAdminBtn.addEventListener("click", () => {
        adminModal.style.display = "flex";
        loadAdminDocs();
    });

    closeAdminBtn.addEventListener("click", () => {
        adminModal.style.display = "none";
    });

    window.addEventListener("click", (e) => {
        if (e.target === adminModal) {
            adminModal.style.display = "none";
        }
    });

    // Abas do Modal Admin
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(btn.getAttribute("data-tab")).classList.add("active");
        });
    });

    // Crawler Trigger
    triggerCrawlerBtn.addEventListener("click", () => {
        triggerCrawlerBtn.disabled = true;
        triggerCrawlerBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Executando raspagem...';
        
        fetch(`${API_BASE}/api/admin/ingest`, { method: "POST" })
            .then(res => res.json())
            .then(data => {
                alert("Raspagem de dados iniciada em segundo plano! A base de dados será atualizada gradualmente.");
                setTimeout(loadAdminDocs, 5000);
            })
            .catch(err => {
                console.error(err);
                alert("Erro ao iniciar raspagem.");
            })
            .finally(() => {
                triggerCrawlerBtn.disabled = false;
                triggerCrawlerBtn.innerHTML = '<i class="fa-solid fa-rotate"></i> Forçar Raspagem e Reindexação';
            });
    });

    // Executar Avaliação RAG
    runEvalBtn.addEventListener("click", runEvaluation);
}

// Alternar entre sessões
function switchSession(sessionId) {
    currentSessionId = sessionId;
    localStorage.setItem("current_sessao_id", currentSessionId);
    
    document.querySelectorAll(".session-item").forEach(item => {
        item.classList.toggle("active", item.getAttribute("data-id") === sessionId);
    });
    
    loadChatHistory();
}

// Limpa mensagens da UI
function clearChatUI() {
    const container = document.getElementById("messages-container");
    container.innerHTML = `
        <div class="welcome-container" id="welcome-container">
            <div class="welcome-badge">PoC de Inteligência Artificial</div>
            <h1>Como posso ajudar você hoje, Uerjiano?</h1>
            <p class="welcome-subtitle">Pergunte sobre notas, trancamentos, bandejão, bolsas, critérios de aprovação ou qualquer legislação interna da universidade.</p>
            <div class="quick-prompts-grid">
                <div class="prompt-card" data-prompt="Qual a média para aprovação direta e como funciona a prova final?">
                    <div class="prompt-card-icon"><i class="fa-solid fa-chart-line"></i></div>
                    <h3>Aprovação e Notas</h3>
                    <p>Qual a média para aprovação direta e como funciona a prova final na UERJ?</p>
                </div>
                <div class="prompt-card" data-prompt="Quantas vezes posso reprovar na mesma disciplina antes de ser desligado?">
                    <div class="prompt-card-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                    <h3>Reprovações e Desligamento</h3>
                    <p>Quantas vezes posso reprovar na mesma matéria antes de ser jubilado?</p>
                </div>
                <div class="prompt-card" data-prompt="Quais são as bolsas e auxílios de assistência estudantil oferecidos pela PR4 e quais os valores?">
                    <div class="prompt-card-icon"><i class="fa-solid fa-hand-holding-dollar"></i></div>
                    <h3>Bolsas e Auxílios</h3>
                    <p>Quais as bolsas da PR4, seus valores e regras para cumulação?</p>
                </div>
                <div class="prompt-card" data-prompt="Qual o valor da refeição no bandejão para cotistas e estudantes em geral, e qual o horário de funcionamento?">
                    <div class="prompt-card-icon"><i class="fa-solid fa-utensils"></i></div>
                    <h3>Restaurante Universitário</h3>
                    <p>Qual o preço do bandejão, horários de acesso e regras de tickets?</p>
                </div>
            </div>
        </div>
    `;
    
    // Re-registrar os eventos nos novos cards criados
    document.querySelectorAll(".prompt-card").forEach(card => {
        card.addEventListener("click", () => {
            const prompt = card.getAttribute("data-prompt");
            const chatInput = document.getElementById("chat-input");
            const sendBtn = document.getElementById("send-btn");
            chatInput.value = prompt;
            chatInput.style.height = "auto";
            sendBtn.disabled = false;
            sendMessage();
        });
    });
}

// Carregar Histórico do Servidor
function loadChatHistory() {
    fetch(`${API_BASE}/api/history/${currentSessionId}`)
        .then(res => res.json())
        .then(data => {
            if (data.historico && data.historico.length > 0) {
                const welcome = document.getElementById("welcome-container");
                if (welcome) welcome.style.display = "none";
                
                const container = document.getElementById("messages-container");
                // Remove as bolhas de chat anteriores, mas deixa o welcome container oculto
                const chatRows = container.querySelectorAll(".message-row");
                chatRows.forEach(row => row.remove());
                
                data.historico.forEach(msg => {
                    appendMessageBubble(msg.papel === "user" ? "user" : "bot", msg.conteudo);
                });
                
                scrollToBottom();
            } else {
                clearChatUI();
            }
        })
        .catch(err => {
            console.error("Erro ao carregar histórico:", err);
        });
}

// Enviar Mensagem para a API
function sendMessage() {
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const query = chatInput.value.trim();
    
    if (query === "") return;
    
    // Ocultar Boas-vindas
    const welcome = document.getElementById("welcome-container");
    if (welcome) welcome.style.display = "none";
    
    // Adicionar mensagem do usuário na interface
    appendMessageBubble("user", query);
    
    // Limpar input
    chatInput.value = "";
    chatInput.style.height = "auto";
    sendBtn.disabled = true;
    
    // Adicionar bolha de digitação temporária do bot
    const loaderId = appendTypingIndicator();
    scrollToBottom();
    
    // Fazer requisição ao backend
    fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            sessao_id: currentSessionId,
            mensagem: query
        })
    })
    .then(res => {
        if (!res.ok) throw new Error("Erro na resposta do servidor");
        return res.json();
    })
    .then(data => {
        removeTypingIndicator(loaderId);
        appendMessageBubble("bot", data.resposta, data.fontes);
        scrollToBottom();
    })
    .catch(err => {
        console.error(err);
        removeTypingIndicator(loaderId);
        appendMessageBubble("bot", "⚠️ Desculpe, ocorreu um erro de conexão com o servidor. Verifique se o backend está ativo.");
        scrollToBottom();
    });
}

// Adicionar bolha de mensagem na tela
function appendMessageBubble(sender, text, sources = []) {
    const container = document.getElementById("messages-container");
    
    const row = document.createElement("div");
    row.className = `message-row ${sender}`;
    
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    
    // Formatação de texto simplificada (Simula renderizador Markdown básico)
    let formattedText = formatTextMarkdown(text);
    bubble.innerHTML = formattedText;
    
    // Inserir fontes citadas se for o bot e tiver fontes
    if (sender === "bot" && sources && sources.length > 0) {
        const sourcesDiv = document.createElement("div");
        sourcesDiv.className = "sources-container";
        sourcesDiv.innerHTML = '<span class="sources-label">Fontes Utilizadas:</span>';
        
        sources.forEach(source => {
            const badge = document.createElement("span");
            badge.className = "citation-badge";
            badge.innerHTML = `<i class="fa-solid fa-file-invoice"></i> ${source.titulo.split(" - ")[0]}`;
            sourcesDiv.appendChild(badge);
        });
        
        bubble.appendChild(sourcesDiv);
    }
    
    row.appendChild(bubble);
    container.appendChild(row);
}

// Renderização básica de marcações tipo Markdown
function formatTextMarkdown(text) {
    if (!text) return "";
    
    let html = text;
    
    // Tratamento de alertas de revogação no texto
    if (html.includes("REVOGADO") || html.includes("revogado")) {
        // Envolve passagens de revogação em uma div de aviso estilizada
        html = html.replace(/(O documento .*? foi revogado .*?\.)/gi, '<div class="revoked-alert"><strong><i class="fa-solid fa-triangle-exclamation"></i> Documento Revogado:</strong> $1</div>');
    }
    
    // Formata negrito **texto**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    
    // Formata listas com marcadores
    html = html.replace(/^\s*-\s+(.*?)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*?<\/li>)/s, "<ul>$1</ul>"); // Envelopa grupos em ul simples
    
    // Quebras de linha
    html = html.replace(/\n/g, "<br>");
    
    return html;
}

// Indicador de digitação
function appendTypingIndicator() {
    const container = document.getElementById("messages-container");
    const loaderId = "typing_" + Date.now();
    
    const row = document.createElement("div");
    row.className = "message-row bot";
    row.id = loaderId;
    
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    
    bubble.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    
    row.appendChild(bubble);
    container.appendChild(row);
    return loaderId;
}

function removeTypingIndicator(loaderId) {
    const elem = document.getElementById(loaderId);
    if (elem) elem.remove();
}

function scrollToBottom() {
    const container = document.getElementById("messages-container");
    container.scrollTop = container.scrollHeight;
}

// CARREGAR DOCUMENTOS NO PAINEL ADMIN
function loadAdminDocs() {
    const tableBody = document.getElementById("admin-docs-table-body");
    const statDocsCount = document.getElementById("stat-docs-count");
    
    fetch(`${API_BASE}/api/admin/documents`)
        .then(res => res.json())
        .then(data => {
            if (data.documentos && data.documentos.length > 0) {
                statDocsCount.innerText = data.documentos.length;
                tableBody.innerHTML = "";
                
                data.documentos.forEach(doc => {
                    const tr = document.createElement("tr");
                    
                    const isRevogadoBadge = doc.revogado === 1
                        ? `<span class="badge revoked" title="Revogado por: ${doc.revogado_por || 'Não especificado'}">Revogado</span>`
                        : '<span class="badge active">Vigente</span>';
                        
                    const typeClass = doc.tipo.toLowerCase().includes("aeda") ? "type-aeda" : "type-reg";
                    const tipoBadge = `<span class="badge ${typeClass}">${doc.tipo}</span>`;
                    
                    const docUrl = doc.url 
                        ? `<a href="${doc.url}" target="_blank" class="citation-badge"><i class="fa-solid fa-arrow-up-right-from-square"></i> Ver PDF</a>`
                        : '<span class="text-secondary">Nenhum</span>';
                    
                    tr.innerHTML = `
                        <td>${doc.id}</td>
                        <td><strong>${doc.titulo}</strong></td>
                        <td>${tipoBadge}</td>
                        <td>${doc.ano || "N/A"}</td>
                        <td>${isRevogadoBadge}</td>
                        <td>${docUrl}</td>
                    `;
                    tableBody.appendChild(tr);
                });
            } else {
                tableBody.innerHTML = '<tr><td colspan="6" class="empty-table">Nenhum documento indexado. Clique em "Forçar Raspagem" para carregar.</td></tr>';
            }
        })
        .catch(err => {
            console.error(err);
            tableBody.innerHTML = '<tr><td colspan="6" class="empty-table text-danger">Erro ao carregar documentos do servidor.</td></tr>';
        });
}

// EXECUTAR TESTE DE AVALIAÇÃO RAG E MODELO
function runEvaluation() {
    const runEvalBtn = document.getElementById("run-eval-btn");
    const statEvalScore = document.getElementById("stat-eval-score");
    const evalSummary = document.getElementById("eval-summary-text");
    const evalList = document.getElementById("eval-results-list");
    
    runEvalBtn.disabled = true;
    runEvalBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Executando testes...';
    evalSummary.innerHTML = "Executando testes semânticos em lote com diferentes perguntas. Isso pode demorar até um minuto...";
    evalList.innerHTML = "";
    
    fetch(`${API_BASE}/api/admin/eval`, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            // Atualizar pontuação de acurácia
            const scorePercent = Math.round(data.acuracia * 100) + "%";
            statEvalScore.innerText = scorePercent;
            
            // Sumário
            evalSummary.innerHTML = `
                <strong>Avaliação Concluída!</strong> Acurácia geral de <strong>${scorePercent}</strong> (${data.testes_aprovados} de ${data.total_testes} testes aprovados).
                Os testes comparam termos essenciais da resposta padrão contra a resposta gerada pelo modelo de IA integrada com RAG.
            `;
            
            // Listar Detalhes
            data.detalhes.forEach(result => {
                const card = document.createElement("div");
                card.className = "eval-result-card";
                
                const statusBadge = result.status === "PASS"
                    ? '<span class="eval-badge pass">PASSOU</span>'
                    : '<span class="eval-badge fail">FALHOU</span>';
                    
                card.innerHTML = `
                    <div class="eval-header">
                        <span class="eval-q"><i class="fa-regular fa-circle-question"></i> ${result.pergunta}</span>
                        ${statusBadge}
                    </div>
                    <div class="eval-details">
                        <div class="eval-block expected">
                            <strong>Resposta Esperada:</strong><br>${result.resposta_esperada}
                        </div>
                        <div class="eval-block generated">
                            <strong>Gerada pelo RAG:</strong><br>${formatTextMarkdown(result.resposta_gerada)}
                            <div style="margin-top: 8px; font-size: 11px; color: var(--text-secondary)">
                                Taxa de correspondência semântica: ${Math.round(result.taxa_correspondencia * 100)}%
                            </div>
                        </div>
                    </div>
                `;
                evalList.appendChild(card);
            });
        })
        .catch(err => {
            console.error(err);
            evalSummary.innerHTML = "❌ Ocorreu um erro ao processar a avaliação automática.";
        })
        .finally(() => {
            runEvalBtn.disabled = false;
            runEvalBtn.innerHTML = '<i class="fa-solid fa-gauge-high"></i> Executar Testes Q&A e Avaliação';
        });
}
