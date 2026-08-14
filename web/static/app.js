/**
 * Local AI Coding Agent - Frontend Application Logic
 * Manages SSE streaming, tool card rendering, file tree explorer, and live model switching.
 */

// Application State
const state = {
  currentModel: "qwen2.5-coder:7b",
  safeMode: false,
  activeFilePath: null,
  isGenerating: false,
  isDrawerOpen: true,
  turnCount: 0
};

// DOM Elements
const elements = {
  modelSelect: document.getElementById("modelSelect"),
  safeModeToggle: document.getElementById("safeModeToggle"),
  clearChatBtn: document.getElementById("clearChatBtn"),
  toggleFileViewerBtn: document.getElementById("toggleFileViewerBtn"),
  fileViewerBtnText: document.getElementById("fileViewerBtnText"),
  refreshFilesBtn: document.getElementById("refreshFilesBtn"),
  workspacePath: document.getElementById("workspacePath"),
  fileTreeContainer: document.getElementById("fileTreeContainer"),
  chatMessages: document.getElementById("chatMessages"),
  chatForm: document.getElementById("chatForm"),
  promptInput: document.getElementById("promptInput"),
  sendBtn: document.getElementById("sendBtn"),
  fileViewerDrawer: document.getElementById("fileViewerDrawer"),
  drawerFileName: document.getElementById("drawerFileName"),
  drawerPlaceholder: document.getElementById("drawerPlaceholder"),
  drawerCodeEditor: document.getElementById("drawerCodeEditor"),
  saveFileBtn: document.getElementById("saveFileBtn"),
  askAboutFileBtn: document.getElementById("askAboutFileBtn"),
  closeDrawerBtn: document.getElementById("closeDrawerBtn"),
  statTurns: document.getElementById("statTurns"),
  statActiveModel: document.getElementById("statActiveModel"),
  connectionStatus: document.getElementById("connectionStatus"),
  currentFileTag: document.getElementById("currentFileTag"),
  currentFileName: document.getElementById("currentFileName"),
  clearActiveFileBtn: document.getElementById("clearActiveFileBtn")
};

// Initialize marked.js configuration
if (typeof marked !== 'undefined') {
  marked.setOptions({
    breaks: true,
    gfm: true
  });
}

/**
 * Initialize Application
 */
async function init() {
  setupEventListeners();
  await loadStatusAndModels();
  await loadWorkspaceTree();
  autoResizeTextarea();
}

/**
 * Setup Event Handlers
 */
function setupEventListeners() {
  // Model switch
  elements.modelSelect.addEventListener("change", async (e) => {
    const selected = e.target.value;
    try {
      const res = await fetch("/api/models/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: selected })
      });
      const data = await res.json();
      if (data.success) {
        state.currentModel = data.current_model;
        elements.statActiveModel.textContent = state.currentModel;
      }
    } catch (err) {
      console.error("Error switching model:", err);
    }
  });

  // Safe mode toggle
  elements.safeModeToggle.addEventListener("change", async (e) => {
    state.safeMode = e.target.checked;
    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ safe_mode: state.safeMode })
    });
  });

  // Clear Chat
  elements.clearChatBtn.addEventListener("click", async () => {
    await fetch("/api/clear", { method: "POST" });
    elements.chatMessages.innerHTML = `
      <div class="message-card system-welcome-card">
        <div class="welcome-header">
          <div class="welcome-avatar">⚡</div>
          <div class="welcome-title-group">
            <h2>Conversation Memory Cleared</h2>
            <p>Ready for a fresh task with local model: <strong>${state.currentModel}</strong>.</p>
          </div>
        </div>
      </div>
    `;
    state.turnCount = 0;
    elements.statTurns.textContent = "0";
  });

  // Refresh files
  elements.refreshFilesBtn.addEventListener("click", loadWorkspaceTree);

  // Toggle File Viewer Drawer
  elements.toggleFileViewerBtn.addEventListener("click", toggleDrawer);
  elements.closeDrawerBtn.addEventListener("click", toggleDrawer);

  // Save modified file
  elements.saveFileBtn.addEventListener("click", saveCurrentFile);

  // Ask about file
  elements.askAboutFileBtn.addEventListener("click", () => {
    if (state.activeFilePath) {
      elements.promptInput.value = `Please review and inspect \`${state.activeFilePath}\`: `;
      elements.promptInput.focus();
    }
  });

  // Clear active file tag
  elements.clearActiveFileBtn.addEventListener("click", () => {
    state.activeFilePath = null;
    elements.currentFileTag.style.display = "none";
  });

  // Quick Action Chips
  document.querySelectorAll(".quick-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const promptText = chip.getAttribute("data-prompt");
      elements.promptInput.value = promptText;
      elements.promptInput.focus();
      autoResizeTextarea();
    });
  });

  // Chat Form Submit
  elements.chatForm.addEventListener("submit", handleSubmitPrompt);

  // Textarea Enter key handling (Shift+Enter for newline)
  elements.promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      elements.chatForm.dispatchEvent(new Event("submit"));
    }
  });

  elements.promptInput.addEventListener("input", autoResizeTextarea);
}

