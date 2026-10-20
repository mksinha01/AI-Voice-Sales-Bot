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
    bubble.className = "typing-bubble-nix";
    bubble.id = "live-typing-indicator";
    bubble.innerHTML = `
      <span style="font-size: 0.68rem; font-weight: 700; color: var(--accent-lime); letter-spacing: 0.05em; margin-right: 4px;">
        ${speaker.toUpperCase()} IS TYPING
      </span>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    `;

    this.typingElem = bubble;
    this.chatBox.appendChild(bubble);
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
      ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const isBot = speaker.toLowerCase() === "bot";

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble-nix ${isBot ? 'bot' : 'customer'}`;

    const meta = document.createElement("div");
    meta.className = "chat-meta-nix";
    meta.innerHTML = `<span>${isBot ? 'ALEX &bull; AI AGENT' : 'PROSPECT'}</span><span>${timeStr}</span>`;

    const content = document.createElement("div");
    content.textContent = trimmed;

    bubble.appendChild(meta);
    bubble.appendChild(content);
    this.chatBox.appendChild(bubble);

    // Auto-scroll automatically so older messages move upper and newest is visible
    this.scrollToBottom();
  },

  scrollToBottom() {
    if (!this.chatBox) this.init();
    if (!this.chatBox) return;

    const performScroll = () => {
      if (!this.chatBox) return;
      this.chatBox.scrollTop = this.chatBox.scrollHeight;
      const lastChild = this.chatBox.lastElementChild;
      if (lastChild && typeof lastChild.scrollIntoView === "function") {
        lastChild.scrollIntoView({ behavior: "smooth", block: "end", inline: "nearest" });
      }
    };

    performScroll();
    requestAnimationFrame(performScroll);
    setTimeout(performScroll, 50);
    setTimeout(performScroll, 150);
  }
};
