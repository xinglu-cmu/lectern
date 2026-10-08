/* Lectern local review UI. Vanilla JS, no build step: report → selection → export. */
(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const api = async (method, url, body, raw) => {
    const r = await fetch(url, {
      method,
      headers: body instanceof FormData || body === undefined ? {} : { "content-type": "application/json" },
      body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
    });
    if (!r.ok) {
      let msg = r.statusText;
      try { msg = (await r.json()).detail || msg; } catch (e) {}
      throw new Error(msg);
    }
    return raw ? r.text() : r.status === 204 ? null : r.json();
  };
  const ZONES = ["task", "background", "example", "structure", "unknown", "ai_policy", "ai_directive", "hidden"];
  const NEVER = new Set(["hidden", "ai_directive", "ai_policy"]);
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const zoneTag = z => `<span class="zone" style="background:var(--${z})">${z}</span>`;

  const state = { id: null, data: null, review: null, tab: "report", preview: "" };

  // ---------------------------------------------------------------- upload
  const drop = $("#drop"), fileInput = $("#file");
  drop.addEventListener("click", () => fileInput.click());
  drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => { if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); });
  fileInput.addEventListener("change", () => { if (fileInput.files[0]) upload(fileInput.files[0]); fileInput.value = ""; });

  async function upload(file) {
    const fd = new FormData(); fd.append("file", file);
    $("#uploadStatus").textContent = `Uploading ${file.name}…`;
    try {
      const { id } = await api("POST", "/api/analyses", fd);
      $("#uploadStatus").textContent = "Analyzing…";
      await loadHistory();
      await open(id);
      watch(id);
    } catch (err) { $("#uploadStatus").innerHTML = `<span class="err">${esc(err.message)}</span>`; }
  }

  function watch(id) {
    const es = new EventSource(`/api/analyses/${id}/events`);
    es.addEventListener("status", async e => {
      const { status } = JSON.parse(e.data);
      if (status === "ready" || status === "failed") { es.close(); $("#uploadStatus").textContent = ""; await loadHistory(); if (state.id === id) await open(id); }
    });
    es.onerror = () => es.close();
  }

  // --------------------------------------------------------------- history
  async function loadHistory() {
    const rows = await api("GET", "/api/analyses");
    $("#hist").innerHTML = rows.map(r => `<button data-id="${r.id}" class="${r.id === state.id ? "sel" : ""}">
      <span class="f">${esc(r.filename)}</span><span class="s">${r.status}${r.mode ? " · " + r.mode : ""} · ${r.created_at.slice(0, 16).replace("T", " ")}</span></button>`).join("")
      || `<span class="small">Nothing yet.</span>`;
  }
  $("#hist").addEventListener("click", e => { const b = e.target.closest("[data-id]"); if (b) open(b.dataset.id); });

  // ---------------------------------------------------------------- render
  async function open(id) {
    state.id = id; state.data = await api("GET", `/api/analyses/${id}`); state.review = state.data.review; state.preview = "";
    await loadHistory(); render();
  }

  function render() {
    const d = state.data, main = $("#main");
    if (!d) return;
    if (d.status !== "ready") {
      main.innerHTML = `<div class="card"><h2>${esc(d.filename)}</h2><p class="status">${d.status === "failed" ? `<span class="err">Failed: ${esc(d.error)}</span>` : "Analyzing on this machine…"}</p>${delBtn()}</div>`;
      return;
    }
    const a = d.analysis;
    main.innerHTML = `
      <div class="card">
        <h2>${esc(a.title || d.filename)}</h2>
        <div class="muted">${esc(d.filename)} · ${a.format}${a.pages ? ` · ${a.pages} pages` : ""} · ${a.segments.length} segments · zoning: ${a.mode}${a.llm ? ` (${esc(a.llm.model)}, $${a.llm.cost_usd.toFixed(4)})` : ""}</div>
        <div class="tabs" role="tablist">
          ${["report", "select", "export"].map(t => `<button role="tab" data-tab="${t}" aria-selected="${state.tab === t}">${{ report: "Report", select: "Choose what to keep", export: "Export" }[t]}</button>`).join("")}
        </div>
      </div>
      <div id="tab"></div>`;
    main.querySelector(".tabs").addEventListener("click", e => { const b = e.target.closest("[data-tab]"); if (b) { state.tab = b.dataset.tab; render(); } });
    ({ report: renderReport, select: renderSelect, export: renderExport })[state.tab]();
  }

  const delBtn = () => `<div class="actions"><button class="btn" id="del">Delete this analysis</button></div>`;
  function bindDelete() { const b = $("#del"); if (b) b.onclick = async () => { if (confirm("Delete this analysis and the stored file?")) { await api("DELETE", `/api/analyses/${state.id}`); state.id = null; state.data = null; $("#main").innerHTML = `<div class="card"><h2>Deleted.</h2></div>`; loadHistory(); } }; }

  function policyBanner(a) {
    const policies = a.findings.filter(f => f.kind === "ai_policy");
    if (!policies.length) return "";
    return `<div class="banner warn"><strong>This document states a rule about AI use.</strong>
      ${policies.map(f => `<div>“${esc(f.excerpt)}” <span class="small">(${f.page ? "p" + f.page + ", " : ""}${f.segment_id})</span></div>`).join("")}
      <label><input type="checkbox" id="ack" ${state.review.policy_acknowledged ? "checked" : ""}> I have read this rule. Exports stay disabled until it is acknowledged.</label></div>`;
  }

  function renderReport() {
    const a = state.data.analysis, el = $("#tab");
    const critical = [...new Set(a.findings.filter(f => f.severity === "critical").map(f => `${f.page}:${f.segment_id}`))]; // one hidden line = one item
    const shares = ZONES.filter(z => a.zone_shares[z]).map(z => [z, a.zone_shares[z]]);
    el.innerHTML = `
      ${a.overview ? `<div class="card"><h3>Overview · ${esc(a.overview.doc_type)}</h3><p>${esc(a.overview.overview)}</p></div>` : `<div class="card"><h3>Overview</h3><p class="muted">No model was available for this analysis (set ANTHROPIC_API_KEY and re-upload, or read the zone map below).</p></div>`}
      ${critical.length ? `<div class="banner crit"><strong>${critical.length} critical finding${critical.length > 1 ? "s" : ""}: hidden text addressed to an AI.</strong> Quarantined: never shown to a model, never in a clean copy.</div>` : ""}
      ${policyBanner(a)}
      <div class="card"><h3>Zone map</h3>
        <div class="bar">${shares.map(([z, s]) => `<i style="width:${(s * 100).toFixed(1)}%;background:var(--${z})" title="${z} ${(s * 100).toFixed(0)}%"></i>`).join("")}</div>
        <div class="legend">${shares.map(([z, s]) => `<span><i class="sw" style="background:var(--${z})"></i>${z} ${(s * 100).toFixed(0)}%</span>`).join("")}</div></div>
      <div class="card"><h3>Findings (${a.findings.length})</h3>
        ${a.findings.length ? `<table><tr><th>det.</th><th>kind</th><th>severity</th><th>status</th><th>where</th><th>excerpt</th><th></th></tr>
        ${a.findings.map((f, i) => { const st = state.review.findings[i] || f.status; return `<tr><td>${f.detector}</td><td>${f.kind}</td><td>${f.severity}</td><td>${st}</td><td>${f.page ? "p" + f.page + " " : ""}${f.segment_id || "doc"}</td><td>${esc(f.excerpt)}${f.note ? `<div class="small">${esc(f.note)}</div>` : ""}</td>
          <td>${f.status === "quarantined" ? "" : `<button class="btn" data-fi="${i}" data-st="${st === "dismissed" ? "open" : "dismissed"}">${st === "dismissed" ? "restore" : "dismiss"}</button>`}</td></tr>`; }).join("")}</table>` : `<p class="muted">None. No hidden text, AI-directed instructions or AI-use policy statements.</p>`}</div>
      <div class="card"><h3>Segments</h3><table><tr><th>id</th><th>page</th><th>zone</th><th>conf</th><th>via</th><th>section / first line</th></tr>
        ${a.segments.map(s => `<tr><td>${s.id}</td><td>${s.anchor.page_start ?? ""}</td><td>${zoneTag(s.zone)}</td><td>${s.confidence.toFixed(2)}</td><td>${s.method}</td><td><span class="small">${esc(s.heading_path.slice(-2).join(" › "))}</span> ${esc(firstLine(s.text))}</td></tr>`).join("")}</table></div>
      ${a.warnings.length ? `<div class="card">${a.warnings.map(w => `<div class="small">note: ${esc(w)}</div>`).join("")}</div>` : ""}
      <div class="card">${delBtn()}</div>`;
    el.addEventListener("click", async e => { const b = e.target.closest("[data-fi]"); if (b) { state.review.findings[b.dataset.fi] = b.dataset.st; await saveReview(); renderReport(); } });
    const ack = $("#ack"); if (ack) ack.onchange = async () => { state.review.policy_acknowledged = ack.checked; await saveReview(); };
    bindDelete();
  }

  const firstLine = t => { const l = t.split("\n").find(x => x.trim() && !x.startsWith("#")) || ""; return l.length > 110 ? l.slice(0, 109) + "…" : l; };

  function renderSelect() {
    const a = state.data.analysis, r = state.review, el = $("#tab");
    const keep = new Set(r.keep_zones);
    const present = ZONES.filter(z => a.segments.some(s => s.zone === z));
    el.innerHTML = `
      <div class="card"><h3>Keep these zones</h3>
        <div class="toggles">${present.map(z => NEVER.has(z) ? `<label title="never kept; listed in the report"><input type="checkbox" disabled> ${zoneTag(z)} never</label>` : `<label><input type="checkbox" data-z="${z}" ${keep.has(z) ? "checked" : ""}> ${zoneTag(z)}</label>`).join("")}</div>
        <p class="small">Hidden text and AI-directed or AI-policy text can never be kept; they are listed in the removal report.</p></div>
      <div class="card"><h3>Per segment</h3><p class="small">Untick to drop a segment, tick to keep one its zone would drop, or change its zone.</p>
        <div id="segs">${a.segments.map(s => {
          const dec = r.segments[s.id] || {}; const never = NEVER.has(s.zone);
          const on = dec.keep === true ? true : dec.keep === false ? false : keep.has(dec.zone || s.zone);
          return `<div class="seg ${on && !never ? "" : "off"}" data-sid="${s.id}">
            <input type="checkbox" data-keep="${s.id}" ${on && !never ? "checked" : ""} ${never ? "disabled" : ""}>
            <div>${never ? zoneTag(s.zone) : `<select data-zone="${s.id}">${ZONES.filter(z => !NEVER.has(z)).map(z => `<option ${(dec.zone || s.zone) === z ? "selected" : ""}>${z}</option>`).join("")}</select>`}</div>
            <div><div class="path">${s.id}${s.anchor.page_start ? " · p" + s.anchor.page_start : ""} · ${esc(s.heading_path.join(" › "))}</div><div class="t">${esc(s.text.slice(0, 600))}</div></div></div>`; }).join("")}</div></div>
      <div class="card"><h3>Preview of the clean copy</h3><div class="actions"><button class="btn" id="prev">Refresh preview</button></div><pre class="preview" id="preview">${esc(state.preview || "(press Refresh preview)")}</pre></div>`;
    el.querySelectorAll("[data-z]").forEach(cb => cb.onchange = async () => { cb.checked ? keep.add(cb.dataset.z) : keep.delete(cb.dataset.z); r.keep_zones = [...keep]; await saveReview(); renderSelect(); });
    el.querySelectorAll("[data-keep]").forEach(cb => cb.onchange = async () => { r.segments[cb.dataset.keep] = { ...(r.segments[cb.dataset.keep] || {}), keep: cb.checked }; await saveReview(); renderSelect(); });
    el.querySelectorAll("[data-zone]").forEach(sel => sel.onchange = async () => { r.segments[sel.dataset.zone] = { ...(r.segments[sel.dataset.zone] || {}), zone: sel.value }; await saveReview(); renderSelect(); });
    $("#prev").onclick = async () => { try { state.preview = await api("POST", `/api/analyses/${state.id}/exports`, { kind: "clean", dry_run: true, report: false }, true); } catch (err) { state.preview = "Cannot preview: " + err.message; } renderSelect(); };
  }

  function renderExport() {
    const a = state.data.analysis, el = $("#tab");
    const needsAck = a.findings.some(f => f.kind === "ai_policy") && !state.review.policy_acknowledged;
    el.innerHTML = `
      ${policyBanner(a)}
      <div class="card"><h3>Export</h3>
        <div class="actions">
          <button class="btn primary" data-kind="clean" ${needsAck ? "disabled" : ""}>clean.md (with removal report)</button>
          <button class="btn" data-kind="brief" ${needsAck ? "disabled" : ""}>brief.md</button>
          <button class="btn" data-kind="json">analysis.json</button></div>
        <p class="small">Files are generated on this machine and downloaded by your browser. ${state.data.exports.length ? `Previous exports: ${state.data.exports.map(x => x.kind).join(", ")}.` : ""}</p></div>`;
    const ack = $("#ack"); if (ack) ack.onchange = async () => { state.review.policy_acknowledged = ack.checked; await saveReview(); renderExport(); };
    el.querySelectorAll("[data-kind]").forEach(b => b.onclick = async () => {
      try {
        const text = await api("POST", `/api/analyses/${state.id}/exports`, { kind: b.dataset.kind }, true);
        const base = state.data.filename.replace(/\.[^.]+$/, "");
        download(`${base}.${b.dataset.kind === "json" ? "analysis.json" : b.dataset.kind + ".md"}`, text);
        state.data = await api("GET", `/api/analyses/${state.id}`); renderExport();
      } catch (err) { alert(err.message); }
    });
  }

  function download(name, text) {
    const blob = new Blob([text], { type: "text/plain" }), url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function saveReview() { state.review = await api("PUT", `/api/analyses/${state.id}/review`, state.review); }

  loadHistory();
})();