/**
 * Auto-resize prompt textarea
 */
function autoResizeTextarea() {
  const textarea = elements.promptInput;
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
}

/**
 * Toggle File Drawer Open/Close
 */
function toggleDrawer() {
  state.isDrawerOpen = !state.isDrawerOpen;
  if (state.isDrawerOpen) {
    elements.fileViewerDrawer.classList.remove("closed");
    elements.fileViewerBtnText.textContent = "Hide Viewer";
  } else {
    elements.fileViewerDrawer.classList.add("closed");
    elements.fileViewerBtnText.textContent = "File Viewer";
  }
}

/**
 * Fetch status and populate models
 */
async function loadStatusAndModels() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    if (data.status === "ok") {
      state.currentModel = data.agent.model;
      state.safeMode = data.agent.safe_mode;
      elements.safeModeToggle.checked = state.safeMode;
      elements.statActiveModel.textContent = state.currentModel;
      elements.workspacePath.textContent = data.agent.workspace;

      // Populate models
      elements.modelSelect.innerHTML = "";
      (data.available_models || []).forEach(m => {
        const opt = document.createElement("option");
        opt.value = m.name;
        opt.textContent = `${m.name} (${m.size})`;
        if (m.name === state.currentModel) opt.selected = true;
        elements.modelSelect.appendChild(opt);
      });

      // Update online badge
      if (data.agent.connected) {
        elements.connectionStatus.innerHTML = `<span class="status-dot online"></span><span class="status-label">Ollama Connected</span>`;
      } else {
        elements.connectionStatus.innerHTML = `<span class="status-dot offline"></span><span class="status-label">Ollama Offline</span>`;
      }
    }
  } catch (err) {
    console.error("Failed to load status:", err);
    elements.connectionStatus.innerHTML = `<span class="status-dot offline"></span><span class="status-label">Ollama Offline</span>`;
  }
}

/**
 * Fetch and render workspace file tree
 */
async function loadWorkspaceTree() {
  try {
    const res = await fetch("/api/workspace/tree");
    const data = await res.json();

    if (data.tree) {
      elements.fileTreeContainer.innerHTML = "";
      renderTreeNode(data.tree, elements.fileTreeContainer, 0);
    }
  } catch (err) {
    elements.fileTreeContainer.innerHTML = `<div style="padding:8px; color:var(--accent-red); font-size:0.75rem;">Error loading files</div>`;
  }
}

function renderTreeNode(node, container, depth) {
  if (!node) return;

  const itemEl = document.createElement("div");
  itemEl.className = "tree-item";
  itemEl.style.paddingLeft = `${depth * 14 + 6}px`;

  const isDir = node.type === "directory";
  const icon = isDir ? "📁" : getFileIcon(node.name);

  itemEl.innerHTML = `
    <span class="tree-item-icon">${icon}</span>
    <span class="tree-item-name">${node.name}</span>
  `;

  if (!isDir && node.path) {
    itemEl.addEventListener("click", () => openFileInViewer(node.path));
  }

  container.appendChild(itemEl);

  if (isDir && node.children && node.children.length > 0) {
    node.children.forEach(child => renderTreeNode(child, container, depth + 1));
  }
}

function getFileIcon(filename) {
  if (filename.endsWith(".py")) return "🐍";
  if (filename.endsWith(".js") || filename.endsWith(".ts")) return "📜";
  if (filename.endsWith(".html")) return "🌐";
  if (filename.endsWith(".css")) return "🎨";
  if (filename.endsWith(".json")) return "⚙️";
  if (filename.endsWith(".md")) return "📝";
  if (filename.endsWith(".bat") || filename.endsWith(".sh")) return "⚡";
  return "📄";
}

/**
 * Open file in Right Drawer Editor
 */
