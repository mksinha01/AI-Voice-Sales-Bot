/**
 * static/js/persona-control.js
 * Production-grade AI Sales Agent Configuration and Version Control Platform Controller.
 */

const PersonaControl = {
  agents: [],
  activeAgent: null,
  versions: [],
  currentVersion: null,
  liveActiveVersion: null,
  allTools: [],
  activeTab: "persona",
  isDirty: false,
  isCallActive: false,
  callTimerInterval: null,
  callSeconds: 0,

  async init() {
    this.bindEvents();
    await this.loadTools();
    await this.loadAgents();
    if (window.lucide) window.lucide.createIcons();
  },

  bindEvents() {
    // Agent dropdown
    document.getElementById("agent-select")?.addEventListener("change", (e) => {
      this.switchAgent(e.target.value);
    });

    // Strategy Generator Box
    document.getElementById("btn-ai-generate")?.addEventListener("click", () => {
      this.generateFromPrompt();
    });
    document.getElementById("ai-instruction-input")?.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.generateFromPrompt();
      }
    });

    // Version Actions
    document.getElementById("btn-new-draft")?.addEventListener("click", () => this.createNewDraft());
    document.getElementById("btn-duplicate-version")?.addEventListener("click", () => this.duplicateCurrentVersion());
    document.getElementById("btn-save-draft")?.addEventListener("click", () => this.saveCurrentDraft());
    document.getElementById("btn-publish-version")?.addEventListener("click", () => this.publishCurrentVersion());
    document.getElementById("btn-activate-version")?.addEventListener("click", () => this.activateCurrentVersion());
    document.getElementById("btn-rollback-version")?.addEventListener("click", () => this.rollbackToCurrentVersion());
    document.getElementById("btn-delete-version")?.addEventListener("click", () => this.deleteCurrentVersion());
    document.getElementById("btn-open-compare")?.addEventListener("click", () => this.openCompareModal());

    // Section Tabs
    document.querySelectorAll(".builder-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        this.switchSectionTab(tab);
      });
    });

    // Recompile Prompt button
    document.getElementById("btn-recompile-prompt")?.addEventListener("click", () => {
      this.recompilePromptFromFields();
    });

    // Temperature slider readout
    document.getElementById("cfg-model-temp")?.addEventListener("input", (e) => {
      const readout = document.getElementById("temp-readout");
      if (readout) readout.textContent = parseFloat(e.target.value).toFixed(2);
      this.markDirty();
    });

    // Input change dirty tracker
    const form = document.getElementById("builder-form");
    form?.addEventListener("input", () => this.markDirty());
    form?.addEventListener("change", () => this.markDirty());

    // Compare Modal Controls
    document.getElementById("btn-close-compare")?.addEventListener("click", () => this.closeCompareModal());
    document.getElementById("compare-v1-select")?.addEventListener("change", () => this.runComparison());
    document.getElementById("compare-v2-select")?.addEventListener("change", () => this.runComparison());

    // Test Voice Call Controls
    document.getElementById("btn-toggle-test-cockpit")?.addEventListener("click", () => this.toggleTestCockpit());
    document.getElementById("btn-close-cockpit")?.addEventListener("click", () => this.closeTestCockpit());
    document.getElementById("btn-start-test-call")?.addEventListener("click", () => this.toggleVoiceCall());
  },

  markDirty() {
    if (this.currentVersion && this.currentVersion.status === "draft") {
      this.isDirty = true;
      const indicator = document.getElementById("unsaved-indicator");
      if (indicator) indicator.style.display = "inline-flex";
    }
  },

  clearDirty() {
    this.isDirty = false;
    const indicator = document.getElementById("unsaved-indicator");
    if (indicator) indicator.style.display = "none";
  },

  async loadTools() {
    try {
      const resp = await fetch("/api/tools");
      const data = await resp.json();
      this.allTools = data.tools || [];
      this.renderToolsMatrix([]);
    } catch (e) {
      console.warn("Failed to load tools registry:", e);
    }
  },

  renderToolsMatrix(activePermissions = []) {
    const container = document.getElementById("tools-checkbox-grid");
    if (!container) return;

    container.innerHTML = this.allTools.map((t) => {
      const isChecked = activePermissions.includes(t.id) ? "checked" : "";
      return `
        <label class="tool-perm-card ${isChecked ? 'selected' : ''}">
          <input type="checkbox" name="tool_perm" value="${t.id}" ${isChecked}>
          <div class="tool-perm-body">
            <div class="tool-perm-header">
              <span class="tool-perm-label">${t.label}</span>
              <span class="tool-perm-cat">${t.category}</span>
            </div>
            <p class="tool-perm-desc">${t.description}</p>
          </div>
        </label>
      `;
    }).join("");

    container.querySelectorAll("input[type='checkbox']").forEach((cb) => {
      cb.addEventListener("change", (e) => {
        const card = e.target.closest(".tool-perm-card");
        if (card) {
          if (e.target.checked) card.classList.add("selected");
          else card.classList.remove("selected");
        }
        this.markDirty();
      });
    });
  },

  async loadAgents() {
    try {
      const resp = await fetch("/api/agents");
      const data = await resp.json();
      this.agents = data.agents || [];
      const select = document.getElementById("agent-select");
      if (select && this.agents.length > 0) {
        select.innerHTML = this.agents.map((a) => `
          <option value="${a.id}">${a.name}</option>
        `).join("");
        await this.switchAgent(this.agents[0].id);
      }
    } catch (e) {
      console.error("Failed to load agents:", e);
    }
  },

  async switchAgent(agentId) {
    this.activeAgent = this.agents.find((a) => a.id === agentId) || null;
    await this.loadVersions(agentId);
  },

  async loadVersions(agentId) {
    try {
      const resp = await fetch(`/api/agents/${agentId}/versions`);
      const data = await resp.json();
      this.versions = data.versions || [];

      // Find currently active live version
      this.liveActiveVersion = this.versions.find((v) => v.status === "active") || this.versions[0] || null;
      this.renderLiveBadge();

      // Render version selector ribbon
      this.renderVersionRibbon();

      // If active version exists, select it by default
      const defaultToSelect = this.liveActiveVersion || this.versions[0];
      if (defaultToSelect) {
        await this.selectVersion(defaultToSelect.id);
      }
    } catch (e) {
      console.error("Failed to load versions:", e);
    }
  },

  renderLiveBadge() {
    const badge = document.getElementById("live-version-badge");
    const label = document.getElementById("live-version-text");
    if (!badge || !label) return;

    if (this.liveActiveVersion) {
      label.textContent = `LIVE: ${this.liveActiveVersion.version_tag} (v${this.liveActiveVersion.version_number})`;
      badge.style.display = "inline-flex";
    } else {
      label.textContent = "No Live Version Active";
      badge.style.display = "inline-flex";
    }
  },

  renderVersionRibbon() {
    const container = document.getElementById("version-tabs-ribbon");
    if (!container) return;

    container.innerHTML = this.versions.map((v) => {
      const isSelected = this.currentVersion && this.currentVersion.id === v.id;
      const isLive = v.status === "active";
      let statusClass = "draft";
      if (v.status === "active") statusClass = "active";
      else if (v.status === "published") statusClass = "published";

      return `
        <button class="version-tab-pill ${isSelected ? 'selected' : ''} ${statusClass}"
          onclick="PersonaControl.selectVersion('${v.id}')"
          title="${v.sales_objective}">
          <span class="v-pill-num">v${v.version_number}</span>
          <span class="v-pill-tag">${v.version_tag || 'Strategy'}</span>
          <span class="v-pill-status">${isLive ? 'LIVE' : v.status}</span>
        </button>
      `;
    }).join("");

    if (window.lucide) window.lucide.createIcons();
  },

  async selectVersion(versionId) {
    if (this.isDirty && this.currentVersion && this.currentVersion.status === "draft") {
      const confirmDiscard = confirm("You have unsaved edits on the current draft. Switch anyway?");
      if (!confirmDiscard) return;
    }

    try {
      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions/${versionId}`);
      if (!resp.ok) throw new Error("Could not fetch version");
      const data = await resp.json();
      this.currentVersion = data.version;
      this.clearDirty();
      this.renderVersionRibbon();
      this.populateForm(this.currentVersion);
      this.updateActionBar(this.currentVersion);
    } catch (e) {
      console.error("Failed to select version:", e);
    }
  },

  populateForm(v) {
    const persona = v.persona || {};
    const customer = v.customer_profile || {};
    const knowledge = v.knowledge_config || {};
    const workflow = v.sales_workflow || {};
    const model = v.model_config || {};

    // 1. Identity & Persona
    this.setVal("cfg-persona-name", persona.name || "Alex Closer");
    this.setVal("cfg-persona-role", persona.role || "Senior Sales Closer");
    this.setVal("cfg-persona-tone", persona.tone || "Consultative, persuasive");
    this.setVal("cfg-persona-lang", persona.language || "en-US");
    this.setVal("cfg-persona-greeting", persona.greeting || "");
    this.setVal("cfg-sales-objective", v.sales_objective || "");
    this.setVal("cfg-customer-icp", customer.icp || "");
    this.setVal("cfg-customer-pain", customer.pain_points || "");

    // 2. System Prompt
    const promptArea = document.getElementById("cfg-system-prompt");
    if (promptArea) {
      promptArea.value = v.system_prompt || v.compiled_prompt_preview || "";
      this.updatePromptMetrics();
    }

    // 3. Knowledge & Commercials
    const prods = knowledge.products || [];
    this.setVal("cfg-products-list", Array.isArray(prods) ? prods.join(", ") : String(prods));
    this.setVal("cfg-price-monthly", knowledge.pricing_monthly ?? 49);
    this.setVal("cfg-price-annual", knowledge.pricing_annual ?? 39);
    const offers = knowledge.approved_offers || [];
    this.setVal("cfg-approved-offers", Array.isArray(offers) ? offers.join("; ") : String(offers));
    const faqs = knowledge.faqs || {};
    this.setVal("cfg-faqs-text", typeof faqs === "object" ? JSON.stringify(faqs, null, 2) : String(faqs));

    // 4. Sales Workflow & Objections
    const stages = workflow.stages || [];
    this.setVal("cfg-workflow-stages", Array.isArray(stages) ? stages.join(" -> ") : String(stages));
    const questions = workflow.qualification_questions || [];
    this.setVal("cfg-qual-questions", Array.isArray(questions) ? questions.join("\n") : String(questions));
    this.setVal("cfg-closing-strategy", workflow.closing_strategy || "");
    this.setVal("cfg-escalation-rules", workflow.escalation_rules || "");

    // 5. Tools Permissions
    this.renderToolsMatrix(v.tool_permissions || []);

    // 6. Model & Voice Settings
    this.setVal("cfg-model-provider", model.provider || "google");
    this.setVal("cfg-model-name", model.model_name || "gemini-2.0-flash");
    const temp = model.temperature ?? 0.3;
    this.setVal("cfg-model-temp", temp);
    const readout = document.getElementById("temp-readout");
    if (readout) readout.textContent = parseFloat(temp).toFixed(2);
    this.setVal("cfg-tts-voice", model.voice_id || "en-US-GuyNeural");

    // Version Tag input
    this.setVal("current-version-tag-input", v.version_tag || "");

    // Handle Immutability Display
    this.applyImmutabilityLock(v.status !== "draft");
  },

  applyImmutabilityLock(isLocked) {
    const banner = document.getElementById("immutability-notice-banner");
    if (banner) banner.style.display = isLocked ? "flex" : "none";

    const form = document.getElementById("builder-form");
    if (!form) return;

    // Toggle disabled state on all form elements except version tag for drafts
    form.querySelectorAll("input, textarea, select, button").forEach((el) => {
      if (el.id === "btn-recompile-prompt") return;
      el.disabled = isLocked;
    });
  },

  updateActionBar(v) {
    const tagDisplay = document.getElementById("version-header-title");
    const statusPill = document.getElementById("version-status-pill");
    const btnSave = document.getElementById("btn-save-draft");
    const btnPublish = document.getElementById("btn-publish-version");
    const btnActivate = document.getElementById("btn-activate-version");
    const btnDuplicate = document.getElementById("btn-duplicate-version");
    const btnRollback = document.getElementById("btn-rollback-version");
    const btnDelete = document.getElementById("btn-delete-version");

    if (tagDisplay) {
      tagDisplay.textContent = `v${v.version_number}: ${v.version_tag}`;
    }

    if (statusPill) {
      statusPill.className = `status-pill-badge ${v.status}`;
      statusPill.textContent = v.status.toUpperCase();
    }

    // Live active versions cannot be deleted to ensure system integrity
    if (btnDelete) {
      btnDelete.disabled = (v.status === "active");
      btnDelete.style.opacity = (v.status === "active") ? "0.4" : "1";
      btnDelete.title = (v.status === "active") ? "Active live version cannot be deleted" : "Delete this version";
    }

    if (v.status === "draft") {
      if (btnSave) btnSave.disabled = false;
      if (btnPublish) btnPublish.disabled = false;
      if (btnActivate) btnActivate.disabled = false;
      if (btnDuplicate) btnDuplicate.disabled = false;
      if (btnRollback) btnRollback.disabled = true;
    } else if (v.status === "active") {
      if (btnSave) btnSave.disabled = true;
      if (btnPublish) btnPublish.disabled = true;
      if (btnActivate) btnActivate.disabled = true;
      if (btnDuplicate) btnDuplicate.disabled = false;
      if (btnRollback) btnRollback.disabled = false;
    } else {
      // published
      if (btnSave) btnSave.disabled = true;
      if (btnPublish) btnPublish.disabled = true;
      if (btnActivate) btnActivate.disabled = false;
      if (btnDuplicate) btnDuplicate.disabled = false;
      if (btnRollback) btnRollback.disabled = false;
    }
  },

  collectFormData() {
    const selectedTools = [];
    document.querySelectorAll("input[name='tool_perm']:checked").forEach((cb) => {
      selectedTools.push(cb.value);
    });

    let faqsObj = {};
    try {
      const faqsRaw = this.getVal("cfg-faqs-text");
      faqsObj = faqsRaw ? JSON.parse(faqsRaw) : {};
    } catch {
      faqsObj = { "General Inquiry": "Contact sales team." };
    }

    const products = this.getVal("cfg-products-list").split(",").map(p => p.trim()).filter(Boolean);
    const offers = this.getVal("cfg-approved-offers").split(";").map(o => o.trim()).filter(Boolean);
    const stages = this.getVal("cfg-workflow-stages").split("->").map(s => s.trim()).filter(Boolean);
    const questions = this.getVal("cfg-qual-questions").split("\n").map(q => q.trim()).filter(Boolean);

    return {
      version_tag: this.getVal("current-version-tag-input"),
      system_prompt: this.getVal("cfg-system-prompt"),
      sales_objective: this.getVal("cfg-sales-objective"),
      persona: {
        name: this.getVal("cfg-persona-name"),
        role: this.getVal("cfg-persona-role"),
        tone: this.getVal("cfg-persona-tone"),
        language: this.getVal("cfg-persona-lang"),
        greeting: this.getVal("cfg-persona-greeting")
      },
      customer_profile: {
        icp: this.getVal("cfg-customer-icp"),
        pain_points: this.getVal("cfg-customer-pain")
      },
      knowledge_config: {
        products: products.length > 0 ? products : ["CloudScale CRM"],
        pricing_monthly: parseFloat(this.getVal("cfg-price-monthly")) || 49,
        pricing_annual: parseFloat(this.getVal("cfg-price-annual")) || 39,
        approved_offers: offers,
        faqs: faqsObj
      },
      sales_workflow: {
        stages: stages.length > 0 ? stages : ["Greeting", "Discovery", "Pitch", "Close"],
        qualification_questions: questions,
        closing_strategy: this.getVal("cfg-closing-strategy"),
        escalation_rules: this.getVal("cfg-escalation-rules")
      },
      tool_permissions: selectedTools,
      model_config: {
        provider: this.getVal("cfg-model-provider") || "google",
        model_name: this.getVal("cfg-model-name") || "gemini-2.0-flash",
        temperature: parseFloat(this.getVal("cfg-model-temp")) || 0.3,
        voice_id: this.getVal("cfg-tts-voice") || "en-US-GuyNeural"
      }
    };
  },

  async saveCurrentDraft() {
    if (!this.currentVersion || this.currentVersion.status !== "draft") return;

    try {
      const payload = this.collectFormData();
      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions/${this.currentVersion.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const err = await resp.json();
        alert(`Error saving draft: ${err.detail || "Validation failed"}`);
        return;
      }

      const data = await resp.json();
      this.currentVersion = data.version;
      this.clearDirty();
      await this.loadVersions(this.activeAgent.id);
      this.populateForm(this.currentVersion);
      this.showToast("Draft saved successfully!");
    } catch (e) {
      console.error("Save error:", e);
      alert("Failed to save draft.");
    }
  },

  async publishCurrentVersion() {
    if (!this.currentVersion || this.currentVersion.status !== "draft") return;

    const confirmPublish = confirm("Publishing locks this version into an immutable state. You will not be able to edit it directly. Proceed?");
    if (!confirmPublish) return;

    try {
      // Auto-save first
      await this.saveCurrentDraft();

      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions/${this.currentVersion.id}/publish`, {
        method: "POST"
      });
      if (!resp.ok) throw new Error("Publish failed");
      const data = await resp.json();
      this.currentVersion = data.version;
      await this.loadVersions(this.activeAgent.id);
      this.populateForm(this.currentVersion);
      this.showToast("Version published! It is now locked and immutable.");
    } catch (e) {
      console.error("Publish error:", e);
      alert("Could not publish version.");
    }
  },

  async activateCurrentVersion() {
    if (!this.currentVersion) return;

    const confirmActivate = confirm(`Activate ${this.currentVersion.version_tag} as the LIVE voice sales agent? New voice sessions will immediately use this configuration.`);
    if (!confirmActivate) return;

    try {
      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions/${this.currentVersion.id}/activate`, {
        method: "POST"
      });
      if (!resp.ok) throw new Error("Activation failed");
      const data = await resp.json();
      this.currentVersion = data.version;
      await this.loadVersions(this.activeAgent.id);
      this.populateForm(this.currentVersion);
      this.showToast(`Active Live Version updated to ${this.currentVersion.version_tag}!`);
    } catch (e) {
      console.error("Activation error:", e);
      alert("Could not activate version.");
    }
  },

  async createNewDraft() {
    try {
      const template = {
        version_tag: `New Custom Strategy (${new Date().toLocaleDateString()})`,
        sales_objective: "Qualify inbound prospects and secure live demo walkthroughs.",
        persona: {
          name: "Alex Closer",
          role: "SaaS Solutions Specialist",
          tone: "Consultative, persuasive",
          language: "en-US",
          greeting: "Hello! Alex here from CloudScale. How are you handling sales pipeline automation today?"
        },
        customer_profile: {
          icp: "B2B SaaS Growth Leaders",
          pain_points: "Manual reporting, missed follow-ups"
        },
        knowledge_config: {
          products: ["CloudScale CRM Growth"],
          pricing_monthly: 49,
          pricing_annual: 39,
          approved_offers: ["20% annual discount applied instantly"],
          faqs: { "How long is setup?": "Under 48 hours." }
        },
        sales_workflow: {
          stages: ["Greeting", "Discovery", "Value Pitch", "Objection Handling", "Closing Demo"],
          qualification_questions: ["What is your sales team size?", "What CRM do you run on today?"],
          closing_strategy: "Book a 15-minute product demonstration",
          escalation_rules: "Transfer to Human AE if custom terms are needed"
        },
        tool_permissions: ["schedule_demo", "check_pricing_tier", "record_objection", "end_call"],
        model_config: {
          provider: "google",
          model_name: "gemini-2.0-flash",
          temperature: 0.3,
          voice_id: "en-US-GuyNeural"
        },
        as_draft: true
      };

      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(template)
      });
      const data = await resp.json();
      await this.loadVersions(this.activeAgent.id);
      await this.selectVersion(data.version.id);
      this.showToast("New draft version created!");
    } catch (e) {
      console.error("Create draft error:", e);
    }
  },

  async duplicateCurrentVersion() {
    if (!this.currentVersion) return;
    try {
      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions/${this.currentVersion.id}/duplicate`, {
        method: "POST"
      });
      const data = await resp.json();
      await this.loadVersions(this.activeAgent.id);
      await this.selectVersion(data.version.id);
      this.showToast(`Duplicated ${this.currentVersion.version_tag} into a new draft!`);
    } catch (e) {
      console.error("Duplicate error:", e);
    }
  },

  async rollbackToCurrentVersion() {
    if (!this.currentVersion) return;
    const confirmRollback = confirm(`Roll back configuration to ${this.currentVersion.version_tag}? This creates a fresh editable draft populated with this exact version.`);
    if (!confirmRollback) return;

    try {
      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions/${this.currentVersion.id}/rollback`, {
        method: "POST"
      });
      const data = await resp.json();
      await this.loadVersions(this.activeAgent.id);
      await this.selectVersion(data.version.id);
      this.showToast(`Rollback draft created from v${this.currentVersion.version_number}!`);
    } catch (e) {
      console.error("Rollback error:", e);
    }
  },

  async deleteCurrentVersion() {
    if (!this.currentVersion) return;
    if (this.currentVersion.status === "active") {
      alert("Cannot delete the active live version. Please deploy another version first.");
      return;
    }

    const tag = this.currentVersion.version_tag || `v${this.currentVersion.version_number}`;
    const confirmed = confirm(`Are you sure you want to permanently delete "${tag}"?`);
    if (!confirmed) return;

    try {
      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions/${this.currentVersion.id}`, {
        method: "DELETE"
      });
      if (!resp.ok) {
        const err = await resp.json();
        alert(`Delete failed: ${err.detail || "Server error"}`);
        return;
      }
      this.showToast(`Deleted ${tag} successfully.`);
      await this.loadVersions(this.activeAgent.id);
    } catch (e) {
      console.error("Delete version error:", e);
      alert("Network error deleting version.");
    }
  },

  async generateFromPrompt() {
    const input = document.getElementById("ai-instruction-input");
    const btn = document.getElementById("btn-ai-generate");
    if (!input || !input.value.trim()) return;

    const instruction = input.value.trim();
    btn.disabled = true;
    btn.textContent = "Synthesizing Strategy...";

    try {
      const resp = await fetch("/api/ai/generate-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction })
      });

      if (!resp.ok) throw new Error("Generation failed");
      const data = await resp.json();
      const cfg = data.generated_config;

      // Populate draft form for review
      if (this.currentVersion && this.currentVersion.status === "draft") {
        this.applyGeneratedConfig(cfg);
        this.showToast("AI Strategy applied to draft! Review and save.");
      } else {
        // Create new draft with this config
        cfg.as_draft = true;
        const createResp = await fetch(`/api/agents/${this.activeAgent.id}/versions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cfg)
        });
        const createdData = await createResp.json();
        await this.loadVersions(this.activeAgent.id);
        await this.selectVersion(createdData.version.id);
        this.showToast("Created new draft with AI generated strategy!");
      }
      input.value = "";
    } catch (e) {
      console.error("Generation error:", e);
      alert("Could not generate strategy from prompt.");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="sparkles" style="width: 14px; height: 14px;"></i><span>AI Generate / Enhance</span>`;
      if (window.lucide) window.lucide.createIcons();
    }
  },

  applyGeneratedConfig(cfg) {
    if (cfg.version_tag) this.setVal("current-version-tag-input", cfg.version_tag);
    if (cfg.sales_objective) this.setVal("cfg-sales-objective", cfg.sales_objective);
    if (cfg.persona) {
      this.setVal("cfg-persona-name", cfg.persona.name || "Alex Closer");
      this.setVal("cfg-persona-role", cfg.persona.role || "Sales Closer");
      this.setVal("cfg-persona-tone", cfg.persona.tone || "Assertive");
      this.setVal("cfg-persona-greeting", cfg.persona.greeting || "");
    }
    if (cfg.customer_profile) {
      this.setVal("cfg-customer-icp", cfg.customer_profile.icp || "");
      this.setVal("cfg-customer-pain", cfg.customer_profile.pain_points || "");
    }
    if (cfg.knowledge_config) {
      this.setVal("cfg-products-list", (cfg.knowledge_config.products || []).join(", "));
      this.setVal("cfg-price-monthly", cfg.knowledge_config.pricing_monthly || 49);
      this.setVal("cfg-price-annual", cfg.knowledge_config.pricing_annual || 39);
      this.setVal("cfg-approved-offers", (cfg.knowledge_config.approved_offers || []).join("; "));
    }
    if (cfg.sales_workflow) {
      this.setVal("cfg-workflow-stages", (cfg.sales_workflow.stages || []).join(" -> "));
      this.setVal("cfg-qual-questions", (cfg.sales_workflow.qualification_questions || []).join("\n"));
      this.setVal("cfg-closing-strategy", cfg.sales_workflow.closing_strategy || "");
      this.setVal("cfg-escalation-rules", cfg.sales_workflow.escalation_rules || "");
    }
    if (cfg.tool_permissions) {
      this.renderToolsMatrix(cfg.tool_permissions);
    }
    this.recompilePromptFromFields();
    this.markDirty();
  },

  recompilePromptFromFields() {
    const data = this.collectFormData();
    const promptArea = document.getElementById("cfg-system-prompt");
    if (!promptArea) return;

    const prods = data.knowledge_config.products.join(", ");
    const qual = data.sales_workflow.qualification_questions.map(q => `- ${q}`).join("\n");
    const tools = data.tool_permissions.join(", ");

    const compiled = `You are ${data.persona.name}, an elite ${data.persona.role}.
Primary Sales Objective: ${data.sales_objective}

Persona & Speaking Style:
- Tone: ${data.persona.tone}
- Language Guidance: Speak naturally, with concise turns (1 to 3 short sentences max). Never monologue.

Target Customer & ICP:
- Target Customer: ${data.customer_profile.icp}
- Core Pain Points: ${data.customer_profile.pain_points}

Approved Knowledge & Commercials:
- Approved Solutions: ${prods}
- Standard Pricing: $${data.knowledge_config.pricing_annual}/user/month (annual) or $${data.knowledge_config.pricing_monthly}/user/month (monthly).
- Approved Offers: ${data.knowledge_config.approved_offers.join("; ")}

Sales Workflow:
- Execution Stages: ${data.sales_workflow.stages.join(" -> ")}
- Core Qualification Questions:
${qual}
- Closing Strategy: ${data.sales_workflow.closing_strategy}
- Escalation Rules: ${data.sales_workflow.escalation_rules}

Permitted Integration Tools:
Authorized tools: ${tools}

Strict Commercial Guardrails:
1. Never hallucinate unauthorized pricing, terms, or discounts.
2. In case of customer farewell or exit, invoke end_call immediately and offer a warm one-sentence goodbye.`;

    promptArea.value = compiled.trim();
    this.updatePromptMetrics();
    this.markDirty();
  },

  updatePromptMetrics() {
    const area = document.getElementById("cfg-system-prompt");
    const countSpan = document.getElementById("prompt-char-count");
    if (area && countSpan) {
      const len = area.value.length;
      const tokens = Math.round(len / 4);
      countSpan.textContent = `${len.toLocaleString()} chars (~${tokens} tokens)`;
    }
  },

  switchSectionTab(tabName) {
    this.activeTab = tabName;
    document.querySelectorAll(".builder-tab-btn").forEach((btn) => {
      if (btn.getAttribute("data-tab") === tabName) btn.classList.add("active");
      else btn.classList.remove("active");
    });

    document.querySelectorAll(".builder-pane").forEach((pane) => {
      if (pane.id === `pane-${tabName}`) pane.classList.add("active");
      else pane.classList.remove("active");
    });
  },

  // ── Version Comparison Modal ──
  openCompareModal() {
    const modal = document.getElementById("compare-modal");
    const sel1 = document.getElementById("compare-v1-select");
    const sel2 = document.getElementById("compare-v2-select");
    if (!modal || !sel1 || !sel2) return;

    const options = this.versions.map((v) => `
      <option value="${v.id}">v${v.version_number} — ${v.version_tag} (${v.status})</option>
    `).join("");

    sel1.innerHTML = options;
    sel2.innerHTML = options;

    if (this.versions.length >= 2) {
      sel1.selectedIndex = 0;
      sel2.selectedIndex = 1;
    }

    modal.classList.add("open");
    this.runComparison();
  },

  closeCompareModal() {
    document.getElementById("compare-modal")?.classList.remove("open");
  },

  async runComparison() {
    const v1Id = document.getElementById("compare-v1-select")?.value;
    const v2Id = document.getElementById("compare-v2-select")?.value;
    const container = document.getElementById("compare-diff-table");
    if (!v1Id || !v2Id || !container) return;

    try {
      const resp = await fetch(`/api/agents/${this.activeAgent.id}/versions/compare?v1=${v1Id}&v2=${v2Id}`);
      const data = await resp.json();
      const diffs = data.comparison.differences;

      container.innerHTML = Object.entries(diffs).map(([field, d]) => {
        const valA = typeof d.version_a === "object" ? JSON.stringify(d.version_a, null, 1) : String(d.version_a || "-");
        const valB = typeof d.version_b === "object" ? JSON.stringify(d.version_b, null, 1) : String(d.version_b || "-");
        const isDiff = d.is_different;

        return `
          <tr class="${isDiff ? 'diff-row-changed' : 'diff-row-same'}">
            <td class="diff-field-name">
              <strong>${field.replace(/_/g, " ").toUpperCase()}</strong>
              ${isDiff ? '<span class="diff-tag-change">CHANGED</span>' : '<span class="diff-tag-same">IDENTICAL</span>'}
            </td>
            <td class="diff-val-col"><pre>${valA}</pre></td>
            <td class="diff-val-col"><pre>${valB}</pre></td>
          </tr>
        `;
      }).join("");
    } catch (e) {
      console.error("Comparison error:", e);
    }
  },

  // ── Live Voice Test Cockpit ──
  toggleTestCockpit() {
    const cockpit = document.getElementById("test-cockpit-drawer");
    if (cockpit) {
      cockpit.classList.toggle("open");
    }
  },

  closeTestCockpit() {
    document.getElementById("test-cockpit-drawer")?.classList.remove("open");
  },

  async toggleVoiceCall() {
    if (this.isCallActive) {
      await this.endVoiceCall();
    } else {
      await this.startVoiceCall();
    }
  },

  async startVoiceCall() {
    const btn = document.getElementById("btn-start-test-call");
    const statusText = document.getElementById("test-call-status-text");
    if (btn) btn.disabled = true;
    if (statusText) statusText.textContent = "Connecting to Voice Engine...";

    const versionToTest = this.currentVersion || this.liveActiveVersion;
    const agentId = this.activeAgent ? this.activeAgent.id : "agent-alex-closer";

    try {
      const tokenResp = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_id: agentId,
          version_id: versionToTest ? versionToTest.id : null,
          product_name: "CloudScale CRM",
          language: versionToTest?.persona?.language || "en-US",
          customer_name: "Test Prospect"
        })
      });

      const tokenData = await tokenResp.json();
      this.isCallActive = true;
      if (btn) {
        btn.disabled = false;
        btn.classList.add("in-call");
        btn.innerHTML = `<i data-lucide="phone-off" style="width: 14px; height: 14px;"></i><span>End Test Call</span>`;
      }
      if (statusText) {
        statusText.textContent = `Live with ${tokenData.version_tag || 'Agent'}`;
      }

      this.startCallTimer();

      // Clear transcript box
      const chatBox = document.getElementById("test-transcript-stream");
      if (chatBox) chatBox.innerHTML = `
        <div class="test-chat-msg bot">
          <div class="msg-author">AI Agent (${tokenData.version_tag || 'Live'})</div>
          <div class="msg-content">${versionToTest?.persona?.greeting || "Hello! How can I assist your sales team today?"}</div>
        </div>
      `;

      // Connect WebRTC if SDK is present
      if (window.LiveKitManager && window.LivekitClient && tokenData.livekit_url.startsWith("wss://")) {
        try {
          await LiveKitManager.connect(tokenData.livekit_url, tokenData.token, {
            onTranscript: (speaker, text) => {
              this.appendTestTranscript(speaker, text);
            },
            onDisconnect: () => {
              this.endVoiceCall();
            }
          }, tokenData.room_name);
        } catch (webrtcErr) {
          console.warn("LiveKit Cloud connection warning (running simulated session):", webrtcErr);
        }
      }

      if (window.lucide) window.lucide.createIcons();
    } catch (e) {
      console.error("Test call error:", e);
      alert("Failed to start test call.");
      if (btn) btn.disabled = false;
    }
  },

  async endVoiceCall() {
    this.isCallActive = false;
    this.stopCallTimer();

    const btn = document.getElementById("btn-start-test-call");
    const statusText = document.getElementById("test-call-status-text");
    if (btn) {
      btn.classList.remove("in-call");
      btn.innerHTML = `<i data-lucide="phone-call" style="width: 14px; height: 14px;"></i><span>Start Test Call</span>`;
    }
    if (statusText) statusText.textContent = "Test Session Concluded";

    if (window.LiveKitManager) {
      await LiveKitManager.disconnect();
    }
    if (window.lucide) window.lucide.createIcons();
  },

  startCallTimer() {
    this.callSeconds = 0;
    const timerElem = document.getElementById("test-call-timer");
    clearInterval(this.callTimerInterval);
    this.callTimerInterval = setInterval(() => {
      this.callSeconds++;
      const m = Math.floor(this.callSeconds / 60).toString().padStart(2, "0");
      const s = (this.callSeconds % 60).toString().padStart(2, "0");
      if (timerElem) timerElem.textContent = `00:${m}:${s}`;
    }, 1000);
  },

  stopCallTimer() {
    clearInterval(this.callTimerInterval);
  },

  appendTestTranscript(speaker, text) {
    const chatBox = document.getElementById("test-transcript-stream");
    if (!chatBox) return;

    const row = document.createElement("div");
    row.className = `test-chat-msg ${speaker === 'bot' ? 'bot' : 'customer'}`;
    row.innerHTML = `
      <div class="msg-author">${speaker === 'bot' ? 'AI Agent' : 'You (Customer)'}</div>
      <div class="msg-content">${text}</div>
    `;
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
  },

  showToast(msg) {
    const toast = document.getElementById("app-toast");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("visible");
    setTimeout(() => toast.classList.remove("visible"), 3200);
  },

  // Helpers
  getVal(id) {
    const el = document.getElementById(id);
    return el ? el.value : "";
  },
  setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
  }
};

window.addEventListener("DOMContentLoaded", () => {
  PersonaControl.init();
});
