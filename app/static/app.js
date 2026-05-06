window.addEventListener("DOMContentLoaded", () => {
  let installPrompt = null;
  let lastNativePath = window.location.pathname;
  const cards = document.querySelectorAll(".card");
  cards.forEach((card, i) => {
    card.animate(
      [
        { opacity: 0, transform: "translateY(10px)" },
        { opacity: 1, transform: "translateY(0)" }
      ],
      {
        duration: 320,
        delay: i * 70,
        fill: "forwards",
        easing: "ease-out"
      }
    );
  });

  document.querySelectorAll("[data-copy-query]").forEach((button) => {
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

  const searchFocus = document.querySelector('[data-role="search-focus"]');
  const matchForm = document.querySelector('[data-role="match-form"]');
  const searchMode = document.querySelector('[data-role="search-mode"]');
  const offerType = document.querySelector('[data-role="offer-type"]');
  const clientType = document.querySelector('[data-role="client-type"]');
  const demandLevel = document.querySelector('[data-role="demand-level"]');
  const contactGoal = document.querySelector('[data-role="contact-goal"]');
  const counterpartyType = document.querySelector('[data-role="counterparty-type"]');
  const postedWithin = document.querySelector('[data-role="posted-within"]');
  const trustSignal = document.querySelector('[data-role="trust-signal"]');
  const companySize = document.querySelector('[data-role="company-size"]');
  const proposalPressure = document.querySelector('[data-role="proposal-pressure"]');
  const customKeywords = document.querySelector('[data-role="custom-keywords"]');
  const modeHint = document.querySelector('[data-role="mode-hint"]');
  const filterOverview = document.querySelector('[data-role="filter-overview"]');
  const workflowTabs = document.querySelectorAll('[data-role="workflow-tab"]');
  const workflowPanels = document.querySelectorAll('[data-role="workflow-panel"]');
  const remoteOnly = document.querySelector('[data-role="remote-only"]');
  const juniorOnly = document.querySelector('[data-role="junior-only"]');
  const backendOnly = document.querySelector('input[name="backend_only"]');
  const regionPreference = document.querySelector('[data-role="region-preference"]');
  const sourceInput = document.querySelector('[data-role="source-input"]');
  const platformTargetsInput = document.querySelector('[data-role="platform-targets"]');
  const verifiedPaymentOnly = matchForm?.elements?.namedItem("verified_payment_only");
  const pakistanFriendlyOnly = matchForm?.elements?.namedItem("pakistan_friendly_only");
  const savedPresetsJson = document.querySelector('[data-role="saved-presets-json"]');
  const presetLibrary = document.querySelector('[data-role="preset-library"]');
  const presetNameInput = document.querySelector('[data-role="preset-name"]');
  const presetStatus = document.querySelector('[data-role="preset-status"]');
  const presetCandidateId = document.querySelector('[data-role="preset-candidate-id"]');
  const presetImportFile = document.querySelector('[data-role="preset-import-file"]');
  const savePresetButton = document.querySelector('[data-role="save-preset"]');
  const applyPresetButton = document.querySelector('[data-role="apply-preset"]');
  const deletePresetButton = document.querySelector('[data-role="delete-preset"]');
  const exportPresetsButton = document.querySelector('[data-role="export-presets"]');
  const importPresetsButton = document.querySelector('[data-role="import-presets"]');
  const installButton = document.querySelector('[data-role="install-app"]');
  const miniJobsLaunch = document.querySelector('[data-role="mini-jobs-launch"]');
  const capacitorApp = window.Capacitor?.Plugins?.App;
  const presetStorageKey = "jobmind_filter_presets_v1";
  let serverPresets = [];
  const presetFieldNames = [
    "candidate_id",
    "top_k",
    "sources",
    "platform_targets",
    "search_mode",
    "offer_type",
    "client_type",
    "demand_level",
    "contact_goal",
    "counterparty_type",
    "trust_signal",
    "posted_within",
    "company_size",
    "proposal_pressure",
    "custom_keywords",
    "min_match_level",
    "backend_only",
    "remote_only",
    "junior_only",
    "search_focus",
    "pakistan_friendly_only",
    "salary_only",
    "visa_support_only",
    "verified_payment_only",
    "region_preference"
  ];

  const syncCheckedValues = (selector, hiddenInput) => {
    if (!hiddenInput) {
      return;
    }

    const options = Array.from(document.querySelectorAll(selector));
    const selectedValues = options.filter((option) => option.checked).map((option) => option.value);
    hiddenInput.value = selectedValues.join(',');
  };

  const setPresetStatus = (message) => {
    if (presetStatus) {
      presetStatus.textContent = message;
    }
  };

  const getCandidatePresetKey = () => {
    const candidateId = presetCandidateId?.value?.trim();
    return candidateId ? `${presetStorageKey}:${candidateId}` : presetStorageKey;
  };

  const normalizeServerPresets = () => {
    if (!savedPresetsJson?.textContent?.trim()) {
      return [];
    }

    try {
      const parsed = JSON.parse(savedPresetsJson.textContent);
      if (!Array.isArray(parsed)) {
        return [];
      }

      return parsed.map((preset) => ({
        id: preset.id,
        candidate_id: preset.candidate_id,
        name: preset.name,
        state: JSON.parse(preset.preset_json || "{}")
      }));
    } catch {
      return [];
    }
  };

  const readPresets = () => {
    if (serverPresets.length) {
      return serverPresets;
    }

    try {
      const raw = window.localStorage.getItem(getCandidatePresetKey());
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  };

  const writePresets = (presets) => {
    serverPresets = presets;
    window.localStorage.setItem(getCandidatePresetKey(), JSON.stringify(presets));
  };

  const renderPresetLibrary = () => {
    if (!presetLibrary) {
      return;
    }

    const presets = readPresets();
    const currentValue = presetLibrary.value;
    presetLibrary.innerHTML = '<option value="">Choose saved preset</option>';
    presets.forEach((preset) => {
      const option = document.createElement("option");
      option.value = preset.name;
      option.textContent = preset.name;
      if (preset.id) {
        option.dataset.presetId = String(preset.id);
      }
      presetLibrary.appendChild(option);
    });
    if (presets.some((preset) => preset.name === currentValue)) {
      presetLibrary.value = currentValue;
    }
  };

  const savePresetToServer = async (candidateId, name, state) => {
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
      candidate_id: data.preset.candidate_id,
      name: data.preset.name,
      state: JSON.parse(data.preset.preset_json || "{}")
    };
  };

  const mergePresetsByName = (existingPresets, incomingPresets) => {
    const merged = [...existingPresets.filter((preset) => !incomingPresets.some((item) => item.name === preset.name)), ...incomingPresets];
    merged.sort((left, right) => left.name.localeCompare(right.name));
    return merged;
  };

  const exportPresets = () => {
    const presets = readPresets();
    if (!presets.length) {
      setPresetStatus("No presets available to export.");
      return;
    }

    const payload = {
      exported_at: new Date().toISOString(),
      candidate_id: presetCandidateId?.value?.trim() || "",
      presets: presets.map((preset) => ({ name: preset.name, state: preset.state }))
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `jobmind-presets-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setPresetStatus(`Exported ${presets.length} preset(s).`);
  };

  const importPresetPayload = async (text) => {
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch {
      setPresetStatus("Invalid preset file.");
      return;
    }

    const importedPresets = Array.isArray(parsed)
      ? parsed
      : Array.isArray(parsed?.presets)
        ? parsed.presets
        : [];

    const normalizedPresets = importedPresets
      .filter((preset) => preset && typeof preset.name === "string" && preset.name.trim())
      .map((preset) => ({ name: preset.name.trim(), state: preset.state || {} }));

    if (!normalizedPresets.length) {
      setPresetStatus("No valid presets found in file.");
      return;
    }

    const candidateId = presetCandidateId?.value?.trim();
    if (!candidateId) {
      writePresets(mergePresetsByName(readPresets(), normalizedPresets));
      renderPresetLibrary();
      setPresetStatus(`Imported ${normalizedPresets.length} preset(s) locally.`);
      return;
    }

    try {
      const savedPresets = [];
      for (const preset of normalizedPresets) {
        savedPresets.push(await savePresetToServer(candidateId, preset.name, preset.state));
      }
      writePresets(mergePresetsByName(readPresets(), savedPresets));
      renderPresetLibrary();
      setPresetStatus(`Imported ${savedPresets.length} preset(s) to profile.`);
    } catch {
      setPresetStatus("Could not import presets right now.");
    }
  };

  const capturePresetState = () => {
    if (!matchForm) {
      return {};
    }

    syncCheckedValues('[data-role="source-option"]', sourceInput);
    syncCheckedValues('[data-role="platform-option"]', platformTargetsInput);

    const state = {};
    presetFieldNames.forEach((name) => {
      const field = matchForm.elements.namedItem(name);
      if (!field) {
        return;
      }

      if (field instanceof RadioNodeList) {
        state[name] = Array.from(field).filter((item) => item.checked).map((item) => item.value);
        return;
      }

      if (field instanceof HTMLInputElement && field.type === "checkbox") {
        state[name] = field.checked;
        return;
      }

      state[name] = field.value;
    });
    return state;
  };

  const applyPresetState = (state) => {
    if (!matchForm || !state) {
      return;
    }

    presetFieldNames.forEach((name) => {
      const field = matchForm.elements.namedItem(name);
      if (!field || !(name in state)) {
        return;
      }

      if (field instanceof HTMLInputElement && field.type === "checkbox") {
        field.checked = Boolean(state[name]);
        return;
      }

      if (!(field instanceof RadioNodeList)) {
        field.value = state[name];
      }
    });

    hydrateCheckedValues('[data-role="source-option"]', sourceInput);
    hydrateCheckedValues('[data-role="platform-option"]', platformTargetsInput);
    updateModeHint();
    updateFilterOverview();
  };

  const updateFilterOverview = () => {
    if (!filterOverview || !searchMode || !offerType || !clientType || !contactGoal) {
      return;
    }

    const mode = searchMode.options[searchMode.selectedIndex]?.text || "Job search";
    const offer = offerType.options[offerType.selectedIndex]?.text || "Software offering";
    const client = clientType.options[clientType.selectedIndex]?.text || "Startups";
    const goal = contactGoal.options[contactGoal.selectedIndex]?.text || "Apply";
    const side = counterpartyType?.options[counterpartyType.selectedIndex]?.text || "Any side";
    const posted = postedWithin?.options[postedWithin.selectedIndex]?.text || "Last 7 days";
    const trust = trustSignal?.options[trustSignal.selectedIndex]?.text || "Any trust level";
    filterOverview.innerHTML = `
      <span>Mode: ${mode}</span>
      <span>Offer: ${offer}</span>
      <span>Client: ${client}</span>
      <span>Goal: ${goal}</span>
      <span>Side: ${side}</span>
      <span>Posted: ${posted}</span>
      <span>Trust: ${trust}</span>
    `;
  };

  const updateModeHint = () => {
    if (!modeHint || !searchMode) {
      return;
    }

    const messages = {
      job_search: "Use this when you want scored job matches plus fresh external listings on selected platforms.",
      sell_services: "Use this when you want client demand, agencies, and service buyers with pitch-ready links.",
      sell_products: "Use this when you want importers, wholesale buyers, and product discovery across web channels.",
      direct_clients: "Use this when your goal is direct outreach to founders, companies, and decision makers."
    };

    modeHint.textContent = messages[searchMode.value] || messages.job_search;
  };

  const setActiveWorkflowTab = (tabName) => {
    workflowTabs.forEach((button) => {
      button.classList.toggle("active", button.dataset.tabTarget === tabName);
    });

    workflowPanels.forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.tabPanel !== tabName);
    });
  };

  const syncWorkflowTabWithMode = () => {
    const clientModes = new Set(["direct_clients", "sell_services", "sell_products"]);
    setActiveWorkflowTab(clientModes.has(searchMode?.value) ? "clients" : "jobs");
  };

  const hydrateCheckedValues = (selector, hiddenInput) => {
    if (!hiddenInput) {
      return;
    }

    const selectedValues = new Set((hiddenInput.value || '').split(',').map((value) => value.trim()).filter(Boolean));
    document.querySelectorAll(selector).forEach((option) => {
      option.checked = selectedValues.has(option.value);
    });
  };

  const handleNativeBack = async () => {
    const hasBrowserHistory = window.history.length > 1;
    const movedWithinApp = window.location.pathname !== lastNativePath;

    lastNativePath = window.location.pathname;

    if (hasBrowserHistory || movedWithinApp) {
      window.history.back();
      return;
    }

    if (typeof capacitorApp?.exitApp === "function") {
      await capacitorApp.exitApp();
    }
  };

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {
      // Keep the dashboard usable even if service worker registration fails.
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

  savePresetButton?.addEventListener("click", () => {
    const name = presetNameInput?.value.trim();
    if (!name) {
      setPresetStatus("Preset name required.");
      return;
    }

    const state = capturePresetState();
    const candidateId = presetCandidateId?.value?.trim();
    if (!candidateId) {
      const presets = readPresets().filter((preset) => preset.name !== name);
      presets.push({ name, state });
      presets.sort((left, right) => left.name.localeCompare(right.name));
      writePresets(presets);
      renderPresetLibrary();
      if (presetLibrary) {
        presetLibrary.value = name;
      }
      setPresetStatus(`Preset saved locally: ${name}`);
      return;
    }

    savePresetToServer(candidateId, name, state)
      .then(async (response) => {
        const presets = readPresets().filter((preset) => preset.name !== response.name);
        presets.push(response);
        presets.sort((left, right) => left.name.localeCompare(right.name));
        writePresets(presets);
        renderPresetLibrary();
        if (presetLibrary) {
          presetLibrary.value = name;
        }
        setPresetStatus(`Preset saved to profile: ${name}`);
      })
      .catch(() => {
        setPresetStatus("Could not save preset right now.");
      });
  });

  exportPresetsButton?.addEventListener("click", () => {
    exportPresets();
  });

  importPresetsButton?.addEventListener("click", () => {
    presetImportFile?.click();
  });

  presetImportFile?.addEventListener("change", async () => {
    const file = presetImportFile.files?.[0];
    if (!file) {
      return;
    }

    const text = await file.text();
    await importPresetPayload(text);
    presetImportFile.value = "";
  });

  applyPresetButton?.addEventListener("click", () => {
    const name = presetLibrary?.value;
    if (!name) {
      setPresetStatus("Choose a preset first.");
      return;
    }

    const preset = readPresets().find((item) => item.name === name);
    if (!preset) {
      setPresetStatus("Selected preset no longer exists.");
      renderPresetLibrary();
      return;
    }

    applyPresetState(preset.state);
    if (presetNameInput) {
      presetNameInput.value = preset.name;
    }
    setPresetStatus(`Preset applied: ${name}`);
  });

  deletePresetButton?.addEventListener("click", () => {
    const name = presetLibrary?.value || presetNameInput?.value.trim();
    if (!name) {
      setPresetStatus("Choose or type a preset name to delete.");
      return;
    }

    const presets = readPresets();
    const selectedPreset = presets.find((preset) => preset.name === name);
    if (!selectedPreset) {
      setPresetStatus("Preset not found.");
      return;
    }

    const finishDelete = () => {
      writePresets(readPresets().filter((preset) => preset.name !== name));
      renderPresetLibrary();
      if (presetLibrary) {
        presetLibrary.value = "";
      }
      if (presetNameInput) {
        presetNameInput.value = "";
      }
      setPresetStatus(`Preset deleted: ${name}`);
    };

    const candidateId = presetCandidateId?.value?.trim();
    if (!candidateId || !selectedPreset.id) {
      finishDelete();
      return;
    }

    const body = new URLSearchParams({ candidate_id: candidateId });
    fetch(`/dashboard/filter-presets/${selectedPreset.id}/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString()
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Could not delete preset");
        }
        await response.json();
        finishDelete();
      })
      .catch(() => {
        setPresetStatus("Could not delete preset right now.");
      });
  });

  presetLibrary?.addEventListener("change", () => {
    if (!presetNameInput) {
      return;
    }
    presetNameInput.value = presetLibrary.value;
  });

  document.querySelectorAll(".preset-chip").forEach((button) => {
    button.addEventListener("click", () => {
      if (searchFocus) {
        searchFocus.value = button.dataset.focus || "python";
      }
      if (searchMode) {
        searchMode.value = button.dataset.mode || "job_search";
      }
      if (offerType && button.dataset.offer) {
        offerType.value = button.dataset.offer;
      }
      if (clientType && button.dataset.client) {
        clientType.value = button.dataset.client;
      }
      if (contactGoal && button.dataset.goal) {
        contactGoal.value = button.dataset.goal;
      }
      if (counterpartyType && button.dataset.side) {
        counterpartyType.value = button.dataset.side;
      }
      if (trustSignal && button.dataset.trust) {
        trustSignal.value = button.dataset.trust;
      }
      if (demandLevel && button.dataset.demand) {
        demandLevel.value = button.dataset.demand;
      }
      if (postedWithin && button.dataset.posted) {
        postedWithin.value = button.dataset.posted;
      }
      if (companySize && button.dataset.size) {
        companySize.value = button.dataset.size;
      }
      if (proposalPressure && button.dataset.competition) {
        proposalPressure.value = button.dataset.competition;
      }
      if (customKeywords && button.dataset.keywords !== undefined) {
        customKeywords.value = button.dataset.keywords;
      }
      if (remoteOnly) {
        remoteOnly.checked = button.dataset.remote === "true";
      }
      if (juniorOnly) {
        juniorOnly.checked = button.dataset.junior === "true";
      }
      if (backendOnly) {
        backendOnly.checked = button.dataset.backend === "true";
      }
      if (regionPreference && button.dataset.region) {
        regionPreference.value = button.dataset.region;
      }
      if (verifiedPaymentOnly instanceof HTMLInputElement && button.dataset.verified !== undefined) {
        verifiedPaymentOnly.checked = button.dataset.verified === "true";
      }
      if (pakistanFriendlyOnly instanceof HTMLInputElement && button.dataset.pakistan !== undefined) {
        pakistanFriendlyOnly.checked = button.dataset.pakistan === "true";
      }
      if (sourceInput && button.dataset.sources !== undefined) {
        sourceInput.value = button.dataset.sources;
      }
      if (platformTargetsInput && button.dataset.platforms !== undefined) {
        platformTargetsInput.value = button.dataset.platforms;
      }
      hydrateCheckedValues('[data-role="source-option"]', sourceInput);
      hydrateCheckedValues('[data-role="platform-option"]', platformTargetsInput);
      updateModeHint();
      updateFilterOverview();
      syncWorkflowTabWithMode();
    });
  });

  miniJobsLaunch?.addEventListener("click", () => {
    const miniPreset = Array.from(document.querySelectorAll('.preset-chip')).find((button) => button.textContent?.trim() === 'Mini Python Gigs');
    miniPreset?.click();
    matchForm?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  workflowTabs.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveWorkflowTab(button.dataset.tabTarget || "jobs");
    });
  });

  hydrateCheckedValues('[data-role="source-option"]', sourceInput);
  hydrateCheckedValues('[data-role="platform-option"]', platformTargetsInput);

  document.querySelectorAll('[data-role="source-option"]').forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      syncCheckedValues('[data-role="source-option"]', sourceInput);
    });
  });

  document.querySelectorAll('[data-role="platform-option"]').forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      syncCheckedValues('[data-role="platform-option"]', platformTargetsInput);
    });
  });

  [searchMode, offerType, clientType, contactGoal, counterpartyType, demandLevel, postedWithin, trustSignal, companySize, proposalPressure, customKeywords].forEach((element) => {
    element?.addEventListener("change", () => {
      updateModeHint();
      updateFilterOverview();
      syncWorkflowTabWithMode();
    });
  });

  syncCheckedValues('[data-role="source-option"]', sourceInput);
  syncCheckedValues('[data-role="platform-option"]', platformTargetsInput);
  serverPresets = normalizeServerPresets();
  renderPresetLibrary();
  updateModeHint();
  updateFilterOverview();
  syncWorkflowTabWithMode();

  window.addEventListener("popstate", () => {
    lastNativePath = window.location.pathname;
  });

  if (typeof capacitorApp?.addListener === "function") {
    capacitorApp.addListener("backButton", () => {
      void handleNativeBack();
    });
  }
});
