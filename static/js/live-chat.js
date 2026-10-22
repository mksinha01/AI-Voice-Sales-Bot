/**
 * static/js/live-chat.js
 * Handles real-time live chat bubble rendering, typing animations, timestamps, and smooth auto-scroll.
 */

const LiveChat = {
  chatBox: null,
  seenIds: new Set(),
  typingElem: null,
  _observer: null,

  init() {
    this.chatBox = document.getElementById("live-chat-box");
    if (this.chatBox && !this._observer) {
      // Auto-scroll automatically whenever ANY message or child is added/updated
      this._observer = new MutationObserver(() => {
        this.scrollToBottom();
      });
      this._observer.observe(this.chatBox, { childList: true, subtree: true, characterData: true });
    }

    const downloadBtn = document.getElementById("btn-download-transcript");
    if (downloadBtn && !downloadBtn._hasListener) {
      downloadBtn._hasListener = true;
      downloadBtn.addEventListener("click", () => this.downloadTranscript());
    }
  },

  ensureChatVisible() {
    const chatBtn = document.getElementById("btn-view-chat");
    const subviewChat = document.getElementById("subview-chat");
    if (subviewChat && subviewChat.style.display === "none") {
      chatBtn?.click();
    }
  },

  clear() {
    if (!this.chatBox) this.init();
    if (this.chatBox) {
      this.chatBox.innerHTML = "";
    }
    this.seenIds.clear();
    this.typingElem = null;
  },

  showConnecting(title = "Alex • AI Agent", desc = "Connecting to live voice channel & initializing SaaS playbooks...") {
    if (!this.chatBox) this.init();
    if (!this.chatBox) return;

    this.ensureChatVisible();
    this.removeConnecting();
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble-nix bot";
    bubble.id = "connecting-placeholder";
    bubble.innerHTML = `
      <div class="chat-meta-nix">
        <span>${title.toUpperCase()}</span>
        <span style="color: var(--accent-lime);">CONNECTING...</span>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <span>${desc}</span>
        <div class="typing-dot" style="display: inline-block;"></div>
      </div>
    `;
    this.chatBox.appendChild(bubble);
    this.scrollToBottom();
  },

  removeConnecting() {
    const el = document.getElementById("connecting-placeholder");
    if (el) el.remove();
  },

  showTyping(speaker = "Alex") {
    if (!this.chatBox) this.init();
    if (!this.chatBox) return;

    this.ensureChatVisible();

    if (this.typingElem) {
      this.scrollToBottom();
      return;
    }

    const bubble = document.createElement("div");
    bubble.className = "chat-message-row bot-row";
    bubble.id = "live-typing-indicator";
    bubble.innerHTML = `
      <div class="chat-avatar bot-avatar"><i data-lucide="bot" style="width: 14px; height: 14px;"></i></div>
      <div class="chat-message-body">
        <div class="chat-sender-header">
          <span class="chat-sender-name">AI Agent</span>
        </div>
        <div class="chat-bubble-bubble bot-bubble typing-dots-bubble">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;

    this.typingElem = bubble;
    this.chatBox.appendChild(bubble);
    if (window.lucide) window.lucide.createIcons();
    this.scrollToBottom();
  },

  hideTyping() {
    if (this.typingElem) {
      this.typingElem.remove();
      this.typingElem = null;
    }
    const existing = document.getElementById("live-typing-indicator");
    if (existing) existing.remove();
  },

  appendMessage(speaker, text, timestamp, id = null) {
    if (!this.chatBox) this.init();
    if (!this.chatBox || !text || !text.trim()) return;

    this.ensureChatVisible();
    this.hideTyping();
    this.removeConnecting();

    const trimmed = text.trim();
    const textKey = `${speaker.toLowerCase()}:${trimmed.slice(0, 80)}`;
    if (id && this.seenIds.has(`id:${id}`)) return;
    if (this.seenIds.has(textKey)) {
      if (id) this.seenIds.add(`id:${id}`);
      return;
    }
    this.seenIds.add(textKey);
    if (id) this.seenIds.add(`id:${id}`);

    const timeStr = timestamp
      ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const isBot = speaker.toLowerCase() === "bot" || speaker.toLowerCase().includes("agent") || speaker.toLowerCase().includes("alex");

    const bubble = document.createElement("div");
    bubble.className = `chat-message-row ${isBot ? 'bot-row' : 'customer-row'}`;

    const avatarHtml = isBot
      ? `<div class="chat-avatar bot-avatar"><i data-lucide="bot" style="width: 14px; height: 14px;"></i></div>`
      : `<div class="chat-avatar customer-avatar"><i data-lucide="user" style="width: 14px; height: 14px;"></i></div>`;

    bubble.innerHTML = `
      ${avatarHtml}
      <div class="chat-message-body">
        <div class="chat-sender-header">
          <span class="chat-sender-name">${isBot ? 'AI Agent' : 'Customer'}</span>
          <span class="chat-msg-time">${timeStr}</span>
        </div>
        <div class="chat-bubble-bubble ${isBot ? 'bot-bubble' : 'customer-bubble'}">
          ${trimmed}
        </div>
      </div>
    `;

    this.chatBox.appendChild(bubble);
    if (window.lucide) window.lucide.createIcons();
    this.scrollToBottom();
  },

  scrollToBottom() {
    if (!this.chatBox) this.init();
    if (!this.chatBox) return;

    // Use dedicated container ref and update its scrollTop to scrollHeight.
    // Strictly isolate scrolling to this container. Do NOT scroll window, body, or parent containers.
    this.chatBox.scrollTop = this.chatBox.scrollHeight;
    requestAnimationFrame(() => {
      if (this.chatBox) {
        this.chatBox.scrollTop = this.chatBox.scrollHeight;
      }
    });
  },

  getTranscriptText() {
    if (!this.chatBox) this.init();
    if (!this.chatBox) return "";

    const rows = this.chatBox.querySelectorAll(".chat-message-row:not(#live-typing-indicator)");
    if (!rows || rows.length === 0) return "";

    const lines = [];
    const dateStr = new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    const product = window.AppState?.activeProduct ? `Product: ${window.AppState.activeProduct}` : "";

    lines.push("==================================================");
    lines.push("AI VOICE SALES BOT - LIVE TRANSCRIPT");
    lines.push(`Exported: ${dateStr} ${new Date().toLocaleTimeString()}`);
    if (product) lines.push(product);
    lines.push("==================================================\n");

    rows.forEach(row => {
      const sender = row.querySelector(".chat-sender-name")?.textContent?.trim() || "Speaker";
      const time = row.querySelector(".chat-msg-time")?.textContent?.trim() || "";
      const text = row.querySelector(".chat-bubble-bubble")?.textContent?.trim() || "";
      if (text) {
        lines.push(time ? `[${time}] ${sender}:\n${text}\n` : `${sender}:\n${text}\n`);
      }
    });

    lines.push("==================================================");
    lines.push("End of Transcript");
    return lines.join("\n");
  },

  downloadTranscript() {
    const text = this.getTranscriptText();
    if (!text) {
      alert("No transcript messages to download.");
      return;
    }
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    a.href = url;
    a.download = `live-transcript-${timestamp}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
};
