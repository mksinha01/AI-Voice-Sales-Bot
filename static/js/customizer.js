/**
 * static/js/customizer.js
 * Support & Prompts Studio: Agent Version Control, System Prompt Tuning & SaaS Specs.
 */

const Customizer = {
  modal: null,
  activeTab: "versions",
  agentId: "agent-alex-closer",
  versions: [],
  selectedVersion: null,
  liveActiveVersion: null,

  init() {
    this.modal = document.getElementById("customizer-modal");

    // Close buttons & Backdrop click
    document.getElementById("btn-close-modal")?.addEventListener("click", () => this.closeModal());
    if (this.modal) {
      this.modal.addEventListener("click", (e) => {
        if (e.target === this.modal) this.closeModal();
      });
    }

    // Tab buttons
    document.getElementById("tab-btn-versions")?.addEventListener("click", () => this.switchTab("versions"));
    document.getElementById("tab-btn-prompt")?.addEventListener("click", () => this.switchTab("prompt"));
    document.getElementById("tab-btn-product")?.addEventListener("click", () => this.switchTab("product"));

    // Version Control Actions
    document.getElementById("modal-btn-create-draft")?.addEventListener("click", () => this.createDraftVersion());
    document.getElementById("modal-btn-ai-gen")?.addEventListener("click", () => this.generateAiStrategy());
    document.getElementById("modal-ai-instruction")?.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        this.generateAiStrategy();
      }
    });

    // Prompt Tab Actions
    document.getElementById("btn-apply-prompt")?.addEventListener("click", () => this.applyPromptToActiveCall());
    document.getElementById("btn-save-as-new-ver")?.addEventListener("click", () => this.savePromptAsNewDraft());
    document.getElementById("btn-reset-prompt")?.addEventListener("click", () => this.resetPrompt());

    // Product Tab Actions
    document.getElementById("btn-reset-customizer")?.addEventListener("click", () => this.resetDefaults());
    document.getElementById("btn-save-customizer")?.addEventListener("click", () => this.saveConfiguration());

    // Initial load of version data in background
    this.loadVersions();
  },

  openModal() {
    if (this.modal) {
      this.modal.classList.add("open");
      this.loadVersions();
      if (window.lucide) window.lucide.createIcons();
    }
  },

  closeModal() {
    if (this.modal) this.modal.classList.remove("open");
  },

  switchTab(tab) {
    this.activeTab = tab;
    const btnVersions = document.getElementById("tab-btn-versions");
    const btnPrompt = document.getElementById("tab-btn-prompt");
    const btnProduct = document.getElementById("tab-btn-product");

    const contentVersions = document.getElementById("tab-content-versions");
    const contentPrompt = document.getElementById("tab-content-prompt");
    const contentProduct = document.getElementById("tab-content-product");

    [btnVersions, btnPrompt, btnProduct].forEach(b => b?.classList.remove("active"));
    if (contentVersions) contentVersions.style.display = "none";
    if (contentPrompt) contentPrompt.style.display = "none";
    if (contentProduct) contentProduct.style.display = "none";

    if (tab === "versions") {
      btnVersions?.classList.add("active");
      if (contentVersions) contentVersions.style.display = "flex";
      this.loadVersions();
    } else if (tab === "prompt") {
      btnPrompt?.classList.add("active");
      if (contentPrompt) contentPrompt.style.display = "flex";
    } else if (tab === "product") {
      btnProduct?.classList.add("active");
      if (contentProduct) contentProduct.style.display = "flex";
    }

    if (window.lucide) window.lucide.createIcons();
  },

  async loadVersions() {
    try {
      const resp = await fetch(`/api/agents/${this.agentId}/versions`);
      if (!resp.ok) return;
      const data = await resp.json();
      this.versions = data.versions || [];

      // Find live active version
      this.liveActiveVersion = this.versions.find(v => v.status === "active") || this.versions[0] || null;

      // Update Header Badges
      const countElem = document.getElementById("modal-version-count");
      if (countElem) countElem.textContent = this.versions.length;

      const liveBadgeText = document.getElementById("customizer-live-text");
      if (liveBadgeText && this.liveActiveVersion) {
        liveBadgeText.textContent = `Live: v${this.liveActiveVersion.version_number}`;
      }

      this.renderVersionsList();
    } catch (err) {
      console.warn("Failed to load agent versions in modal:", err);
    }
  },

  renderVersionsList() {
    const listContainer = document.getElementById("modal-version-list");
    if (!listContainer) return;

    if (!this.versions.length) {
      listContainer.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No agent versions found.</div>`;
      return;
    }

    listContainer.innerHTML = this.versions.map(v => {
      const isLive = v.status === "active";
      const isDraft = v.status === "draft";
      const isArchived = v.status === "archived";

      let statusBadge = `<span class="version-pill-badge">PUBLISHED</span>`;
      if (isLive) statusBadge = `<span class="version-pill-badge live">● LIVE ACTIVE</span>`;
      else if (isDraft) statusBadge = `<span class="version-pill-badge draft">DRAFT</span>`;
      else if (isArchived) statusBadge = `<span class="version-pill-badge" style="opacity: 0.5;">ARCHIVED</span>`;

      const title = v.name || v.version_tag || `Version ${v.version_number}`;
      const desc = v.sales_strategy || v.agent_role || "Sales Closer Agent Persona";

      return `
        <div class="modal-version-card ${isLive ? 'is-live' : ''}" data-version-id="${v.id}">
          <div class="modal-version-meta">
            <div class="modal-version-header-row">
              <span class="version-pill-badge ${isLive ? 'live' : ''}">v${v.version_number}</span>
              <span class="modal-version-name" title="${title}">${title}</span>
              ${statusBadge}
            </div>
            <div class="modal-version-desc" title="${desc}">${desc}</div>
          </div>

          <div class="modal-version-actions">
            ${isLive ? `
              <button class="btn-version-action is-active-btn" disabled>
                <i data-lucide="check" style="width: 12px; height: 12px;"></i>
                <span>Active</span>
              </button>
            ` : `
              <button class="btn-version-action btn-activate" onclick="Customizer.activateVersion('${v.id}')" title="Immediately deploy this version to live calls">
                <i data-lucide="zap" style="width: 12px; height: 12px;"></i>
                <span>Set Live</span>
              </button>
            `}
            <button class="btn-version-action" onclick="Customizer.inspectPrompt('${v.id}')" title="Inspect & edit system prompt in editor">
              <i data-lucide="file-code" style="width: 12px; height: 12px;"></i>
              <span>Prompt</span>
            </button>
            <button class="btn-version-action" onclick="Customizer.duplicateVersion('${v.id}')" title="Clone into a new draft">
              <i data-lucide="copy" style="width: 12px; height: 12px;"></i>
            </button>
            ${!isLive ? `
              <button class="btn-version-action" onclick="Customizer.deleteVersion('${v.id}')" title="Delete this version" style="color: #ef4444; border-color: rgba(239, 68, 68, 0.35);">
                <i data-lucide="trash-2" style="width: 12px; height: 12px;"></i>
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }).join("");

    if (window.lucide) window.lucide.createIcons();
  },

  async activateVersion(versionId) {
    try {
      const resp = await fetch(`/api/agents/${this.agentId}/versions/${versionId}/activate`, {
        method: "POST"
      });
      if (!resp.ok) {
        const err = await resp.json();
        alert(`Activation failed: ${err.detail || "Server error"}`);
        return;
      }
      const data = await resp.json();

      // Reset any manual temporary prompt override so the active version takes full effect
      window.AppState.customSystemPrompt = null;

      // Update dashboard bot role status
      const roleStatus = document.getElementById("bot-role-status");
      if (roleStatus && data.active_version) {
        roleStatus.innerHTML = `<span class="status-dot-pulse"></span> Live: v${data.active_version.version_number} (${data.active_version.name})`;
      }

      await this.loadVersions();
    } catch (e) {
      console.error("Activate version error:", e);
      alert("Network error activating version.");
    }
  },

  inspectPrompt(versionId) {
    const ver = this.versions.find(v => v.id === versionId);
    if (!ver) return;

    this.selectedVersion = ver;
    const promptInput = document.getElementById("cust-system-prompt");
    if (promptInput) {
      promptInput.value = ver.system_prompt || "";
    }

    const tagElem = document.getElementById("prompt-version-tag");
    if (tagElem) {
      tagElem.textContent = `${ver.name || ver.version_tag} (v${ver.version_number})`;
    }

    const pillElem = document.getElementById("prompt-live-tag-pill");
    if (pillElem) {
      if (ver.status === "active") {
        pillElem.textContent = "ACTIVE LIVE";
        pillElem.className = "version-pill-badge live";
      } else {
        pillElem.textContent = (ver.status || "DRAFT").toUpperCase();
        pillElem.className = `version-pill-badge ${ver.status === "draft" ? "draft" : ""}`;
      }
    }

    this.switchTab("prompt");
  },

  async duplicateVersion(versionId) {
    try {
      const resp = await fetch(`/api/agents/${this.agentId}/versions/${versionId}/duplicate`, {
        method: "POST"
      });
      if (resp.ok) {
        await this.loadVersions();
      } else {
        alert("Failed to duplicate version.");
      }
    } catch (e) {
      console.error("Duplicate error:", e);
    }
  },

  async deleteVersion(versionId) {
    const ver = this.versions.find(v => v.id === versionId);
    if (!ver) return;
    if (ver.status === "active") {
      alert("Cannot delete the active live version. Activate another version first.");
      return;
    }
    const tag = ver.name || ver.version_tag || `v${ver.version_number}`;
    if (!confirm(`Permanently delete "${tag}"?`)) return;

    try {
      const resp = await fetch(`/api/agents/${this.agentId}/versions/${versionId}`, {
        method: "DELETE"
      });
      if (resp.ok) {
        await this.loadVersions();
      } else {
        const err = await resp.json();
        alert(`Delete failed: ${err.detail || "Server error"}`);
      }
    } catch (e) {
      console.error("Delete version error:", e);
    }
  },

  async createDraftVersion() {
    const verNum = this.versions.length + 1;
    const basePrompt = this.liveActiveVersion?.system_prompt || "You are Alex, an elite consultative closer for enterprise SaaS.";
    const payload = {
      name: `Custom Sales Closer (v${verNum})`,
      agent_role: "Elite Sales Specialist",
      sales_objective: "Qualify prospect needs and secure discovery calls",
      personality: "Authoritative, empathetic, highly articulate",
      tone: "consultative",
      system_prompt: basePrompt,
      change_notes: "Draft version created from Support & Prompts studio"
    };

    try {
      const resp = await fetch(`/api/agents/${this.agentId}/versions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        await this.loadVersions();
      } else {
        alert("Could not create new draft version.");
      }
    } catch (e) {
      console.error("Create draft error:", e);
    }
  },

  async generateAiStrategy() {
    const input = document.getElementById("modal-ai-instruction");
    const instruction = input?.value?.trim();
    if (!instruction) {
      alert("Please describe the desired sales behavior.");
      return;
    }

    const btn = document.getElementById("modal-btn-ai-gen");
    if (btn) btn.innerHTML = `<span>Enhancing...</span>`;

    try {
      const resp = await fetch(`/api/agents/${this.agentId}/generate-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction })
      });
      if (!resp.ok) throw new Error("AI generation failed");
      const data = await resp.json();
      const cfg = data.config || {};

      // Fill in prompt tab with generated prompt
      const promptInput = document.getElementById("cust-system-prompt");
      if (promptInput) {
        promptInput.value = cfg.system_prompt || "";
      }

      const tagElem = document.getElementById("prompt-version-tag");
      if (tagElem) {
        tagElem.textContent = `AI Generated: ${cfg.name || "Custom Strategy"}`;
      }

      this.switchTab("prompt");
      input.value = "";
    } catch (e) {
      console.error("AI gen error:", e);
      alert("AI enhancement failed. Using default template.");
    } finally {
      if (btn) btn.innerHTML = `<i data-lucide="sparkles" style="width: 12px; height: 12px;"></i><span>AI Enhance</span>`;
      if (window.lucide) window.lucide.createIcons();
    }
  },

  applyPromptToActiveCall() {
    const promptText = document.getElementById("cust-system-prompt")?.value?.trim();
    if (!promptText) {
      alert("Prompt cannot be empty.");
      return;
    }
    window.AppState.customSystemPrompt = promptText;
    const roleStatus = document.getElementById("bot-role-status");
    if (roleStatus) {
      roleStatus.innerHTML = `<span class="status-dot-pulse"></span> Custom Prompt Override Active`;
    }
    alert("Custom prompt applied to incoming sales calls!");
    this.closeModal();
  },

  async savePromptAsNewDraft() {
    const promptText = document.getElementById("cust-system-prompt")?.value?.trim();
    if (!promptText) {
      alert("Prompt cannot be empty.");
      return;
    }
    const verNum = this.versions.length + 1;
    const payload = {
      name: `Tuned Closer Persona (v${verNum})`,
      agent_role: "SaaS Account Executive",
      sales_objective: "Book pipeline discovery meetings",
      personality: "Persuasive, analytical, objection-handling specialist",
      system_prompt: promptText,
      change_notes: "Prompt updated and saved from Support & Prompts studio"
    };

    try {
      const resp = await fetch(`/api/agents/${this.agentId}/versions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        alert(`Saved as new Version v${verNum}!`);
        await this.loadVersions();
        this.switchTab("versions");
      } else {
        alert("Failed to save version draft.");
      }
    } catch (e) {
      console.error("Save draft error:", e);
    }
  },

  resetPrompt() {
    if (this.selectedVersion) {
      document.getElementById("cust-system-prompt").value = this.selectedVersion.system_prompt || "";
    } else if (this.liveActiveVersion) {
      document.getElementById("cust-system-prompt").value = this.liveActiveVersion.system_prompt || "";
    } else {
      document.getElementById("cust-system-prompt").value = "";
    }
  },

  resetDefaults() {
    document.getElementById("cust-prod-name").value = "";
    document.getElementById("cust-prod-tagline").value = "";
    document.getElementById("cust-prod-desc").value = "";
    document.getElementById("cust-prod-monthly").value = "49";
    document.getElementById("cust-prod-annual").value = "39";
    document.getElementById("cust-prod-features").value = "";
    document.getElementById("cust-system-prompt").value = "";

    window.AppState.customSystemPrompt = null;
    window.AppState.customProductData = null;
    alert("Studio reset to catalog defaults.");
  },

  async saveConfiguration() {
    const nameInput = document.getElementById("cust-prod-name");
    const name = nameInput ? nameInput.value.trim() : "";
    const promptInput = document.getElementById("cust-system-prompt");
    const promptText = promptInput ? promptInput.value.trim() : "";

    if (!name) {
      alert("Please provide a product name.");
      return;
    }

    const tagline = document.getElementById("cust-prod-tagline")?.value.trim() || "";
    const description = document.getElementById("cust-prod-desc")?.value.trim() || "";
    const pricing_monthly = parseFloat(document.getElementById("cust-prod-monthly")?.value) || 49;
    const pricing_annual = parseFloat(document.getElementById("cust-prod-annual")?.value) || 39;
    const featuresRaw = document.getElementById("cust-prod-features")?.value.trim() || "";
    const key_features = featuresRaw ? featuresRaw.split(",").map(s => s.trim()) : [];

    const productPayload = {
      name,
      tagline,
      description,
      pricing_monthly,
      pricing_annual,
      key_features,
      target_audience: "Businesses seeking growth",
      custom_system_prompt: promptText || null
    };

    try {
      const resp = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(productPayload)
      });
      if (resp.ok) {
        window.AppState.customProductData = productPayload;
        window.AppState.customSystemPrompt = promptText || null;

        if (window.App && window.App.loadProducts) {
          await window.App.loadProducts(name);
        }
        this.closeModal();
      } else {
        alert("Failed to save product to database.");
      }
    } catch (e) {
      console.error("Save product error:", e);
      alert("Network error saving product.");
    }
  }
};
