(function () {
  "use strict";

  const REGISTRY_KEY = "jobmind.hunted.registry.v1";
  const LEADS_KEY = "jobmind.hunted.leads.v1";
  const PROFILE_KEY = "jobmind.mobile.profile.v1";
  const SKIP_DOMAINS = new Set([
    "example.com", "test.com", "github.com", "google.com", "noreply.com",
    "sentry.io", "w3.org", "schema.org", "cloudflare.com", "render.com"
  ]);
  const GH_QUERIES = [
    "freelance developer email hire",
    "python developer freelance email",
    "react developer freelance email",
    "shopify developer email contact",
    "UI UX designer email contact hire",
    "digital marketer email whatsapp hire",
    "wordpress developer email hire",
    "fullstack developer freelance email"
  ];
  const UA = "JobMindMatch/2.4 (Android; LeadHunter)";
  const DEFAULT_PANEL = { job: "search", sell: "hunt" };
  const PANEL_TITLES = {
    job: { search: "Job Search", profile: "CV & Profile", links: "Quick Links" },
    sell: { hunt: "Lead Hunter", leads: "Lead Tracker", pitch: "Sales Pitch" }
  };
  const EXPORT_FOLDER = "JobMind-Match";
  const GH_HDR = { Accept: "application/vnd.github.v3+json", "User-Agent": UA };
  const SITE_PATHS = ["/", "/contact", "/about", "/hire", "/freelancers"];

  let huntData = { summary: { total: 212 }, platforms: [], hunt_plan: [] };
  let platformMap = {};
  let leads = [];
  let emails = new Set();
  let was = new Set();
  let dups = 0;
  let running = false;
  let halt = false;
  let uiMode = "sell";
  let sellPanel = "hunt";
  let jobPanel = "search";
  let exportOpen = false;
  let filterQuery = "";
  let filterSrc = "";
  let navPushing = false;

  function $(id) { return document.getElementById(id); }

  function toast(msg, type) {
    const el = $("toast");
    if (!el) return;
    el.textContent = msg;
    el.className = "toast " + (type || "in");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), 2600);
  }

  function esc(s) {
    return String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

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

  function loadLeads() {
    try {
      const raw = localStorage.getItem(LEADS_KEY);
      if (raw) leads = JSON.parse(raw) || [];
    } catch (e) {
      leads = [];
    }
  }

  function saveLeads() {
    localStorage.setItem(LEADS_KEY, JSON.stringify(leads.slice(0, 500)));
  }

  function normWa(v) {
    return String(v || "").replace(/[\s\-()]/g, "");
  }

  function validEmail(e) {
    if (!e || !e.includes("@")) return false;
    const d = e.split("@")[1].toLowerCase();
    return !SKIP_DOMAINS.has(d) && !e.endsWith(".png") && e.length < 80;
  }

  function extractContacts(text) {
    const blob = String(text || "");
    const emailRe = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,7}/g;
    const foundEmails = [...new Set((blob.match(emailRe) || []).filter(validEmail))];
    const foundWa = [];
    const patterns = [
      /wa\.me\/(\d{7,15})/gi,
      /whatsapp\.com\/send\?phone=(\d{7,15})/gi,
      /(?:whatsapp|wa)[:\s\-]+(\+?[\d][\d\s\-]{9,14})/gi,
      /\+92[\s\-]?3\d{2}[\s\-]?\d{7}/g,
      /\+1[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}/g,
      /\+44[\s\-]?\d{10}/g,
      /\+91[\s\-]?\d{10}/g,
      /\+971[\s\-]?\d{9}/g
    ];
    patterns.forEach((re) => {
      let m;
      while ((m = re.exec(blob)) !== null) {
        const raw = (m[1] || m[0] || "").replace(/[\s\-()]/g, "");
        const n = raw.replace(/[^\d+]/g, "");
        if (n.replace(/\D/g, "").length >= 10) {
          foundWa.push(n.startsWith("+") ? n : (n.length > 10 && n.startsWith("92") ? "+" + n : "+" + n.replace(/^\+/, "")));
        }
      }
    });
    return { emails: foundEmails, whatsapp: [...new Set(foundWa.map(normWa))] };
  }

  function matchesCountry(text, cc) {
    if (!cc) return true;
    const t = (text || "").toLowerCase();
    const c = cc.toLowerCase();
    return t.includes(c) || (c.includes("+92") && t.includes("pakistan")) || (c.includes("+1") && t.includes("usa"));
  }

  function addLeads(batch) {
    const cc = ($("hunt-cc")?.value || "").trim();
    let added = 0;
    for (const l of batch) {
      const blob = [l.email, l.whatsapp, l.notes, l.name].join(" ");
      if (cc && !matchesCountry(blob, cc)) continue;
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
    saveLeads();
    renderLeads();
    renderLeadsPanel();
    updateStats();
    refreshSourceFilter();
    return added;
  }

  function updateStats() {
    $("stat-total").textContent = leads.length;
    $("stat-email").textContent = leads.filter((l) => l.email).length;
    $("stat-wa").textContent = leads.filter((l) => l.whatsapp).length;
    $("stat-known").textContent = emails.size + was.size;
    $("stat-dup").textContent = dups;
    $("platform-count").textContent = huntData.summary?.total || 212;
  }

  function log(msg) {
    const el = $("hunt-log");
    if (!el) return;
    el.innerHTML += "› " + esc(msg) + "<br>";
    el.scrollTop = el.scrollHeight;
  }

  function setProg(pct, status) {
    $("prog-fill").style.width = Math.min(pct, 99) + "%";
    $("prog-pct").textContent = Math.min(Math.round(pct), 99) + "%";
    if (status) $("prog-status").textContent = status;
  }

  async function fetchText(url, headers) {
    const res = await fetch(url, { headers: { "User-Agent": UA, ...(headers || {}) }, cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    return res.text();
  }

  async function fetchJson(url, headers) {
    const res = await fetch(url, { headers: { "User-Agent": UA, ...(headers || {}) }, cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  }

  function leadFromText(name, designation, source, url, text) {
    const ex = extractContacts(text);
    if (!ex.emails.length && !ex.whatsapp.length) return null;
    return {
      name: name || "Unknown",
      designation: designation || "",
      email: ex.emails[0] || "",
      whatsapp: ex.whatsapp[0] || "",
      source,
      url: url || "",
      notes: String(text || "").slice(0, 100)
    };
  }

  async function huntGithubPlatform(platform, offset, kw) {
    const query = kw ? kw + " freelance email" : (platform.query || GH_QUERIES[(platform.query_index || offset) % GH_QUERIES.length]);
    const page = (offset % 3) + 1;
    const out = [];
    const search = await fetchJson(
      "https://api.github.com/search/users?q=" + encodeURIComponent(query) + "&per_page=12&page=" + page,
      GH_HDR
    );
    for (const u of (search.items || []).slice(0, 8)) {
      try {
        const p = await fetchJson("https://api.github.com/users/" + u.login, GH_HDR);
        const blob = [p.email, p.bio, p.blog, p.location, p.company, p.html_url].filter(Boolean).join(" ");
        const item = leadFromText(p.name || p.login, "Developer", "GitHub", p.html_url, blob);
        if (item) out.push(item);
        await delay(300);
      } catch (e) { /* skip */ }
    }
    return out;
  }

  async function huntGithubReadme(kw, offset) {
    const query = kw || GH_QUERIES[offset % GH_QUERIES.length];
    const page = Math.floor(offset / 3) + 1;
    const out = [];
    const search = await fetchJson(
      "https://api.github.com/search/repositories?q=" + encodeURIComponent(query + " email in:readme") + "&per_page=12&page=" + page + "&sort=updated",
      GH_HDR
    );
    for (const repo of (search.items || []).slice(0, 6)) {
      const owner = repo.owner?.login || "";
      const rname = repo.name || "";
      for (const branch of ["main", "master"]) {
        try {
          const txt = await fetchText("https://raw.githubusercontent.com/" + owner + "/" + rname + "/" + branch + "/README.md", GH_HDR);
          const item = leadFromText(owner, "Developer", "GitHub README", repo.html_url, txt);
          if (item) out.push(item);
          break;
        } catch (e) { /* try next branch */ }
      }
      await delay(250);
    }
    return out;
  }

  async function huntGithubIssues() {
    const data = await fetchJson(
      "https://api.github.com/search/issues?q=freelance+email+hire+label:hiring&sort=created&order=desc&per_page=20",
      GH_HDR
    );
    const out = [];
    (data.items || []).slice(0, 12).forEach((issue) => {
      const blob = [issue.title, issue.body || ""].join(" ");
      const item = leadFromText(issue.user?.login || "GitHub", "Hiring issue", "GitHub Issues", issue.html_url, blob);
      if (item) out.push(item);
    });
    return out;
  }

  async function huntRedditRss(sub) {
    const out = [];
    const xml = await fetchText("https://www.reddit.com/r/" + sub + "/new/.rss?limit=40", {
      Accept: "application/rss+xml, application/xml, text/xml",
      "User-Agent": "Mozilla/5.0 (compatible; RSS reader)"
    });
    const doc = new DOMParser().parseFromString(xml, "text/xml");
    doc.querySelectorAll("entry, item").forEach((entry) => {
      const title = entry.querySelector("title")?.textContent || "";
      const content = entry.querySelector("content, description")?.textContent || "";
      const link = entry.querySelector("link")?.getAttribute("href") || entry.querySelector("link")?.textContent || "";
      const author = entry.querySelector("author name, author")?.textContent || "";
      const item = leadFromText(author || title.slice(0, 60), "Reddit r/" + sub, "Reddit r/" + sub, link, title + " " + content);
      if (item) out.push(item);
    });
    return out;
  }

  async function huntDevto(tag, offset) {
    const page = (offset % 3) + 1;
    const data = await fetchJson("https://dev.to/api/articles?tag=" + encodeURIComponent(tag) + "&per_page=15&page=" + page);
    const out = [];
    for (const a of (data || []).slice(0, 6)) {
      try {
        let blob = [a.title, a.description, a.url, a.user?.username].join(" ");
        if (a.id) {
          const full = await fetchJson("https://dev.to/api/articles/" + a.id);
          blob += " " + (full.body_markdown || full.body_html || "");
        }
        const item = leadFromText(a.user?.name || a.title?.slice(0, 40), "Dev.to", "Dev.to", a.url, blob);
        if (item) out.push(item);
        await delay(200);
      } catch (e) { /* skip */ }
    }
    return out;
  }

  async function huntRss(label, url) {
    if (!url) return [];
    const xml = await fetchText(url, { Accept: "application/rss+xml, application/xml, text/xml" });
    const doc = new DOMParser().parseFromString(xml, "text/xml");
    const out = [];
    doc.querySelectorAll("item, entry").forEach((item) => {
      const title = item.querySelector("title")?.textContent || "";
      const desc = item.querySelector("description, summary, content")?.textContent || "";
      const link = item.querySelector("link")?.getAttribute("href") || item.querySelector("link")?.textContent || "";
      const row = leadFromText(title.slice(0, 50), label, label, link, title + " " + desc);
      if (row) out.push(row);
    });
    return out;
  }

  async function huntHNDeep() {
    const out = [];
    const queries = ["Ask HN Who is hiring", "freelancer email contact"];
    for (const q of queries) {
      const data = await fetchJson("https://hn.algolia.com/api/v1/search?query=" + encodeURIComponent(q) + "&tags=story&hitsPerPage=2");
      for (const hit of (data.hits || []).slice(0, 1)) {
        try {
          const story = await fetchJson("https://hacker-news.firebaseio.com/v0/item/" + hit.objectID + ".json");
          const kids = (story.kids || []).slice(0, 25);
          for (const kid of kids) {
            try {
              const k = await fetchJson("https://hacker-news.firebaseio.com/v0/item/" + kid + ".json");
              const blob = (k.text || "").replace(/<[^>]+>/g, " ");
              const item = leadFromText(k.by || "HN", "HN comment", "Hacker News", "https://news.ycombinator.com/item?id=" + k.id, blob);
              if (item) out.push(item);
              await delay(80);
            } catch (e) { /* skip */ }
          }
        } catch (e) { /* skip */ }
      }
    }
    return out;
  }

  async function huntIndieHackers() {
    try {
      const data = await fetchJson("https://www.indiehackers.com/api/posts?limit=25");
      const out = [];
      (data || []).forEach((p) => {
        const blob = [p.title, p.body, p.content, p.url].join(" ");
        const item = leadFromText(p.userDisplayName || p.title, "IndieHackers", "IndieHackers", p.url, blob);
        if (item) out.push(item);
      });
      return out;
    } catch (e) {
      return [];
    }
  }

  async function huntArbeitnow() {
    const data = await fetchJson("https://www.arbeitnow.com/api/job-board-api");
    const out = [];
    (data.data || []).slice(0, 30).forEach((job) => {
      const blob = [job.title, job.company_name, job.description, job.url].join(" ");
      const item = leadFromText(job.company_name || job.title, "Arbeitnow", "Arbeitnow", job.url, blob);
      if (item) out.push(item);
    });
    return out;
  }

  async function huntSite(domain, kw, offset) {
    if (!domain) return [];
    const path = SITE_PATHS[offset % SITE_PATHS.length];
    const query = kw || "freelance contact email whatsapp";
    const urls = ["https://" + domain + path, "https://www." + domain + path];
    for (const url of urls) {
      try {
        const html = await fetchText(url);
        const text = html.replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ") + " " + query;
        const ex = extractContacts(text);
        if (ex.emails.length || ex.whatsapp.length) {
          return ex.emails.slice(0, 3).map((email, i) => ({
            name: domain.split(".")[0],
            designation: "Marketplace",
            email,
            whatsapp: ex.whatsapp[i] || ex.whatsapp[0] || "",
            source: domain,
            url,
            notes: "Found on " + domain
          }));
        }
      } catch (e) { /* try next url */ }
    }
    return [];
  }

  async function runPlatform(platform, batchIndex) {
    const kw = ($("hunt-kw")?.value || "").trim();
    const type = platform.type;
    const offset = batchIndex;
    if (type === "github") return huntGithubPlatform(platform, offset, kw);
    if (type === "github_readme") return huntGithubReadme(kw, offset);
    if (type === "github_issues") return huntGithubIssues();
    if (type === "reddit") return huntRedditRss(platform.subreddit || "forhire");
    if (type === "devto") return huntDevto(platform.tag || "forhire", offset);
    if (type === "rss") return huntRss(platform.name, platform.feed_url);
    if (type === "hackernews") return huntHNDeep();
    if (type === "indiehackers") return huntIndieHackers();
    if (type === "remotive") return huntRss("Remotive", "https://remotive.com/remote-jobs/feed");
    if (type === "weworkremotely") return huntRss("WeWorkRemotely", "https://weworkremotely.com/remote-jobs.rss");
    if (type === "arbeitnow") return huntArbeitnow();
    if (type === "site") return huntSite(platform.site, kw, offset);
    return [];
  }

  function delay(ms) { return new Promise((r) => setTimeout(r, ms)); }

  function enabledChips() {
    return [...document.querySelectorAll(".chip[data-chip]")].filter((c) => c.classList.contains("on")).map((c) => c.dataset.chip);
  }

  function chipEnabled(chip) {
    const chips = new Set(enabledChips());
    if (chips.has(chip)) return true;
    if (chips.has("misc") && (chip === "misc" || chip === "indiehackers")) return true;
    return false;
  }

  function indexPlatforms() {
    platformMap = {};
    (huntData.platforms || []).forEach((p) => { platformMap[p.id] = p; });
  }

  function buildPlan() {
    const plan = [];
    for (const platform of (huntData.platforms || [])) {
      if (!chipEnabled(platform.chip)) continue;
      plan.push({
        platform,
        label: platform.name,
        batches: platform.batches || 1
      });
    }
    if (plan.length) return plan;
    return [{
      platform: { type: "github", query: GH_QUERIES[0], query_index: 0 },
      label: "GitHub",
      batches: 2
    }];
  }

  async function startHunt() {
    if (running) return;
    running = true;
    halt = false;
    $("hunt-start").disabled = true;
    $("hunt-stop").style.display = "";
    $("hunt-prog").classList.remove("hidden");
    $("hunt-log").innerHTML = "";
    const plan = buildPlan();
    const totalSteps = plan.reduce((n, p) => n + (p.batches || 1), 0);
    let step = 0;
    log("Hunting " + plan.length + " platforms (" + (huntData.summary?.total || 212) + " total registry)");
    toast("Hunt started — " + plan.length + " sources", "in");
    for (const item of plan) {
      if (halt) break;
      for (let b = 0; b < (item.batches || 1); b++) {
        if (halt) break;
        step++;
        setProg((step / totalSteps) * 100, item.label + "…");
        try {
          const batch = await runPlatform(item.platform, b);
          const added = addLeads(batch);
          log(item.label + ": +" + added + " new (" + (batch?.length || 0) + " raw)");
        } catch (e) {
          log(item.label + ": skip (" + (e.message || "error") + ")");
        }
        await delay(450);
      }
    }
    setProg(100, "Done — " + leads.length + " contacts");
    running = false;
    $("hunt-start").disabled = false;
    $("hunt-stop").style.display = "none";
    toast("Hunt done — " + leads.length + " leads", "ok");
  }

  function stopHunt() {
    halt = true;
    toast("Stopping hunt…", "in");
  }

  function filteredLeads() {
    const q = filterQuery.toLowerCase();
    return leads.filter((l) => {
      const blob = [l.name, l.email, l.whatsapp, l.source, l.designation].join(" ").toLowerCase();
      const matchQ = !q || blob.includes(q);
      const matchS = !filterSrc || l.source === filterSrc;
      return matchQ && matchS;
    });
  }

  function rowHtml(l, i, actions) {
    const em = l.email ? '<a href="mailto:' + esc(l.email) + '">' + esc(l.email) + '</a>' : "—";
    const wa = l.whatsapp ? '<a href="https://wa.me/' + l.whatsapp.replace(/\D/g, "") + '" target="_blank" rel="noopener">' + esc(l.whatsapp) + "</a>" : "—";
    const act = actions
      ? '<button class="btn sm ghost" data-copy="' + esc(l.email || l.whatsapp) + '">📋</button>'
      : "";
    return "<tr><td>" + (i + 1) + "</td><td>" + esc(l.name) + "</td><td>" + em + "</td><td>" + wa + "</td><td>" + esc(l.source) + "</td>" + (actions ? "<td>" + act + "</td>" : "") + "</tr>";
  }

  function renderLeads() {
    const tb = $("lead-tbody");
    if (!tb) return;
    if (!leads.length) {
      tb.innerHTML = '<tr><td colspan="6" class="hint">Tap Start Hunting — runs on your phone.</td></tr>';
      return;
    }
    tb.innerHTML = leads.slice(0, 150).map((l, i) => rowHtml(l, i, true)).join("");
    tb.querySelectorAll("[data-copy]").forEach((btn) => {
      btn.addEventListener("click", () => copyText(btn.dataset.copy));
    });
  }

  function renderLeadsPanel() {
    const tb = $("leads-tbody");
    const list = filteredLeads();
    $("lead-filter-count").textContent = list.length + " shown / " + leads.length + " total";
    if (!tb) return;
    if (!list.length) {
      tb.innerHTML = '<tr><td colspan="5" class="hint">No leads match filter.</td></tr>';
      return;
    }
    tb.innerHTML = list.map((l, i) => rowHtml(l, i, false)).join("");
  }

  function refreshSourceFilter() {
    const sel = $("lead-filter-src");
    if (!sel) return;
    const cur = sel.value;
    const sources = [...new Set(leads.map((l) => l.source).filter(Boolean))].sort();
    sel.innerHTML = '<option value="">All sources</option>' + sources.map((s) => '<option value="' + esc(s) + '">' + esc(s) + "</option>").join("");
    sel.value = cur;
  }

  function exportBaseName() {
    const fname = ($("hunt-fname")?.value || "leads").trim().replace(/[^\w\-]/g, "_") || "leads";
    const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, "");
    return fname + "_" + ts;
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const raw = String(reader.result || "");
        resolve(raw.includes(",") ? raw.split(",")[1] : raw);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  async function saveFile(blob, filename) {
    const Fs = window.Capacitor?.Plugins?.Filesystem;
    const Share = window.Capacitor?.Plugins?.Share;
    const path = EXPORT_FOLDER + "/" + filename;

    if (Fs) {
      try {
        const data = await blobToBase64(blob);
        await Fs.writeFile({
          path,
          data,
          directory: "DOCUMENTS",
          recursive: true
        });
        let shareUri = "";
        try {
          const uriResult = await Fs.getUri({ path, directory: "DOCUMENTS" });
          shareUri = uriResult?.uri || "";
        } catch (e) { /* optional */ }
        toast("Saved → Files → Documents → " + EXPORT_FOLDER, "ok");
        if (Share && shareUri) {
          try {
            await Share.share({
              title: filename,
              text: "JobMind export — tap Save to Downloads or share",
              url: shareUri,
              dialogTitle: "Save / Share " + filename
            });
          } catch (e) { /* user closed share sheet */ }
        }
        return;
      } catch (e) {
        toast("Save failed — " + (e.message || "try again"), "er");
      }
    }

    try {
      if (navigator.share && navigator.canShare) {
        const file = new File([blob], filename, { type: blob.type });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ files: [file], title: "JobMind Export" });
          toast("Pick Save to Downloads in share menu", "ok");
          return;
        }
      }
    } catch (e) { /* fallback */ }

    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    toast("Saved " + filename, "ok");
  }

  function exportLeads(fmt) {
    closeExportMenu();
    if (!leads.length) { toast("No contacts to export!", "er"); return; }
    const base = exportBaseName();
    const rows = leads.map((l, i) => [i + 1, l.name || "", l.designation || "", l.email || "", l.whatsapp || "", l.source || "", l.url || "", l.notes || ""]);
    const hdr = ["#", "Name", "Designation", "Email", "WhatsApp", "Source", "Profile URL", "Notes"];
    let blob, filename;

    if (fmt === "csv") {
      const escv = (v) => '"' + String(v).replace(/"/g, '""') + '"';
      const csv = [hdr, ...rows].map((r) => r.map(escv).join(",")).join("\n");
      blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      filename = base + ".csv";
    } else if (fmt === "json") {
      blob = new Blob([JSON.stringify(leads, null, 2)], { type: "application/json" });
      filename = base + ".json";
    } else if (fmt === "txt_email") {
      blob = new Blob([leads.filter((l) => l.email).map((l) => l.email).join("\n")], { type: "text/plain" });
      filename = base + "_emails.txt";
    } else if (fmt === "txt_wa") {
      blob = new Blob([leads.filter((l) => l.whatsapp).map((l) => l.whatsapp).join("\n")], { type: "text/plain" });
      filename = base + "_whatsapp.txt";
    } else if (fmt === "xls") {
      const th = hdr.map((h) => '<th style="background:#7c3aed;color:#fff;padding:8px">' + h + "</th>").join("");
      const tr = rows.map((r) => "<tr>" + r.map((c) => "<td>" + esc(c) + "</td>").join("") + "</tr>").join("");
      const xls = '<html><head><meta charset="UTF-8"></head><body><table border="1" style="border-collapse:collapse">' + "<tr>" + th + "</tr>" + tr + "</table></body></html>";
      blob = new Blob([xls], { type: "application/vnd.ms-excel" });
      filename = base + ".xls";
    } else if (fmt === "html") {
      const cards = leads.map((l, i) => {
        const em = l.email ? '<a href="mailto:' + esc(l.email) + '">' + esc(l.email) + "</a><br>" : "";
        const wa = l.whatsapp ? '<a href="https://wa.me/' + l.whatsapp.replace(/\D/g, "") + '">' + esc(l.whatsapp) + "</a><br>" : "";
        return '<div style="border:1px solid #7c3aed;border-radius:10px;padding:14px;margin:8px;min-width:220px;display:inline-block;vertical-align:top;background:#0e0e1c;color:#eee"><b>#' + (i + 1) + " " + esc(l.name) + '</b><div style="font-size:11px;color:#a07cfc;margin:6px 0">' + esc(l.designation) + "</div>" + em + wa + '<div style="font-size:10px;color:#666">' + esc(l.source) + "</div></div>";
      }).join("");
      const html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Lead Hunter</title></head><body style='background:#080812;padding:20px;font-family:sans-serif'><h2 style='color:#c084fc'>Lead Hunter — " + leads.length + " Contacts</h2>" + cards + "</body></html>";
      blob = new Blob([html], { type: "text/html" });
      filename = base + ".html";
    } else {
      toast("Unknown format", "er");
      return;
    }
    saveFile(blob, filename);
  }

  function copyText(text) {
    if (!text) { toast("Nothing to copy", "er"); return; }
    navigator.clipboard.writeText(text).then(() => toast("Copied!", "ok")).catch(() => toast("Copy failed", "er"));
  }

  function copyAllEmails() {
    const e = leads.filter((l) => l.email).map((l) => l.email).join("\n");
    if (!e) { toast("No emails!", "er"); return; }
    copyText(e);
  }

  function copyAllWa() {
    const w = leads.filter((l) => l.whatsapp).map((l) => l.whatsapp).join("\n");
    if (!w) { toast("No WhatsApp numbers!", "er"); return; }
    copyText(w);
  }

  function toggleExportMenu() {
    exportOpen = !exportOpen;
    $("export-menu").classList.toggle("hidden", !exportOpen);
  }

  function closeExportMenu() {
    exportOpen = false;
    $("export-menu")?.classList.add("hidden");
  }

  function updateHeaderTitle() {
    const panel = uiMode === "sell" ? sellPanel : jobPanel;
    $("header-title").textContent = (PANEL_TITLES[uiMode] && PANEL_TITLES[uiMode][panel]) || "JobMind Match";
  }

  function setMode(mode, skipHistory) {
    uiMode = mode;
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
    document.querySelectorAll(".panel[data-mode-panel]").forEach((p) => {
      p.classList.toggle("active", p.dataset.modePanel === mode);
    });
    document.querySelectorAll(".nav-group").forEach((g) => {
      g.classList.toggle("active", g.dataset.navMode === mode);
    });
    showPanel(mode === "sell" ? sellPanel : jobPanel, mode, skipHistory);
  }

  function pushNavState(mode, panelId) {
    if (navPushing) return;
    const hash = mode + "/" + panelId;
    if (location.hash === "#" + hash) return;
    history.pushState({ mode, panel: panelId }, "", "#" + hash);
  }

  function showPanel(panelId, mode, skipHistory) {
    if (mode === "sell") sellPanel = panelId;
    else jobPanel = panelId;
    document.querySelectorAll(".panel[data-mode-panel='" + mode + "'] .subpanel").forEach((p) => {
      p.classList.toggle("active", p.dataset.panel === panelId);
    });
    document.querySelectorAll(".nav-group[data-nav-mode='" + mode + "'] .nav-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.panel === panelId);
    });
    updateHeaderTitle();
    if (panelId === "leads") renderLeadsPanel();
    if (panelId === "pitch") updatePitchPreview();
    if (!skipHistory) pushNavState(mode, panelId);
  }

  function handleBack() {
    if (exportOpen) { closeExportMenu(); return true; }
    if (running) { stopHunt(); return true; }
    const panel = uiMode === "sell" ? sellPanel : jobPanel;
    const def = DEFAULT_PANEL[uiMode];
    if (panel !== def) {
      navPushing = true;
      showPanel(def, uiMode, true);
      history.replaceState({ mode: uiMode, panel: def }, "", "#" + uiMode + "/" + def);
      navPushing = false;
      toast("Back to " + PANEL_TITLES[uiMode][def], "in");
      return true;
    }
    if (uiMode === "sell") {
      navPushing = true;
      setMode("job", true);
      history.replaceState({ mode: "job", panel: jobPanel }, "", "#job/" + jobPanel);
      navPushing = false;
      toast("Job Search mode", "in");
      return true;
    }
    const App = window.Capacitor?.Plugins?.App;
    if (App?.minimizeApp) {
      App.minimizeApp();
      return true;
    }
    if (App?.exitApp) {
      App.exitApp();
      return true;
    }
    if (history.length > 1) {
      history.back();
      return true;
    }
    return false;
  }

  function wireBackButton() {
    $("btn-back")?.addEventListener("click", (e) => {
      e.preventDefault();
      handleBack();
    });

    window.addEventListener("popstate", (e) => {
      if (!e.state || !e.state.mode) {
        handleBack();
        return;
      }
      navPushing = true;
      uiMode = e.state.mode;
      if (e.state.mode === "sell") sellPanel = e.state.panel;
      else jobPanel = e.state.panel;
      document.querySelectorAll(".mode-btn").forEach((b) => b.classList.toggle("active", b.dataset.mode === uiMode));
      document.querySelectorAll(".panel[data-mode-panel]").forEach((p) => {
        p.classList.toggle("active", p.dataset.modePanel === uiMode);
      });
      document.querySelectorAll(".nav-group").forEach((g) => {
        g.classList.toggle("active", g.dataset.navMode === uiMode);
      });
      showPanel(e.state.panel, e.state.mode, true);
      navPushing = false;
    });

    function registerCapBack() {
      const App = window.Capacitor?.Plugins?.App;
      if (!App?.addListener) return false;
      App.addListener("backButton", () => handleBack());
      return true;
    }

    if (!registerCapBack()) {
      const timer = setInterval(() => {
        if (registerCapBack()) clearInterval(timer);
      }, 250);
      setTimeout(() => clearInterval(timer), 6000);
    }
    document.addEventListener("backbutton", (e) => {
      e.preventDefault();
      handleBack();
    }, false);
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
    updatePitchPreview();
    toast("Profile saved", "ok");
  }

  function loadProfile() {
    try {
      const p = JSON.parse(localStorage.getItem(PROFILE_KEY) || "{}");
      if (p.name) $("prof-name").value = p.name;
      if (p.email) $("prof-email").value = p.email;
      if (p.skills) $("prof-skills").value = p.skills;
      if (p.pitch) $("prof-pitch").value = p.pitch;
    } catch (e) { /* ignore */ }
    updatePitchPreview();
  }

  function updatePitchPreview() {
    const p = JSON.parse(localStorage.getItem(PROFILE_KEY) || "{}");
    const el = $("pitch-preview");
    if (!el) return;
    if (p.pitch) {
      el.textContent = (p.name ? p.name + "\n\n" : "") + p.pitch + (p.skills ? "\n\nSkills: " + p.skills : "");
      el.classList.remove("hint");
    }
  }

  async function init() {
    loadRegistry();
    loadLeads();
    loadProfile();
    try {
      const res = await fetch("data/hunt-data.json", { cache: "no-store" });
      if (res.ok) {
        huntData = await res.json();
        indexPlatforms();
      }
    } catch (e) { /* defaults */ }
    updateStats();
    renderLeads();
    renderLeadsPanel();
    refreshSourceFilter();
    wireBackButton();

    document.querySelectorAll(".chip[data-chip]").forEach((chip) => {
      chip.addEventListener("click", () => chip.classList.toggle("on"));
    });
    document.querySelectorAll(".mode-btn").forEach((b) => {
      b.addEventListener("click", () => setMode(b.dataset.mode));
    });
    document.querySelectorAll(".nav-btn").forEach((b) => {
      b.addEventListener("click", () => showPanel(b.dataset.panel, b.dataset.navMode));
    });
    $("hunt-start")?.addEventListener("click", startHunt);
    $("hunt-stop")?.addEventListener("click", stopHunt);
    $("hunt-export-btn")?.addEventListener("click", toggleExportMenu);
    document.querySelectorAll("#export-menu [data-fmt]").forEach((btn) => {
      btn.addEventListener("click", () => exportLeads(btn.dataset.fmt));
    });
    $("hunt-copy-emails")?.addEventListener("click", copyAllEmails);
    $("hunt-copy-wa")?.addEventListener("click", copyAllWa);
    $("hunt-clear")?.addEventListener("click", () => {
      if (!confirm("Clear current session leads? (Saved registry stays forever)")) return;
      leads = [];
      dups = 0;
      saveLeads();
      renderLeads();
      renderLeadsPanel();
      updateStats();
      toast("Session cleared", "in");
    });
    $("prof-save")?.addEventListener("click", saveProfile);
    $("pitch-copy")?.addEventListener("click", () => {
      const p = JSON.parse(localStorage.getItem(PROFILE_KEY) || "{}");
      copyText(p.pitch || "");
    });
    $("lead-search")?.addEventListener("input", (e) => {
      filterQuery = e.target.value;
      renderLeadsPanel();
    });
    $("lead-filter-src")?.addEventListener("change", (e) => {
      filterSrc = e.target.value;
      renderLeadsPanel();
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".export-wrap")) closeExportMenu();
    });

    setMode("sell", true);
    showPanel("hunt", "sell", true);
    history.replaceState({ mode: "sell", panel: "hunt" }, "", "#sell/hunt");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
