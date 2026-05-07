window.addEventListener("DOMContentLoaded", () => {
  let installPrompt = null;
  let lastNativePath = window.location.pathname;
  const staticVersion = document
    .querySelector('meta[name="jobmind-static-version"]')
    ?.getAttribute("content") || "local-dev";
  const cards = document.querySelectorAll(".card");
  cards.forEach((card, index) => {
    card.animate(
      [
        { opacity: 0, transform: "translateY(10px)" },
        { opacity: 1, transform: "translateY(0)" }
      ],
      {
        duration: 320,
        delay: index * 50,
        fill: "forwards",
        easing: "ease-out"
      }
    );
  });

  const installButton = document.querySelector('[data-role="install-app"]');
  const capacitorApp = window.Capacitor?.Plugins?.App;
  const modeToggles = document.querySelectorAll('[data-role="mode-toggle"]');
  const modeShells = document.querySelectorAll('[data-role="mode-shell"]');
  const modeSummaryCards = document.querySelectorAll('[data-role="mode-summary-card"]');
  const spotlightTitle = document.querySelector('[data-role="mode-spotlight-title"]');
  const spotlightDescription = document.querySelector('[data-role="mode-spotlight-description"]');
  const staleResultsNotes = document.querySelectorAll('[data-role="stale-results-note"]');
  const liveResultsContent = document.querySelectorAll('[data-role="results-live-content"]');
  const submitFeedbackNodes = document.querySelectorAll('[data-role="submit-feedback"]');
  const jobForm = document.querySelector('[data-role="job-form"]');
  const sellForm = document.querySelector('[data-role="sell-form"]');
  const currentPath = window.location.pathname;
  const currentQuery = new URLSearchParams(window.location.search);
  const sellSearchModes = new Set(["sell_services", "sell_products", "direct_clients"]);
  const serverResultMode = sellSearchModes.has(currentQuery.get("search_mode")) ? "sell" : "job";
  const initialMode = currentQuery.get("active_mode") || serverResultMode;
  const modeMeta = {
    job: {
      title: "Job Search Mode",
      description: "Find remote Python and backend roles with job-only filters, match cards, and application tracking."
    },
    sell: {
      title: "Sell Services Mode",
      description: "Prospect buyers for your residency management software or dev services with client-only tools and lead tracking."
    }
  };

  const submitMeta = {
    job: {
      idleLabel: "Run Job Search",
      busyLabel: "Searching Jobs...",
      feedback: "Job search is starting. On Render this can take a few seconds if the app was sleeping."
    },
    sell: {
      idleLabel: "Run Client Search",
      busyLabel: "Searching Clients...",
      feedback: "Client search is starting. On Render this can take a few seconds if the app was sleeping."
    }
  };

  const storageKeys = {
    uiMode: "jobmind.activeMode.v2",
    modeState: "jobmind.modeState.v2",
    presets: "jobmind.modePresets.v2",
    trackers: "jobmind.modeTrackers.v2"
  };

  const formConfig = {
    job: {
      mode: "job",
      form: jobForm,
      sourceSelector: '[data-role="job-source-option"]',
      platformSelector: '[data-role="job-platform-option"]',
      sourceInput: jobForm?.querySelector('[data-role="source-input"]') || null,
      platformInput: jobForm?.querySelector('[data-role="platform-targets"]') || null,
      filterOverview: document.querySelector('[data-role="job-filter-overview"]'),
      defaults: {
        search_mode: "job_search",
        offer_type: "software",
        client_type: "startup",
        contact_goal: "apply",
        counterparty_type: "any",
        company_size: "any",
        proposal_pressure: "any",
        search_focus: "python",
        region_preference: "global",
        trust_signal: "verified_company",
        posted_within: "7d",
        demand_level: "latest",
        min_match_level: "all",
        custom_keywords: "",
        sources: "remotive,weworkremotely,arbeitnow",
        platform_targets: "linkedin,indeed",
        backend_only: true,
        remote_only: true,
        junior_only: false,
        verified_payment_only: false,
        salary_only: false,
        visa_support_only: false,
        pakistan_friendly_only: false
      },
      overviewBuilder: (form) => {
        const role = getSelectText(form, 'select[name="search_focus"]');
        const region = getSelectText(form, 'select[name="region_preference"]');
        const trust = getSelectText(form, 'select[name="trust_signal"]');
        const posted = getSelectText(form, 'select[name="posted_within"]');
        return [`Role: ${role}`, `Region: ${region}`, `Trust: ${trust}`, `Window: ${posted}`];
      },
      presetFields: [
        "candidate_id",
        "top_k",
        "search_mode",
        "offer_type",
        "client_type",
        "contact_goal",
        "counterparty_type",
        "company_size",
        "proposal_pressure",
        "search_focus",
        "region_preference",
        "trust_signal",
        "posted_within",
        "demand_level",
        "min_match_level",
        "custom_keywords",
        "sources",
        "platform_targets",
        "backend_only",
        "remote_only",
        "junior_only",
        "verified_payment_only",
        "salary_only",
        "visa_support_only",
        "pakistan_friendly_only"
      ]
    },
    sell: {
      mode: "sell",
      form: sellForm,
      sourceSelector: '[data-role="sell-source-option"]',
      platformSelector: '[data-role="sell-platform-option"]',
      sourceInput: sellForm?.querySelector('[data-role="sell-source-input"]') || null,
      platformInput: sellForm?.querySelector('[data-role="sell-platform-targets"]') || null,
      filterOverview: document.querySelector('[data-role="sell-filter-overview"]'),
      defaults: {
        search_mode: "sell_services",
        demand_level: "premium",
        posted_within: "7d",
        search_focus: "all",
        min_match_level: "all",
        region_preference: "global",
        trust_signal: "verified_company",
        offer_type: "software",
        client_type: "property_management",
        contact_goal: "meeting",
        counterparty_type: "founder",
        company_size: "any",
        proposal_pressure: "any",
        custom_keywords: "residency management system apartment operator housing society property manager software",
        sources: "",
        platform_targets: "linkedin,google_clients,google_maps,upwork,fiverr",
        backend_only: false,
        remote_only: false,
        junior_only: false,
        verified_payment_only: false,
        salary_only: false,
        visa_support_only: false,
        pakistan_friendly_only: false
      },
      overviewBuilder: (form) => {
        const client = getSelectText(form, 'select[name="client_type"]');
        const offer = getSelectText(form, 'select[name="offer_type"]');
        const goal = getSelectText(form, 'select[name="contact_goal"]');
        const target = getSelectText(form, 'select[name="counterparty_type"]');
        return [`Client: ${client}`, `Offer: ${offer}`, `Goal: ${goal}`, `Target: ${target}`];
      },
      presetFields: [
        "candidate_id",
        "top_k",
        "search_mode",
        "offer_type",
        "client_type",
        "contact_goal",
        "counterparty_type",
        "trust_signal",
        "custom_keywords",
        "platform_targets",
        "sources"
      ]
    }
  };

  function safeJsonParse(raw, fallback) {
    try {
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  }

  function readStorage(key, fallback) {
    return safeJsonParse(window.localStorage.getItem(key), fallback);
  }

  function writeStorage(key, value) {
    window.localStorage.setItem(key, JSON.stringify(value));
  }

  function getSelectText(form, selector) {
    const field = form?.querySelector(selector);
    if (!(field instanceof HTMLSelectElement)) {
      return "";
    }
    return field.options[field.selectedIndex]?.text || "";
  }

  function setActiveMode(mode) {
    writeStorage(storageKeys.uiMode, mode);
    modeToggles.forEach((button) => {
      button.classList.toggle("active", button.dataset.mode === mode);
    });
    modeShells.forEach((shell) => {
      shell.classList.toggle("hidden", shell.dataset.modePanel !== mode);
    });
    modeSummaryCards.forEach((card) => {
      card.classList.toggle("active", card.dataset.modeCard === mode);
    });
    if (spotlightTitle) {
      spotlightTitle.textContent = modeMeta[mode].title;
    }
    if (spotlightDescription) {
      spotlightDescription.textContent = modeMeta[mode].description;
    }
    staleResultsNotes.forEach((note) => {
      const isStale = note.dataset.mode === mode && mode !== serverResultMode;
      note.classList.toggle("hidden", !isStale);
    });
    liveResultsContent.forEach((content) => {
      const isStale = content.dataset.mode === mode && mode !== serverResultMode;
      content.classList.toggle("hidden", isStale);
    });
  }

  function syncHiddenValues(config) {
    if (config.sourceInput) {
      const sourceValues = Array.from(document.querySelectorAll(config.sourceSelector))
        .filter((checkbox) => checkbox.checked)
        .map((checkbox) => checkbox.value);
      config.sourceInput.value = sourceValues.join(",");
    }
    if (config.platformInput) {
      const platformValues = Array.from(document.querySelectorAll(config.platformSelector))
        .filter((checkbox) => checkbox.checked)
        .map((checkbox) => checkbox.value);
      config.platformInput.value = platformValues.join(",");
    }
  }

  function setSubmitState(mode, isBusy) {
    const config = formConfig[mode];
    if (!(config?.form instanceof HTMLFormElement)) {
      return;
    }
    const submitButton = config.form.querySelector('button[type="submit"]');
    const feedback = Array.from(submitFeedbackNodes).find((node) => node.dataset.mode === mode);
    if (submitButton instanceof HTMLButtonElement) {
      submitButton.disabled = isBusy;
      submitButton.textContent = isBusy ? submitMeta[mode].busyLabel : submitMeta[mode].idleLabel;
      submitButton.classList.toggle("is-loading", isBusy);
    }
    if (feedback) {
      feedback.textContent = isBusy ? submitMeta[mode].feedback : "";
      feedback.classList.toggle("is-visible", isBusy);
    }
    config.form.classList.toggle("is-submitting", isBusy);
  }

  function hydrateCheckboxGroup(selector, csv) {
    const selectedValues = new Set((csv || "").split(",").map((value) => value.trim()).filter(Boolean));
    document.querySelectorAll(selector).forEach((checkbox) => {
      checkbox.checked = selectedValues.has(checkbox.value);
    });
  }

  function captureFormState(config) {
    if (!(config.form instanceof HTMLFormElement)) {
      return {};
    }
    syncHiddenValues(config);
    const state = {};
    config.presetFields.forEach((name) => {
      const field = config.form.elements.namedItem(name);
      if (!field) {
        return;
      }
      if (field instanceof HTMLInputElement && field.type === "checkbox") {
        state[name] = field.checked;
        return;
      }
      state[name] = field.value;
    });
    return state;
  }

  function applyFormState(config, state) {
    if (!(config.form instanceof HTMLFormElement) || !state) {
      return;
    }
    Object.entries(state).forEach(([name, value]) => {
      const field = config.form.elements.namedItem(name);
      if (!field) {
        return;
      }
      if (field instanceof HTMLInputElement && field.type === "checkbox") {
        field.checked = Boolean(value);
        return;
      }
      if (typeof value === "string") {
        field.value = value;
      }
    });
    hydrateCheckboxGroup(config.sourceSelector, config.sourceInput?.value || "");
    hydrateCheckboxGroup(config.platformSelector, config.platformInput?.value || "");
    updateOverview(config);
  }

  function applyDefaults(config) {
    applyFormState(config, config.defaults);
  }

  function updateOverview(config) {
    if (!config.filterOverview) {
      return;
    }
    const pills = config.overviewBuilder(config.form);
    config.filterOverview.innerHTML = pills.map((item) => `<span>${item}</span>`).join("");
  }

  function persistModeState(mode) {
    const state = readStorage(storageKeys.modeState, {});
    state[mode] = captureFormState(formConfig[mode]);
    writeStorage(storageKeys.modeState, state);
  }

  function restoreModeState(mode) {
    const state = readStorage(storageKeys.modeState, {});
    const config = formConfig[mode];
    const snapshot = state[mode];
    if (snapshot) {
      applyFormState(config, snapshot);
      return;
    }
    applyDefaults(config);
  }

  function getPresetBuckets() {
    return readStorage(storageKeys.presets, { job: [], sell: [] });
  }

  function writePresetBuckets(payload) {
    writeStorage(storageKeys.presets, payload);
  }

  function normalizeServerPresets() {
    const raw = document.querySelector('[data-role="saved-presets-json"]')?.textContent?.trim() || "[]";
    const parsed = safeJsonParse(raw, []);
    const buckets = { job: [], sell: [] };
    parsed.forEach((preset) => {
      const state = safeJsonParse(preset.preset_json || "{}", {});
      const mode = state.search_mode === "sell_services" || state.search_mode === "sell_products" || state.search_mode === "direct_clients" ? "sell" : "job";
      buckets[mode].push({ id: preset.id, name: preset.name, state });
    });
    return buckets;
  }

  function mergePresets(localBuckets, serverBuckets) {
    const merged = { job: [], sell: [] };
    ["job", "sell"].forEach((mode) => {
      const map = new Map();
      [...(localBuckets[mode] || []), ...(serverBuckets[mode] || [])].forEach((preset) => {
        map.set(preset.name, preset);
      });
      merged[mode] = Array.from(map.values()).sort((left, right) => left.name.localeCompare(right.name));
    });
    return merged;
  }

  async function savePresetToServer(candidateId, name, state) {
    const body = new URLSearchParams({
      candidate_id: candidateId,
      preset_name: name,
      preset_payload: JSON.stringify(state)
    });

    const response = await fetch("/dashboard/filter-presets", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString()
    });

    if (!response.ok) {
      throw new Error("Could not save preset");
    }

    const data = await response.json();
    return {
      id: data.preset.id,
      name: data.preset.name,
      state: safeJsonParse(data.preset.preset_json || "{}", {})
    };
  }

  async function deletePresetFromServer(candidateId, presetId) {
    const body = new URLSearchParams({ candidate_id: candidateId });
    const response = await fetch(`/dashboard/filter-presets/${presetId}/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString()
    });
    if (!response.ok) {
      throw new Error("Could not delete preset");
    }
  }

  function renderPresetLibrary(mode) {
    const library = document.querySelector(`[data-role="preset-library"][data-preset-mode="${mode}"]`);
    if (!(library instanceof HTMLSelectElement)) {
      return;
    }
    const buckets = getPresetBuckets();
    const currentValue = library.value;
    library.innerHTML = `<option value="">Choose ${mode === "job" ? "job" : "client"} preset</option>`;
    (buckets[mode] || []).forEach((preset) => {
      const option = document.createElement("option");
      option.value = preset.name;
      option.textContent = preset.name;
      if (preset.id) {
        option.dataset.presetId = String(preset.id);
      }
      library.appendChild(option);
    });
    if ((buckets[mode] || []).some((preset) => preset.name === currentValue)) {
      library.value = currentValue;
    }
  }

  function setPresetStatus(mode, message) {
    const element = document.querySelector(`[data-role="preset-status"][data-preset-mode="${mode}"]`);
    if (element) {
      element.textContent = message;
    }
  }

  function getPresetNameInput(mode) {
    return document.querySelector(`[data-role="preset-name"][data-preset-mode="${mode}"]`);
  }

  function getPresetLibrary(mode) {
    return document.querySelector(`[data-role="preset-library"][data-preset-mode="${mode}"]`);
  }

  function getPresetCandidateId(mode) {
    return document.querySelector(`[data-role="preset-candidate-id"][data-preset-mode="${mode}"]`)?.value?.trim() || "";
  }

  function wirePresetControls(mode) {
    const config = formConfig[mode];
    const saveButton = document.querySelector(`[data-role="save-preset"][data-preset-mode="${mode}"]`);
    const applyButton = document.querySelector(`[data-role="apply-preset"][data-preset-mode="${mode}"]`);
    const deleteButton = document.querySelector(`[data-role="delete-preset"][data-preset-mode="${mode}"]`);
    const exportButton = document.querySelector(`[data-role="export-presets"][data-preset-mode="${mode}"]`);
    const importButton = document.querySelector(`[data-role="import-presets"][data-preset-mode="${mode}"]`);
    const importFile = document.querySelector(`[data-role="preset-import-file"][data-preset-mode="${mode}"]`);
    const library = getPresetLibrary(mode);
    const nameInput = getPresetNameInput(mode);

    library?.addEventListener("change", () => {
      if (nameInput instanceof HTMLInputElement) {
        nameInput.value = library.value;
      }
    });

    saveButton?.addEventListener("click", async () => {
      const name = nameInput?.value?.trim();
      if (!name) {
        setPresetStatus(mode, "Preset name required.");
        return;
      }
      persistModeState(mode);
      const state = captureFormState(config);
      const buckets = getPresetBuckets();
      const candidateId = getPresetCandidateId(mode);
      let preset = { name, state };
      if (candidateId) {
        try {
          preset = await savePresetToServer(candidateId, name, state);
        } catch {
          setPresetStatus(mode, "Could not save preset right now.");
          return;
        }
      }
      buckets[mode] = (buckets[mode] || []).filter((item) => item.name !== name);
      buckets[mode].push(preset);
      buckets[mode].sort((left, right) => left.name.localeCompare(right.name));
      writePresetBuckets(buckets);
      renderPresetLibrary(mode);
      if (library instanceof HTMLSelectElement) {
        library.value = name;
      }
      setPresetStatus(mode, `${mode === "job" ? "Job" : "Client"} preset saved: ${name}`);
    });

    applyButton?.addEventListener("click", () => {
      const name = library?.value;
      if (!name) {
        setPresetStatus(mode, "Choose a preset first.");
        return;
      }
      const preset = (getPresetBuckets()[mode] || []).find((item) => item.name === name);
      if (!preset) {
        setPresetStatus(mode, "Preset not found.");
        return;
      }
      applyFormState(config, preset.state);
      persistModeState(mode);
      setPresetStatus(mode, `${mode === "job" ? "Job" : "Client"} preset applied: ${name}`);
    });

    deleteButton?.addEventListener("click", async () => {
      const name = library?.value || nameInput?.value?.trim();
      if (!name) {
        setPresetStatus(mode, "Choose a preset name first.");
        return;
      }
      const buckets = getPresetBuckets();
      const preset = (buckets[mode] || []).find((item) => item.name === name);
      if (!preset) {
        setPresetStatus(mode, "Preset not found.");
        return;
      }
      const candidateId = getPresetCandidateId(mode);
      if (candidateId && preset.id) {
        try {
          await deletePresetFromServer(candidateId, preset.id);
        } catch {
          setPresetStatus(mode, "Could not delete preset right now.");
          return;
        }
      }
      buckets[mode] = (buckets[mode] || []).filter((item) => item.name !== name);
      writePresetBuckets(buckets);
      renderPresetLibrary(mode);
      if (library instanceof HTMLSelectElement) {
        library.value = "";
      }
      if (nameInput instanceof HTMLInputElement) {
        nameInput.value = "";
      }
      setPresetStatus(mode, `${mode === "job" ? "Job" : "Client"} preset deleted: ${name}`);
    });

    exportButton?.addEventListener("click", () => {
      const payload = {
        mode,
        exported_at: new Date().toISOString(),
        presets: getPresetBuckets()[mode] || []
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `jobmind-${mode}-presets-${Date.now()}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setPresetStatus(mode, `Exported ${(getPresetBuckets()[mode] || []).length} preset(s).`);
    });

    importButton?.addEventListener("click", () => {
      importFile?.click();
    });

    importFile?.addEventListener("change", async () => {
      const file = importFile.files?.[0];
      if (!file) {
        return;
      }
      const parsed = safeJsonParse(await file.text(), {});
      const imported = Array.isArray(parsed?.presets) ? parsed.presets : Array.isArray(parsed) ? parsed : [];
      const normalized = imported
        .filter((item) => item && typeof item.name === "string" && item.name.trim())
        .map((item) => ({ name: item.name.trim(), state: item.state || {} }));
      const buckets = getPresetBuckets();
      normalized.forEach((preset) => {
        buckets[mode] = (buckets[mode] || []).filter((item) => item.name !== preset.name);
        buckets[mode].push(preset);
      });
      buckets[mode].sort((left, right) => left.name.localeCompare(right.name));
      writePresetBuckets(buckets);
      renderPresetLibrary(mode);
      setPresetStatus(mode, `Imported ${normalized.length} preset(s).`);
      importFile.value = "";
    });
  }

  function submitModeForm(mode) {
    const config = formConfig[mode];
    if (!(config.form instanceof HTMLFormElement)) {
      return;
    }
    setSubmitState(mode, true);
    syncHiddenValues(config);
    persistModeState(mode);
    const formData = new FormData(config.form);
    const params = new URLSearchParams();
    for (const [key, value] of formData.entries()) {
      if (!key) {
        continue;
      }
      params.set(key, String(value));
    }
    config.form.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      if (!checkbox.name) {
        return;
      }
      params.set(checkbox.name, checkbox.checked ? "true" : "false");
    });
    const targetUrl = `${config.form.getAttribute("action") || currentPath}?${params.toString()}`;
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        window.location.assign(targetUrl);
      });
    });
  }

  function wireForm(config) {
    if (!(config.form instanceof HTMLFormElement)) {
      return;
    }
    hydrateCheckboxGroup(config.sourceSelector, config.sourceInput?.value || config.defaults.sources || "");
    hydrateCheckboxGroup(config.platformSelector, config.platformInput?.value || config.defaults.platform_targets || "");

    config.form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitModeForm(config.mode);
    });

    config.form.querySelectorAll("select, input, textarea").forEach((field) => {
      field.addEventListener("change", () => {
        syncHiddenValues(config);
        updateOverview(config);
        persistModeState(config.mode);
      });
      field.addEventListener("input", () => {
        persistModeState(config.mode);
      });
    });

    document.querySelectorAll(config.sourceSelector).forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        syncHiddenValues(config);
        persistModeState(config.mode);
      });
    });

    document.querySelectorAll(config.platformSelector).forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        syncHiddenValues(config);
        persistModeState(config.mode);
      });
    });

    updateOverview(config);
  }

  function applyModePreset(button) {
    const mode = button.dataset.targetForm;
    const config = formConfig[mode];
    if (!config) {
      return;
    }
    const patch = {};
    if (button.dataset.mode) patch.search_mode = button.dataset.mode;
    if (button.dataset.offer) patch.offer_type = button.dataset.offer;
    if (button.dataset.client) patch.client_type = button.dataset.client;
    if (button.dataset.goal) patch.contact_goal = button.dataset.goal;
    if (button.dataset.side) patch.counterparty_type = button.dataset.side;
    if (button.dataset.trust) patch.trust_signal = button.dataset.trust;
    if (button.dataset.keywords !== undefined) patch.custom_keywords = button.dataset.keywords;
    if (button.dataset.platforms !== undefined) patch.platform_targets = button.dataset.platforms;
    if (button.dataset.sources !== undefined) patch.sources = button.dataset.sources;
    if (button.dataset.region) patch.region_preference = button.dataset.region;
    applyFormState(config, patch);
    persistModeState(mode);
    setActiveMode(mode);
  }

  function getTrackerBuckets() {
    return readStorage(storageKeys.trackers, { job: [], sell: [] });
  }

  function writeTrackerBuckets(payload) {
    writeStorage(storageKeys.trackers, payload);
  }

  function syncServerTrackersToLocal() {
    const jobRaw = document.querySelector('[data-role="server-applications-json"]')?.textContent?.trim() || "[]";
    const sellRaw = document.querySelector('[data-role="server-client-leads-json"]')?.textContent?.trim() || "[]";
    const buckets = getTrackerBuckets();
    buckets.job = safeJsonParse(jobRaw, []);
    buckets.sell = safeJsonParse(sellRaw, []);
    writeTrackerBuckets(buckets);
  }

  function wireModeToggles() {
    modeToggles.forEach((button) => {
      button.addEventListener("click", () => {
        const mode = button.dataset.mode || "job";
        setActiveMode(mode);
        restoreModeState(mode);
      });
    });
  }

  document.querySelectorAll('[data-copy-query]').forEach((button) => {
    button.addEventListener("click", async () => {
      const query = button.getAttribute("data-copy-query") || "";
      if (!query) {
        return;
      }
      try {
        await navigator.clipboard.writeText(query);
        const originalText = button.textContent;
        button.textContent = "Copied";
        window.setTimeout(() => {
          button.textContent = originalText;
        }, 1000);
      } catch {
        button.textContent = "Copy failed";
      }
    });
  });

  document.querySelectorAll('[data-role="mode-preset"]').forEach((button) => {
    button.addEventListener("click", () => {
      applyModePreset(button);
    });
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register(`/static/sw.js?v=${encodeURIComponent(staticVersion)}`).catch(() => {
      // Ignore registration failures.
    });
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    installButton?.classList.remove("hidden");
  });

  installButton?.addEventListener("click", async () => {
    if (!installPrompt) {
      return;
    }
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    installButton.classList.add("hidden");
  });

  window.addEventListener("popstate", () => {
    lastNativePath = window.location.pathname;
  });

  if (typeof capacitorApp?.addListener === "function") {
    capacitorApp.addListener("backButton", async () => {
      const hasBrowserHistory = window.history.length > 1;
      const movedWithinApp = window.location.pathname !== lastNativePath;
      lastNativePath = window.location.pathname;
      if (hasBrowserHistory || movedWithinApp) {
        window.history.back();
        return;
      }
      if (typeof capacitorApp.exitApp === "function") {
        await capacitorApp.exitApp();
      }
    });
  }

  const mergedPresets = mergePresets(getPresetBuckets(), normalizeServerPresets());
  writePresetBuckets(mergedPresets);
  renderPresetLibrary("job");
  renderPresetLibrary("sell");
  wirePresetControls("job");
  wirePresetControls("sell");
  wireForm(formConfig.job);
  wireForm(formConfig.sell);
  syncServerTrackersToLocal();
  wireModeToggles();
  restoreModeState("job");
  restoreModeState("sell");
  setActiveMode(readStorage(storageKeys.uiMode, initialMode) || initialMode);
});
