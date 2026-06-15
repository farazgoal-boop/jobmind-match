(function () {
  "use strict";

  const REGISTRY_KEY = "jobmind.hunted.registry.v1";
  const PROFILE_KEY = "jobmind.mobile.profile.v1";
  const EMAIL_RE = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,7}/g;
  const GH_QUERIES = [
    "freelance developer email hire",
    "python developer freelance email",
    "react developer freelance email",
    "shopify developer email contact",
    "UI UX designer email contact hire",
    "digital marketer email whatsapp hire"
  ];
  const DEVTO_TAGS = ["forhire", "freelance", "hiring", "webdev", "python", "react"];
  const REDDIT_SUBS = ["forhire", "freelance", "slavelabour", "hiring", "WorkOnline"];
  const RSS_FEEDS = [
    ["Remotive", "https://remotive.com/remote-jobs/feed"],
    ["WeWorkRemotely", "https://weworkremotely.com/remote-jobs.rss"],
    ["Authentic Jobs", "https://authenticjobs.com/rss/custom.php?type=rss"]
  ];

  let huntData = { summary: { total: 212 }, hunt_plan: [] };
  let leads = [];
  let emails = new Set();
  let was = new Set();
  let dups = 0;
  let running = false;
  let halt = false;
  let uiMode = "sell";
  let sellPanel = "hunt";
  let jobPanel = "search";

  function $(id) { return document.getElementById(id); }

  function loadRegistry() {
    try {
      const raw = localStorage.getItem(REGISTRY_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      (data.emails || []).forEach((e) => emails.add(e.toLowerCase().trim()));
      (data.whatsapp || []).forEach((w) => was.add(normWa(w)));
    } catch (e) { /* ignore */ }
  }

  function saveRegistry() {
    localStorage.setItem(REGISTRY_KEY, JSON.stringify({
      emails: [...emails],
      whatsapp: [...was],
      total: emails.size + was.size
    }));
  }

  function normWa(v) {
    return (v || "").replace(/[\s\-]/g, "");
  }

  function validEmail(e) {
    return e && !e.endsWith(".png") && !e.endsWith(".jpg") && e.includes("@");
  }

  function extractContacts(text) {
    const foundEmails = [...new Set((text.match(EMAIL_RE) || []).filter(validEmail))];
    const foundWa = [];
    const waRe = /(?:whatsapp\.com\/send\?phone=(\d{7,15})|(?:whatsapp|wa)[:\s\-]+(\+?[\d][\d\s\-]{9,14}))/gi;
    let m;
    while ((m = waRe.exec(text)) !== null) {
      const num = (m[1] || m[2] || "").replace(/[\s\-]/g, "");
      if (num.length >= 10) foundWa.push(num.startsWith("+") ? num : "+" + num);
    }
    return { emails: foundEmails, whatsapp: [...new Set(foundWa)] };
  }

  function addLeads(batch) {
    let added = 0;
    for (const l of batch) {
      const e = (l.email || "").toLowerCase().trim();
      const w = normWa(l.whatsapp);
      if (!e && !w) { dups++; continue; }
      if (e && emails.has(e)) { dups++; continue; }
      if (w && !e && was.has(w)) { dups++; continue; }
      if (e) emails.add(e);
      if (w) was.add(w);
      leads.push(l);
      added++;
    }
    saveRegistry();
    renderLeads();
    updateStats();
    return added;
  }

  function updateStats() {
    $("stat-total").textContent = leads.length;
    $("stat-email").textContent = leads.filter((l) => l.email).length;
    $("stat-wa").textContent = leads.filter((l) => l.whatsapp).length;
    $("stat-known").textContent = emails.size + was.size;
    $("stat-dup").textContent = dups;
    $("platform-count").textContent = huntData.summary?.total || huntData.hunt_plan?.length || 212;
  }

  function log(msg) {
    const el = $("hunt-log");
    el.innerHTML += "› " + msg + "<br>";
    el.scrollTop = el.scrollHeight;
  }

  function setProg(pct, status) {
    $("prog-fill").style.width = Math.min(pct, 99) + "%";
    $("prog-pct").textContent = Math.min(Math.round(pct), 99) + "%";
    if (status) $("prog-status").textContent = status;
  }

  async function fetchText(url, headers) {
    const res = await fetch(url, { headers: headers || {}, cache: "no-store" });
    if (!res.ok) throw new Error(res.status + "");
    return res.text();
  }

  async function fetchJson(url, headers) {
    const res = await fetch(url, { headers: headers || {}, cache: "no-store" });
    if (!res.ok) throw new Error(res.status + "");
    return res.json();
  }

  async function huntGithub(offset) {
    const kw = ($("hunt-kw").value || "").trim();
    const query = kw || GH_QUERIES[offset % GH_QUERIES.length];
    const page = Math.floor(offset / GH_QUERIES.length) + 1;
    const hdr = { Accept: "application/vnd.github.v3+json" };
    const search = await fetchJson(
      "https://api.github.com/search/users?q=" + encodeURIComponent(query) + "&per_page=20&page=" + page,
      hdr
    );
    const out = [];
    for (const u of (search.items || []).slice(0, 12)) {
      try {
        const p = await fetchJson("https://api.github.com/users/" + u.login, hdr);
        const blob = [p.bio, p.blog, p.location, p.company].filter(Boolean).join(" ");
        const ex = extractContacts(blob + " " + (p.email || ""));
        const email = p.email || ex.emails[0] || "";
        const wa = ex.whatsapp[0] || "";
        if (email || wa) {
          out.push({
            name: p.name || p.login,
            designation: "Developer",
            email,
            whatsapp: wa,
            source: "GitHub",
            url: p.html_url || "",
            notes: (p.bio || "").slice(0, 80)
          });
        }
      } catch (e) { /* skip */ }
    }
    return out;
  }

  async function huntReddit(sub) {
    const xml = await fetchText("https://www.reddit.com/r/" + sub + "/new/.rss?limit=25", {
      "User-Agent": "JobMindMatch/2.1"
    });
    const doc = new DOMParser().parseFromString(xml, "text/xml");
    const out = [];
    doc.querySelectorAll("entry").forEach((entry) => {
      const title = entry.querySelector("title")?.textContent || "";
      const content = entry.querySelector("content")?.textContent || "";
      const link = entry.querySelector("link")?.getAttribute("href") || "";
      const ex = extractContacts(title + " " + content);
      if (ex.emails.length || ex.whatsapp.length) {
        out.push({
          name: title.slice(0, 60),
          designation: "Reddit post",
          email: ex.emails[0] || "",
          whatsapp: ex.whatsapp[0] || "",
          source: "Reddit r/" + sub,
          url: link,
          notes: ""
        });
      }
    });
    return out;
  }

  async function huntDevto(tag, page) {
    const data = await fetchJson("https://dev.to/api/articles?tag=" + encodeURIComponent(tag) + "&per_page=20&page=" + page);
    const out = [];
    (data || []).forEach((a) => {
      const blob = [a.title, a.description, a.url].join(" ");
      const ex = extractContacts(blob);
      if (ex.emails.length || ex.whatsapp.length) {
        out.push({
          name: a.user?.name || a.title?.slice(0, 40) || "Dev.to",
          designation: "Article",
          email: ex.emails[0] || "",
          whatsapp: ex.whatsapp[0] || "",
          source: "Dev.to",
          url: a.url || "",
          notes: (a.title || "").slice(0, 60)
        });
      }
    });
    return out;
  }

  async function huntRss(label, url) {
    const xml = await fetchText(url, { "User-Agent": "JobMindMatch/2.1", Accept: "application/rss+xml" });
    const doc = new DOMParser().parseFromString(xml, "text/xml");
    const out = [];
    doc.querySelectorAll("item, entry").forEach((item) => {
      const title = item.querySelector("title")?.textContent || "";
      const desc = item.querySelector("description, summary, content")?.textContent || "";
      const link = item.querySelector("link")?.textContent || item.querySelector("link")?.getAttribute("href") || "";
      const ex = extractContacts(title + " " + desc);
      if (ex.emails.length || ex.whatsapp.length) {
        out.push({
          name: title.slice(0, 50),
          designation: label,
          email: ex.emails[0] || "",
          whatsapp: ex.whatsapp[0] || "",
          source: label,
          url: link,
          notes: ""
        });
      }
    });
    return out;
  }

  async function huntHN() {
    const data = await fetchJson("https://hn.algolia.com/api/v1/search?query=freelancer%20email&tags=story&hitsPerPage=20");
    const out = [];
    (data.hits || []).forEach((h) => {
      const blob = [h.title, h.url, h.story_text].filter(Boolean).join(" ");
      const ex = extractContacts(blob);
      if (ex.emails.length || ex.whatsapp.length) {
        out.push({
          name: (h.title || "").slice(0, 50),
          designation: "HN",
          email: ex.emails[0] || "",
          whatsapp: ex.whatsapp[0] || "",
          source: "Hacker News",
          url: h.url || ("https://news.ycombinator.com/item?id=" + h.objectID),
          notes: ""
        });
      }
    });
    return out;
  }

  function enabledChips() {
    return [...document.querySelectorAll(".chip[data-chip]")].filter((c) => c.classList.contains("on")).map((c) => c.dataset.chip);
  }

  function buildPlan() {
    const chips = new Set(enabledChips());
    const plan = [];
    if (chips.has("github")) {
      GH_QUERIES.forEach((q, i) => plan.push({ label: "GitHub", run: () => huntGithub(i), batches: 2 }));
    }
    if (chips.has("reddit")) {
      REDDIT_SUBS.forEach((s) => plan.push({ label: "Reddit r/" + s, run: () => huntReddit(s), batches: 1 }));
    }
    if (chips.has("devto")) {
      DEVTO_TAGS.forEach((t, i) => plan.push({ label: "Dev.to " + t, run: () => huntDevto(t, (i % 3) + 1), batches: 1 }));
    }
    if (chips.has("misc")) {
      RSS_FEEDS.forEach(([label, url]) => plan.push({ label, run: () => huntRss(label, url), batches: 1 }));
      plan.push({ label: "Hacker News", run: huntHN, batches: 1 });
    }
    if (huntData.hunt_plan?.length && plan.length < 20) {
      huntData.hunt_plan.slice(0, 40).forEach((p) => {
        if (p.chip === "github" && chips.has("github")) return;
        if (p.chip === "reddit" && chips.has("reddit")) return;
      });
    }
    return plan.length ? plan : [{ label: "GitHub", run: () => huntGithub(0), batches: 2 }];
  }

  async function startHunt() {
    if (running) return;
    running = true;
    halt = false;
    $("hunt-start").disabled = true;
    $("hunt-stop").style.display = "";
    $("hunt-prog").style.display = "block";
    $("hunt-log").innerHTML = "";
    const plan = buildPlan();
    const totalSteps = plan.reduce((n, p) => n + (p.batches || 1), 0);
    let step = 0;
    log("Starting hunt on phone (no PC, no Render)…");
    for (const item of plan) {
      if (halt) break;
      for (let b = 0; b < (item.batches || 1); b++) {
        if (halt) break;
        step++;
        setProg((step / totalSteps) * 100, item.label + "…");
        try {
          const batch = await item.run();
          const added = addLeads(batch);
          log(item.label + ": +" + added + " new");
        } catch (e) {
          log(item.label + ": skip (" + (e.message || "error") + ")");
        }
        await new Promise((r) => setTimeout(r, 800));
      }
    }
    setProg(100, "Done — " + leads.length + " contacts");
    running = false;
    $("hunt-start").disabled = false;
    $("hunt-stop").style.display = "none";
  }

  function stopHunt() { halt = true; }

  function renderLeads() {
    const tb = $("lead-tbody");
    if (!leads.length) {
      tb.innerHTML = '<tr><td colspan="5" class="hint">Tap Start Hunting — runs on your phone only.</td></tr>';
      return;
    }
    tb.innerHTML = leads.slice(0, 200).map((l, i) =>
      "<tr><td>" + (i + 1) + "</td><td>" + esc(l.name) + "</td><td>" + esc(l.email) + "</td><td>" + esc(l.whatsapp) + "</td><td>" + esc(l.source) + "</td></tr>"
    ).join("");
  }

  function esc(s) {
    return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function exportCsv() {
    const rows = [["#", "Name", "Email", "WhatsApp", "Source", "URL"]];
    leads.forEach((l, i) => rows.push([i + 1, l.name, l.email, l.whatsapp, l.source, l.url]));
    const csv = rows.map((r) => r.map((c) => '"' + String(c || "").replace(/"/g, '""') + '"').join(",")).join("\n");
    downloadBlob(csv, "jobmind-leads.csv", "text/csv");
  }

  function downloadBlob(text, name, type) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name;
    a.click();
  }

  function setMode(mode) {
    uiMode = mode;
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
    document.querySelectorAll(".panel[data-mode-panel]").forEach((p) => {
      p.classList.toggle("active", p.dataset.modePanel === mode);
    });
    document.querySelectorAll(".nav-group").forEach((g) => {
      g.style.display = g.dataset.navMode === mode ? "flex" : "none";
    });
    showPanel(mode === "sell" ? sellPanel : jobPanel, mode);
  }

  function showPanel(panelId, mode) {
    if (mode === "sell") sellPanel = panelId;
    else jobPanel = panelId;
    document.querySelectorAll(".panel[data-mode-panel='" + mode + "'] .subpanel").forEach((p) => {
      p.classList.toggle("active", p.dataset.panel === panelId);
    });
    document.querySelectorAll(".nav-group[data-nav-mode='" + mode + "'] .nav-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.panel === panelId);
    });
  }

  function saveProfile() {
    const profile = {
      name: $("prof-name").value.trim(),
      email: $("prof-email").value.trim(),
      skills: $("prof-skills").value.trim(),
      pitch: $("prof-pitch").value.trim()
    };
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
    $("prof-msg").textContent = "Saved on this phone.";
  }

  function loadProfile() {
    try {
      const p = JSON.parse(localStorage.getItem(PROFILE_KEY) || "{}");
      if (p.name) $("prof-name").value = p.name;
      if (p.email) $("prof-email").value = p.email;
      if (p.skills) $("prof-skills").value = p.skills;
      if (p.pitch) $("prof-pitch").value = p.pitch;
    } catch (e) { /* ignore */ }
  }

  async function init() {
    loadRegistry();
    loadProfile();
    try {
      const res = await fetch("data/hunt-data.json", { cache: "no-store" });
      if (res.ok) huntData = await res.json();
    } catch (e) { /* use defaults */ }
    updateStats();
    renderLeads();

    document.querySelectorAll(".chip[data-chip]").forEach((chip) => {
      chip.addEventListener("click", () => chip.classList.toggle("on"));
    });
    document.querySelectorAll(".mode-btn").forEach((b) => {
      b.addEventListener("click", () => setMode(b.dataset.mode));
    });
    document.querySelectorAll(".nav-btn").forEach((b) => {
      b.addEventListener("click", () => showPanel(b.dataset.panel, b.dataset.navMode));
    });
    $("hunt-start").addEventListener("click", startHunt);
    $("hunt-stop").addEventListener("click", stopHunt);
    $("hunt-export").addEventListener("click", exportCsv);
    $("hunt-clear").addEventListener("click", () => {
      if (!confirm("Clear current hunt results?")) return;
      leads = [];
      dups = 0;
      renderLeads();
      updateStats();
    });
    $("prof-save").addEventListener("click", saveProfile);

    setMode("sell");
    showPanel("hunt", "sell");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