async function openFileInViewer(relativePath) {
  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(relativePath)}`);
    const data = await res.json();

    if (data.content !== undefined) {
      state.activeFilePath = relativePath;
      elements.drawerFileName.textContent = relativePath;
      elements.drawerPlaceholder.style.display = "none";
      elements.drawerCodeEditor.style.display = "block";
      elements.drawerCodeEditor.value = data.content;
      elements.saveFileBtn.style.display = "inline-flex";
      elements.askAboutFileBtn.style.display = "inline-flex";

      // Show active file tag in input bar
      elements.currentFileTag.style.display = "inline-flex";
      elements.currentFileName.textContent = relativePath;

      if (!state.isDrawerOpen) toggleDrawer();
    }
  } catch (err) {
    alert("Could not load file: " + err.message);
  }
}

/**
 * Save file modifications back to disk
 */
async function saveCurrentFile() {
  if (!state.activeFilePath) return;

  const content = elements.drawerCodeEditor.value;
  try {
    const res = await fetch("/api/workspace/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: state.activeFilePath, content: content })
    });
    const data = await res.json();
    if (data.success) {
      elements.saveFileBtn.textContent = "✔ Saved!";
      setTimeout(() => { elements.saveFileBtn.textContent = "💾 Save File"; }, 2000);
      loadWorkspaceTree();
    } else {
      alert("Error saving: " + data.output);
    }
  } catch (err) {
    alert("Failed to save: " + err.message);
  }
}

/**
 * Submit chat prompt and consume SSE stream
 */
async function handleSubmitPrompt(e) {
  e.preventDefault();
  if (state.isGenerating) return;

  const prompt = elements.promptInput.value.trim();
  if (!prompt) return;

  // Append user message UI
  appendUserMessage(prompt);
  elements.promptInput.value = "";
  autoResizeTextarea();

  state.turnCount += 1;
  elements.statTurns.textContent = state.turnCount;
  state.isGenerating = true;
  elements.sendBtn.disabled = true;

  // Create Assistant Message Box
  const assistantContainer = createAssistantMessageCard();
  const reasoningSection = assistantContainer.querySelector(".reasoning-stream");
  const markdownSection = assistantContainer.querySelector(".markdown-stream");

  let accumulatedContent = "";

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const event = JSON.parse(line.slice(6));
            handleAgentEvent(event, reasoningSection, markdownSection, () => accumulatedContent, (val) => { accumulatedContent = val; });
          } catch (pe) {
            console.error("JSON parse error on SSE chunk:", pe);
          }
        }
      }
      scrollToBottom();
    }
  } catch (err) {
    markdownSection.innerHTML += `<div style="color:var(--accent-red); margin-top:8px;">❌ Communication Error: ${err.message}</div>`;
  } finally {
    state.isGenerating = false;
    elements.sendBtn.disabled = false;
    await loadWorkspaceTree(); // refresh files in case agent created/edited files
  }
}

/**
 * Handle discrete Agent Events from SSE
 */
function handleAgentEvent(event, reasoningEl, markdownEl, getContent, setContent) {
  const type = event.type;
  const data = event.data || {};

  if (type === "token") {
    const delta = data.delta || "";
    setContent(getContent() + delta);
    if (typeof marked !== 'undefined') {
      markdownEl.innerHTML = marked.parse(getContent());
    } else {
      markdownEl.textContent = getContent();
    }
  } else if (type === "tool_start") {
    const toolName = data.tool || "unknown";
    const toolArgs = data.args || {};
    const step = data.step || 1;

    const toolCard = document.createElement("div");
    toolCard.className = "tool-card";
    toolCard.id = `tool-card-step-${step}-${toolName}`;

    const argsStr = Object.entries(toolArgs).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");

    toolCard.innerHTML = `
      <div class="tool-header" onclick="this.parentElement.querySelector('.tool-output').classList.toggle('collapsed')">
        <div class="tool-title">
          <span class="tool-badge">${toolName}</span>
          <span style="color:var(--text-muted); font-size:0.75rem;">(${argsStr})</span>
        </div>
        <span class="tool-status-badge running">Running...</span>
      </div>
      <div class="tool-output">Executing tool in workspace...</div>
    `;

    reasoningEl.appendChild(toolCard);
  } else if (type === "tool_end") {
    const toolName = data.tool || "";
    const success = data.success;
    const output = data.output || "(Empty output)";
    const step = data.step || 1;

    const card = reasoningEl.querySelector(`#tool-card-step-${step}-${toolName}`) || reasoningEl.querySelector(".tool-card:last-child");
    if (card) {
      const badge = card.querySelector(".tool-status-badge");
      if (badge) {
        badge.className = `tool-status-badge ${success ? "success" : "error"}`;
        badge.textContent = success ? "✔ Done" : "✖ Failed";
      }
      const outEl = card.querySelector(".tool-output");
      if (outEl) {
        outEl.textContent = output;
      }
    }
  } else if (type === "message") {
    const finalContent = data.content || "";
    setContent(finalContent);
    if (typeof marked !== 'undefined') {
      markdownEl.innerHTML = marked.parse(finalContent);
    } else {
      markdownEl.textContent = finalContent;
    }
  } else if (type === "error") {
    markdownEl.innerHTML += `<div style="color:var(--accent-red); margin-top:8px;">❌ Agent Error: ${data.message}</div>`;
  }
}

/**
 * Append User Message Card
 */
function appendUserMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row user-row";
  row.innerHTML = `
    <div class="message-content-wrapper">
      <div class="message-bubble user-bubble">${escapeHtml(text)}</div>
    </div>
    <div class="message-avatar user">👤</div>
  `;
  elements.chatMessages.appendChild(row);
  scrollToBottom();
}

/**
 * Create Assistant Card
 */
function createAssistantMessageCard() {
  const row = document.createElement("div");
  row.className = "message-row assistant-row";
  row.innerHTML = `
    <div class="message-avatar assistant">⚡</div>
    <div class="message-content-wrapper">
      <div class="message-bubble assistant-bubble">
        <div class="reasoning-stream"></div>
        <div class="markdown-stream markdown-body"></div>
      </div>
    </div>
  `;
  elements.chatMessages.appendChild(row);
  scrollToBottom();
  return row;
}

function scrollToBottom() {
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Start app on DOM load
document.addEventListener("DOMContentLoaded", init);
