const messagesEl = document.getElementById("messages");
const emptyStateEl = document.getElementById("emptyState");
const formEl = document.getElementById("chatForm");
const inputEl = document.getElementById("chatInput");
const sendBtnEl = document.getElementById("sendBtn");
const newChatBtnEl = document.getElementById("newChatBtn");
const modeSelectEl = document.getElementById("modeSelect");
const modelBadgeEl = document.getElementById("modelBadge");
const footerModelEl = document.getElementById("footerModel");

const chatHistory = [];
let typingEl = null;

async function loadModes() {
  try {
    const res = await fetch("/api/chat/modes");
    if (res.ok) {
      const data = await res.json();
      if (data.default_mode && modeSelectEl) {
        modeSelectEl.value = data.default_mode;
        updateModelLabels(data.default_mode === "gemini" ? "gemini-3.8-flash" : "mock-sld-llm-v2");
      }
    }
  } catch (err) {
    console.warn("Could not load chat modes:", err);
  }
}

function updateModelLabels(modelName) {
  if (modelBadgeEl) modelBadgeEl.textContent = modelName;
  if (footerModelEl) footerModelEl.textContent = modelName;
}

if (modeSelectEl) {
  modeSelectEl.addEventListener("change", () => {
    const isGemini = modeSelectEl.value === "gemini";
    updateModelLabels(isGemini ? "gemini-3.8-flash" : "mock-sld-llm-v2");
  });
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

let mermaidInitialized = false;
function initMermaid() {
  if (window.mermaid && !mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "loose",
      fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
      themeVariables: {
        darkMode: true,
        background: "#171717",
        primaryColor: "#10a37f",
        primaryTextColor: "#ececec",
        primaryBorderColor: "#2f2f2f",
        lineColor: "#10a37f",
        secondaryColor: "#2a2a2a",
        tertiaryColor: "#212121",
        pie1: "#10a37f",
        pie2: "#3b82f6",
        pie3: "#f59e0b",
        pie4: "#ec4899",
        pie5: "#8b5cf6",
        pie6: "#06b6d4",
        pie7: "#10b981",
        pie8: "#6366f1",
      },
    });
    mermaidInitialized = true;
  }
}

