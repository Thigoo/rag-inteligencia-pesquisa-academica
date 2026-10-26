document.addEventListener("DOMContentLoaded", () => {
  const chatStream = document.getElementById("chat-stream");
  const ragForm = document.getElementById("rag-form");
  const queryInput = document.getElementById("query-input");
  const sendBtn = document.getElementById("send-btn");
  const quickBtns = document.querySelectorAll(".quick-btn");

  // Auto-resize do textarea
  queryInput.addEventListener("input", () => {
    queryInput.style.height = "auto";
    queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + "px";
  });

  // Enviar com Enter (sem Shift)
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ragForm.dispatchEvent(new Event("submit"));
    }
  });

  // Clique nos botões rápidos das personas
  quickBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const q = btn.getAttribute("data-query");
      queryInput.value = q;
      queryInput.dispatchEvent(new Event("input"));
      ragForm.dispatchEvent(new Event("submit"));
    });
  });

  // Submissão do Formulário
  ragForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    // Adiciona mensagem do usuário na tela
    appendUserMessage(query);
    queryInput.value = "";
    queryInput.style.height = "auto";
    sendBtn.disabled = true;

    // Adiciona indicador de carregamento
    const loadingCard = appendLoadingMessage();
    chatStream.scrollTop = chatStream.scrollHeight;

    try {
      const response = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, query_id: "web_" + Date.now() }),
      });

      const data = await response.json();
      loadingCard.remove();

      if (data.error) {
        appendErrorMessage(data.error);
      } else {
        appendAssistantMessage(data);
      }
    } catch (err) {
      loadingCard.remove();
      appendErrorMessage("Falha de conexão com o servidor local: " + err.message);
    } finally {
      sendBtn.disabled = false;
      queryInput.focus();
      chatStream.scrollTop = chatStream.scrollHeight;
    }
  });

  function appendUserMessage(text) {
    const card = document.createElement("div");
    card.className = "message-card user";
    card.innerHTML = `
      <div class="msg-avatar">👤</div>
      <div class="msg-body">${escapeHtml(text)}</div>
    `;
    chatStream.appendChild(card);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function appendLoadingMessage() {
    const card = document.createElement("div");
    card.className = "message-card assistant";
    card.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-body">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
        <small style="color: var(--text-muted); font-size: 11px;">Processando rotas e recuperando evidências...</small>
      </div>
    `;
    chatStream.appendChild(card);
    return card;
  }

  function appendAssistantMessage(data) {
    const card = document.createElement("div");
    card.className = "message-card assistant" + (data.is_refusal ? " refusal" : "");

    let sourcesHtml = "";
    if (data.sources && data.sources.length > 0) {
      const chips = data.sources
        .map(
          (s) =>
            `<span class="source-chip">📑 <strong>${escapeHtml(s.base_id)}</strong> (${escapeHtml(s.chunk_id)})</span>`
        )
        .join("");

      sourcesHtml = `
        <div class="sources-container">
          <div class="sources-header">Fontes Consultadas (${data.sources.length}):</div>
          <div class="source-chips">${chips}</div>
        </div>
      `;
    }

    let refusalBadge = "";
    if (data.is_refusal) {
      refusalBadge = `<div class="guardrails-notice" style="border-color: #ef4444; background: rgba(239,68,68,0.1); color: #f87171;">
        ⚠️ <strong>RECUSA ÉTICA / GUARDRAIL ACIONADO:</strong> Proteção de duplo-cego ou vedação de juízo depreciativo individual.
      </div>`;
    }

    const formattedAnswer = formatMarkdown(data.answer);

    card.innerHTML = `
      <div class="msg-avatar">${data.is_refusal ? "🛡️" : "🤖"}</div>
      <div class="msg-body">
        ${refusalBadge}
        <div class="answer-content">${formattedAnswer}</div>
        ${sourcesHtml}
        <div class="msg-footer">
          <span>⏱️ Latência: <strong>${data.latency_ms} ms</strong></span>
          <span>🆔 Run ID: <code>${escapeHtml(data.run_id)}</code></span>
        </div>
      </div>
    `;

    chatStream.appendChild(card);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function appendErrorMessage(errorMsg) {
    const card = document.createElement("div");
    card.className = "message-card assistant refusal";
    card.innerHTML = `
      <div class="msg-avatar">⚠️</div>
      <div class="msg-body">
        <strong style="color: #ef4444;">Erro no Pipeline:</strong>
        <p>${escapeHtml(errorMsg)}</p>
      </div>
    `;
    chatStream.appendChild(card);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    // Negrito
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Listas com bullet points
    html = html.replace(/\n\s*•\s*(.*?)(?=\n|$)/g, "<br>• $1");
    html = html.replace(/\n\s*-\s*(.*?)(?=\n|$)/g, "<br>• $1");
    // Quebras de linha
    html = html.replace(/\n/g, "<br>");
    return html;
  }
});