if (typeof marked !== "undefined") {
  marked.setOptions({
    gfm: true,
    breaks: true,
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function preprocessMarkdown(content) {
  if (!content || typeof content !== "string") return content;

  let text = content;

  // 1. Normalize triple single quotes to triple backticks (e.g. ''' mermaid -> ```mermaid)
  text = text.replace(/'''[^\S\r\n]*([a-zA-Z0-9_-]*)/g, (match, lang) => {
    return "```" + (lang ? lang : "");
  });

  // 2. Normalize space in ``` mermaid -> ```mermaid
  text = text.replace(/```[^\S\r\n]+mermaid/gi, "```mermaid");

  const diagramKeywords = "(?:pie|graph|flowchart|sequenceDiagram|classDiagram|stateDiagram-v2|stateDiagram|erDiagram|journey|gantt|gitGraph|mindmap|timeline|quadrantChart|xychart|sankey-beta|kanban|block-beta)";

  // 3. Separate diagram keywords if they appear on the same line as ```mermaid
  // e.g. ```mermaid pie title ... -> ```mermaid\npie title ...
  const sameLineRegex = new RegExp("```mermaid[^\\S\\r\\n]+(" + diagramKeywords + "\\b[^\\n]*)", "gi");
  text = text.replace(sameLineRegex, "```mermaid\n$1");

  // 4. If code fence has no "mermaid" but starts with diagram keyword (e.g. ```pie title ...)
  const noMermaidRegex = new RegExp("```(?:[^\\S\\r\\n]*\\n\\s*|[^\\S\\r\\n]*)(" + diagramKeywords + "\\b[^\\n]*)", "gi");
  text = text.replace(noMermaidRegex, "```mermaid\n$1");

  // 5. If no backticks in string, but contains an unfenced diagram keyword at start of line:
  if (!text.includes("```")) {
    const unfencedRegex = new RegExp("(^|\\n)(" + diagramKeywords + "\\b[\\s\\S]*?$)", "i");
    const match = text.match(unfencedRegex);
    if (match) {
      const startIdx = match.index + match[1].length;
      const before = text.slice(0, startIdx);
      const diagram = text.slice(startIdx).trim();
      text = before + "\n```mermaid\n" + diagram + "\n```";
    }
  }

  return text;
}

function wrapTables(container) {
  const tables = container.querySelectorAll("table");
  tables.forEach((table) => {
    if (!table.parentElement.classList.contains("table-container")) {
      const wrap = document.createElement("div");
      wrap.className = "table-container";
      table.parentNode.insertBefore(wrap, table);
      wrap.appendChild(table);
    }
  });
}

let mermaidIdCounter = 0;
async function renderMermaidInElement(container) {
  initMermaid();
  if (!window.mermaid) return;

  const mermaidKeywords = /^\s*(pie|graph|flowchart|sequenceDiagram|classDiagram|stateDiagram-v2|stateDiagram|erDiagram|journey|gantt|gitGraph|mindmap|timeline|quadrantChart|xychart|sankey-beta|kanban|block-beta)\b/m;

  // Convert pre/code blocks containing mermaid
  const preElements = container.querySelectorAll("pre");
  preElements.forEach((pre) => {
    const codeEl = pre.querySelector("code");
    const text = (codeEl ? codeEl.textContent : pre.textContent).trim();
    const isMermaid = pre.classList.contains("language-mermaid") ||
                      (codeEl && (codeEl.classList.contains("language-mermaid") || codeEl.classList.contains("mermaid"))) ||
                      mermaidKeywords.test(text);

    if (isMermaid) {
      const wrap = document.createElement("div");
      wrap.className = "mermaid-wrap";
      const div = document.createElement("div");
      div.className = "mermaid-block";
      div.setAttribute("data-mermaid-code", text);
      wrap.appendChild(div);
      pre.replaceWith(wrap);
    }
  });

  // Convert standalone paragraphs containing unfenced mermaid
  const pElements = container.querySelectorAll("p");
  pElements.forEach((p) => {
    const text = p.textContent.trim();
    if (mermaidKeywords.test(text) && text.split("\n").length >= 2) {
      const wrap = document.createElement("div");
      wrap.className = "mermaid-wrap";
      const div = document.createElement("div");
      div.className = "mermaid-block";
      div.setAttribute("data-mermaid-code", text);
      wrap.appendChild(div);
      p.replaceWith(wrap);
    }
  });

  // Render each mermaid block
  const mermaidBlocks = container.querySelectorAll(".mermaid-block");
  for (const block of mermaidBlocks) {
    const code = block.getAttribute("data-mermaid-code");
    if (!code) continue;
    const renderId = `mermaid-${Date.now()}-${++mermaidIdCounter}`;
    try {
      const { svg } = await mermaid.render(renderId, code, block);
      block.innerHTML = svg;
    } catch (err) {
      try {
        const { svg } = await mermaid.render(renderId, code);
        block.innerHTML = svg;
      } catch (err2) {
        console.warn("Mermaid diagram rendering error:", err2 || err);
        const strayErr = document.getElementById(`d${renderId}`);
        if (strayErr) strayErr.remove();

        block.innerHTML = `<pre><code>${escapeHtml(code)}</code></pre><div class="mermaid-error">⚠️ Diagram render error: ${escapeHtml((err2 && err2.message) || (err && err.message) || "Invalid syntax")}</div>`;
      }
    }
  }

  scrollToBottom();
}

function hideEmptyState() {
  if (emptyStateEl && emptyStateEl.parentNode) {
    emptyStateEl.remove();
  }
}

function addMessage(role, content, extraClass = "", iterations = null, toolCalls = null) {
  hideEmptyState();

  const row = document.createElement("div");
  row.className = `message ${role} ${extraClass}`.trim();

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  // If there are iterations or tool calls recorded for assistant, display thought & iteration trace
  const hasIterations = Array.isArray(iterations) && iterations.length > 0;
  const hasToolCalls = Array.isArray(toolCalls) && toolCalls.length > 0;

  if (role === "assistant" && (hasIterations || hasToolCalls)) {
    const traceWrap = document.createElement("div");
    traceWrap.className = "trace-container";

    const details = document.createElement("details");
    details.className = "trace-details";

    const summary = document.createElement("summary");
    summary.className = "trace-summary";

    const totalSteps = hasIterations ? iterations.length : 1;
    const totalTools = hasToolCalls ? toolCalls.length : (hasIterations ? iterations.reduce((acc, it) => acc + (it.tool_calls ? it.tool_calls.length : 0), 0) : 0);

    const summaryLeft = document.createElement("span");
    summaryLeft.className = "trace-summary-left";
    summaryLeft.innerHTML = `<span>🧠 Agent Reasoning & Tools</span> <span class="trace-badge">${totalSteps} iteration${totalSteps > 1 ? "s" : ""} · ${totalTools} tool call${totalTools !== 1 ? "s" : ""}</span>`;

    summary.appendChild(summaryLeft);
    details.appendChild(summary);

    const contentEl = document.createElement("div");
    contentEl.className = "trace-content";

    if (hasIterations) {
      iterations.forEach((step) => {
        const iterCard = document.createElement("div");
        iterCard.className = "iteration-card";

        const iterHeader = document.createElement("div");
        iterHeader.className = "iteration-header";
        iterHeader.textContent = `Iteration ${step.iteration}`;
        iterCard.appendChild(iterHeader);

        if (step.thought) {
          const thoughtBox = document.createElement("div");
          thoughtBox.className = "thought-box";
          const thoughtLabel = document.createElement("div");
          thoughtLabel.className = "thought-label";
          thoughtLabel.textContent = "Thought";
          thoughtBox.appendChild(thoughtLabel);
          const thoughtText = document.createElement("div");
          thoughtText.textContent = step.thought;
          thoughtBox.appendChild(thoughtText);
          iterCard.appendChild(thoughtBox);
        }

        if (step.tool_calls && step.tool_calls.length > 0) {
          const toolsList = document.createElement("div");
          toolsList.className = "tool-calls-list";
          step.tool_calls.forEach((tc) => {
            const toolItem = document.createElement("div");
            toolItem.className = "tool-item";

            const th = document.createElement("div");
            th.className = "tool-item-header";
            th.innerHTML = `<span>⚡ ${tc.tool}()</span>`;

            const statusSpan = document.createElement("span");
            statusSpan.className = `tool-item-status ${tc.error ? "tool-status-error" : "tool-status-success"}`;
            statusSpan.textContent = tc.error ? "Failed" : "Success";
            th.appendChild(statusSpan);
            toolItem.appendChild(th);

            const jsonPreview = document.createElement("div");
            jsonPreview.className = "tool-json-preview";
            const previewData = {
              args: tc.parameters,
              summary: tc.summary,
            };
            if (tc.error) previewData.error = tc.error;
            if (tc.result) previewData.result = tc.result;
            jsonPreview.textContent = JSON.stringify(previewData, null, 2);
            toolItem.appendChild(jsonPreview);

            toolsList.appendChild(toolItem);
          });
          iterCard.appendChild(toolsList);
        }

        contentEl.appendChild(iterCard);
      });
    } else if (hasToolCalls) {
      // Fallback for standalone tool_calls
      const toolsList = document.createElement("div");
      toolsList.className = "tool-calls-list";
      toolCalls.forEach((tc) => {
        const toolItem = document.createElement("div");
        toolItem.className = "tool-item";

        const th = document.createElement("div");
        th.className = "tool-item-header";
        th.innerHTML = `<span>⚡ ${tc.tool}()</span>`;
        toolItem.appendChild(th);

        const jsonPreview = document.createElement("div");
        jsonPreview.className = "tool-json-preview";
        jsonPreview.textContent = JSON.stringify({ args: tc.parameters, summary: tc.summary }, null, 2);
        toolItem.appendChild(jsonPreview);

        toolsList.appendChild(toolItem);
      });
      contentEl.appendChild(toolsList);
    }

    details.appendChild(contentEl);
    traceWrap.appendChild(details);
    bubble.appendChild(traceWrap);
  }

  const replyEl = document.createElement("div");
  replyEl.className = "reply-text";

  if (role === "assistant") {
    const processedContent = preprocessMarkdown(content);
    let html = "";
    if (typeof marked !== "undefined" && typeof marked.parse === "function") {
      html = marked.parse(processedContent);
    } else {
      html = `<p>${escapeHtml(processedContent)}</p>`;
    }

    if (typeof DOMPurify !== "undefined" && typeof DOMPurify.sanitize === "function") {
      html = DOMPurify.sanitize(html);
    }

    replyEl.innerHTML = html;
    wrapTables(replyEl);
  } else {
    replyEl.textContent = content;
  }

  bubble.appendChild(replyEl);

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  scrollToBottom();

  if (role === "assistant") {
    renderMermaidInElement(replyEl);
  }

  return row;
}

function showTyping() {
  hideEmptyState();
  typingEl = document.createElement("div");
  typingEl.className = "message assistant typing";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const dots = document.createElement("div");
  dots.className = "typing-dots";
  dots.innerHTML = "<span></span><span></span><span></span>";

  bubble.appendChild(dots);
  typingEl.appendChild(avatar);
  typingEl.appendChild(bubble);
  messagesEl.appendChild(typingEl);
  scrollToBottom();
}

function hideTyping() {
  if (typingEl) {
    typingEl.remove();
    typingEl = null;
  }
}

function setSending(isSending) {
  sendBtnEl.disabled = isSending;
  inputEl.disabled = isSending;
}

function autosizeInput() {
  inputEl.style.height = "auto";
  inputEl.style.height = `${Math.min(inputEl.scrollHeight, 192)}px`;
}

async function sendMessage(text) {
  addMessage("user", text);
  chatHistory.push({ role: "user", content: text });

  setSending(true);
  showTyping();

  const currentMode = modeSelectEl ? modeSelectEl.value : "mock";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: chatHistory.slice(-10),
        mode: currentMode,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Backend returned ${response.status}`);
    }

    const data = await response.json();
    hideTyping();
    addMessage("assistant", data.reply, "", data.iterations, data.tool_calls);
    chatHistory.push({ role: "assistant", content: data.reply });
    if (data.model) {
      updateModelLabels(data.model);
    }
  } catch (error) {
    hideTyping();
    addMessage("assistant", `Error: ${error.message}`, "error");
  } finally {
    setSending(false);
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  autosizeInput();
  sendMessage(text);
});

inputEl.addEventListener("input", autosizeInput);

inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    formEl.requestSubmit();
  }
});

newChatBtnEl.addEventListener("click", () => {
  chatHistory.length = 0;
  messagesEl.innerHTML = "";
  if (emptyStateEl) {
    messagesEl.appendChild(emptyStateEl);
  }
  inputEl.value = "";
  autosizeInput();
  inputEl.focus();
});

loadModes();
inputEl.focus();
