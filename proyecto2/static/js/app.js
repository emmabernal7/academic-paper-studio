// Proyecto 2 - Frontend Application Logic
// Academic Paper Studio: Google Scholar + ORCID + Scopus

let currentMode = "articles";
let currentProfilesData = { unified: [], orcid: [], scholar: [], scopus: [] };
let activeProfileFilter = "all";

// 1. Initialization
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initApiConfig();
});

// 2. Dark Mode Toggle
function initTheme() {
  const isDark = localStorage.getItem("aps_theme") === "dark" || 
    (!localStorage.getItem("aps_theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
  setTheme(isDark);
}

function toggleTheme() {
  const isDark = document.documentElement.classList.contains("dark");
  setTheme(!isDark);
}

function setTheme(dark) {
  const sunIcon = document.getElementById("themeIconSun");
  const moonIcon = document.getElementById("themeIconMoon");
  if (dark) {
    document.documentElement.classList.add("dark");
    localStorage.setItem("aps_theme", "dark");
    if (sunIcon) sunIcon.classList.remove("hidden");
    if (moonIcon) moonIcon.classList.add("hidden");
  } else {
    document.documentElement.classList.remove("dark");
    localStorage.setItem("aps_theme", "light");
    if (sunIcon) sunIcon.classList.add("hidden");
    if (moonIcon) moonIcon.classList.remove("hidden");
  }
}

// 3. Mode Switcher (Articles vs Profiles)
function switchMode(mode) {
  currentMode = mode;
  const viewArticles = document.getElementById("viewArticles");
  const viewProfiles = document.getElementById("viewProfiles");
  const btnArticles = document.getElementById("btnModeArticles");
  const btnProfiles = document.getElementById("btnModeProfiles");

  if (mode === "articles") {
    viewArticles.classList.remove("hidden");
    viewProfiles.classList.add("hidden");
    
    btnArticles.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all bg-white dark:bg-slate-700 text-indigo-600 dark:text-cyan-400 shadow-sm";
    btnProfiles.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white";
  } else {
    viewArticles.classList.add("hidden");
    viewProfiles.classList.remove("hidden");
    
    btnProfiles.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all bg-white dark:bg-slate-700 text-indigo-600 dark:text-cyan-400 shadow-sm";
    btnArticles.className = "px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white";
  }
}

// 4. API Configuration Modal (Scopus Key)
function toggleConfigModal(open) {
  const modal = document.getElementById("configModal");
  if (open) {
    const savedKey = localStorage.getItem("aps_scopus_key") || "";
    document.getElementById("inputScopusKey").value = savedKey;
    modal.classList.remove("hidden");
  } else {
    modal.classList.add("hidden");
  }
}

function initApiConfig() {
  const savedKey = localStorage.getItem("aps_scopus_key");
  if (savedKey) {
    document.getElementById("inputScopusKey").value = savedKey;
  }
}

function saveApiConfig() {
  const key = document.getElementById("inputScopusKey").value.trim();
  localStorage.setItem("aps_scopus_key", key);
  toggleConfigModal(false);
  showToast("Clave de Scopus guardada con éxito");
}

function getScopusApiKey() {
  return localStorage.getItem("aps_scopus_key") || "";
}

// 5. Toast Notification
function showToast(msg) {
  const div = document.createElement("div");
  div.className = "fixed bottom-5 right-5 z-50 bg-slate-900 text-white border border-cyan-500/30 px-4 py-2.5 rounded-xl shadow-2xl text-xs font-semibold flex items-center gap-2 transition-opacity";
  div.innerHTML = `<span>⚡</span><span>${msg}</span>`;
  document.body.appendChild(div);
  setTimeout(() => {
    div.style.opacity = "0";
    setTimeout(() => div.remove(), 300);
  }, 3000);
}

// ==========================================
// MODO 1: BÚSQUEDA DE ARTÍCULOS (GOOGLE SCHOLAR)
// ==========================================
async function handleArticleSearch(e) {
  e.preventDefault();
  const query = document.getElementById("articleQuery").value.trim();
  if (!query) return;

  const yearLow = document.getElementById("yearLow").value.trim();
  const yearHigh = document.getElementById("yearHigh").value.trim();
  const limit = parseInt(document.getElementById("articleLimit").value) || 10;

  const btn = document.getElementById("btnSearchArticles");
  const list = document.getElementById("articlesList");
  const countLabel = document.getElementById("articlesResultsCount");

  btn.disabled = true;
  btn.innerHTML = `<span class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-1"></span> Buscando en Scholar...`;
  list.innerHTML = `
    <div class="text-center py-16">
      <div class="animate-spin inline-block w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full mb-3"></div>
      <p class="text-xs text-slate-500 font-medium">Consultando Google Scholar para "${escapeHtml(query)}"...</p>
    </div>
  `;

  try {
    const resp = await fetch("/api/scholar/articles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit, year_low: yearLow || null, year_high: yearHigh || null })
    });
    const data = await resp.json();

    if (data.success && data.articles && data.articles.length > 0) {
      countLabel.textContent = `Se encontraron ${data.articles.length} artículos en Google Scholar`;
      renderArticles(data.articles);
    } else {
      countLabel.textContent = `0 resultados`;
      list.innerHTML = `
        <div class="text-center py-12 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
          <p class="text-sm text-slate-500">No se encontraron artículos para tu consulta. Prueba con otros términos.</p>
        </div>
      `;
    }
  } catch (err) {
    list.innerHTML = `
      <div class="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-500 rounded-xl text-xs">
        Error al buscar en Google Scholar: ${err.message}
      </div>
    `;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Buscar Artículos</span>`;
  }
}

function renderArticles(articles) {
  const list = document.getElementById("articlesList");
  list.innerHTML = "";

  articles.forEach((art) => {
    const card = document.createElement("div");
    card.className = "p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm hover:shadow-md transition-shadow space-y-3";

    // Citation badge
    const citCount = art.citations || 0;
    const citBadge = citCount > 0 
      ? `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">⭐ ${citCount} citas</span>`
      : `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-500">Sin citas</span>`;

    // Year badge
    const yearBadge = art.year 
      ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono">${art.year}</span>`
      : "";

    // PDF Free link
    const pdfBtn = art.eprint_url 
      ? `<a href="${art.eprint_url}" target="_blank" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 flex items-center gap-1">📄 PDF Scholar</a>`
      : "";

    // DOI or Publisher button
    const pubBtn = art.url 
      ? `<a href="${art.url}" target="_blank" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 flex items-center gap-1">🔗 Ver en Editorial</a>`
      : "";

    // Download in APS button (extracts possible DOI or title search)
    const dlApsBtn = `<button onclick="sendToApsDownloader('${escapeAttr(art.title)}', '${escapeAttr(art.url)}')" class="px-3 py-1 text-xs font-bold rounded-lg bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white shadow-sm flex items-center gap-1.5">⚡ Descargar con APS</button>`;

    // Authors string
    const authorsStr = art.authors && art.authors.length > 0 
      ? art.authors.slice(0, 5).join(", ") + (art.authors.length > 5 ? " et al." : "")
      : "Autor desconocido";

    card.innerHTML = `
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div class="space-y-1 flex-1 min-w-[280px]">
          <div class="flex items-center gap-2 flex-wrap">
            ${yearBadge}
            ${citBadge}
            <span class="text-xs text-slate-400 italic">${art.venue || art.publisher || "Publicación"}</span>
          </div>
          <h4 class="text-base font-bold text-slate-900 dark:text-white leading-snug hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors">
            <a href="${art.url || '#'}" target="_blank">${escapeHtml(art.title)}</a>
          </h4>
          <p class="text-xs font-medium text-slate-500 dark:text-slate-400">${escapeHtml(authorsStr)}</p>
        </div>
      </div>

      ${art.abstract ? `<p class="text-xs text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed bg-slate-50 dark:bg-slate-950/40 p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/60">${escapeHtml(art.abstract)}</p>` : ""}

      <div class="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800/60 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          ${pubBtn}
          ${pdfBtn}
        </div>
        <div>
          ${dlApsBtn}
        </div>
      </div>
    `;

    list.appendChild(card);
  });
}

function sendToApsDownloader(title, url) {
  // Try extracting DOI from URL
  let doiMatch = null;
  if (url) {
    const m = url.match(/10\.\d{4,9}\/[-._;()/:A-Za-z0-9]+/);
    if (m) doiMatch = m[0];
  }
  
  if (doiMatch) {
    window.open(`http://localhost:8765/?doi=${encodeURIComponent(doiMatch)}`, "_blank");
  } else {
    // If no direct DOI string in URL, search via prompt or open publisher
    window.open(`http://localhost:8765/?search=${encodeURIComponent(title)}`, "_blank");
  }
}

// ==========================================
// MODO 2: BUSCADOR DE PERFILES (SCHOLAR + ORCID + SCOPUS)
// ==========================================
async function handleProfileSearch(e) {
  e.preventDefault();
  const query = document.getElementById("profileQuery").value.trim();
  if (!query) return;

  const btn = document.getElementById("btnSearchProfiles");
  const grid = document.getElementById("profilesGrid");
  const countLabel = document.getElementById("profilesResultsCount");

  btn.disabled = true;
  btn.innerHTML = `<span class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-1"></span> Consultando bases...`;
  grid.innerHTML = `
    <div class="col-span-full text-center py-16">
      <div class="animate-spin inline-block w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full mb-3"></div>
      <p class="text-xs text-slate-500 font-medium">Buscando perfiles en ORCID, Google Scholar y Scopus para "${escapeHtml(query)}"...</p>
    </div>
  `;

  try {
    const scopusKey = getScopusApiKey();
    const resp = await fetch("/api/profiles/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, scopus_api_key: scopusKey })
    });
    const data = await resp.json();

    if (data.success && data.data) {
      currentProfilesData = data.data;
      renderProfiles();
    } else {
      countLabel.textContent = `0 resultados`;
      grid.innerHTML = `
        <div class="col-span-full text-center py-12 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
          <p class="text-sm text-slate-500">No se encontraron perfiles con el criterio ingresado.</p>
        </div>
      `;
    }
  } catch (err) {
    grid.innerHTML = `
      <div class="col-span-full p-4 bg-rose-500/10 border border-rose-500/20 text-rose-500 rounded-xl text-xs">
        Error al buscar perfiles: ${err.message}
      </div>
    `;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Buscar Perfiles</span>`;
  }
}

function filterProfilesSource(source) {
  activeProfileFilter = source;
  
  // Update tabs styles
  const tabs = ["all", "orcid", "scholar", "scopus"];
  tabs.forEach(t => {
    const el = document.getElementById("tabFilter" + t.charAt(0).toUpperCase() + t.slice(1));
    if (el) {
      if (t === source) {
        el.className = "px-3 py-1 rounded-lg font-semibold bg-white/20 text-white";
      } else {
        el.className = "px-3 py-1 rounded-lg font-semibold text-slate-400 hover:text-white";
      }
    }
  });

  renderProfiles();
}

function renderProfiles() {
  const grid = document.getElementById("profilesGrid");
  const countLabel = document.getElementById("profilesResultsCount");
  grid.innerHTML = "";

  let listToRender = [];
  if (activeProfileFilter === "all") {
    listToRender = currentProfilesData.unified || [];
  } else if (activeProfileFilter === "orcid") {
    listToRender = (currentProfilesData.orcid || []).map(o => ({
      name: o.name,
      affiliation: o.affiliation,
      orcid_id: o.orcid_id,
      orcid_url: o.profile_url,
      sources: ["ORCID"]
    }));
  } else if (activeProfileFilter === "scholar") {
    listToRender = (currentProfilesData.scholar || []).map(s => ({
      name: s.name,
      affiliation: s.affiliation,
      scholar_id: s.scholar_id,
      scholar_url: s.profile_url,
      citations: s.citations,
      photo_url: s.photo_url,
      interests: s.interests,
      sources: ["Google Scholar"]
    }));
  } else if (activeProfileFilter === "scopus") {
    listToRender = (currentProfilesData.scopus || []).map(sc => ({
      name: sc.name,
      affiliation: sc.affiliation,
      scopus_id: sc.scopus_id,
      scopus_url: sc.profile_url,
      interests: sc.subject_areas,
      sources: ["Scopus"]
    }));
  }

  countLabel.textContent = `Se encontraron ${listToRender.length} perfiles (${activeProfileFilter.toUpperCase()})`;

  if (listToRender.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full text-center py-12 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
        <p class="text-sm text-slate-500">No hay perfiles disponibles bajo el filtro '${activeProfileFilter}'.</p>
      </div>
    `;
    return;
  }

  listToRender.forEach((p) => {
    const card = document.createElement("div");
    card.className = "p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between space-y-4";

    // Source badges
    const badges = [];
    if (p.orcid_id) {
      badges.push(`<a href="${p.orcid_url || `https://orcid.org/${p.orcid_id}`}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">🟢 ORCID: ${p.orcid_id}</a>`);
    }
    if (p.scholar_id || (p.sources && p.sources.includes("Google Scholar"))) {
      badges.push(`<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/30">🔵 Scholar</span>`);
    }
    if (p.scopus_id || (p.sources && p.sources.includes("Scopus"))) {
      badges.push(`<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30">🟠 Scopus ID: ${p.scopus_id || "Reportado"}</span>`);
    }

    // Avatar
    const avatarHtml = p.photo_url 
      ? `<img src="${p.photo_url}" class="w-12 h-12 rounded-full object-cover border border-slate-300 dark:border-slate-700 flex-shrink-0" onerror="this.src='/static/favicon.png'">`
      : `<div class="w-12 h-12 rounded-full bg-gradient-to-tr from-indigo-600 to-cyan-500 text-white font-bold text-base flex items-center justify-center flex-shrink-0 shadow">${p.name.charAt(0)}</div>`;

    // Citations count
    const citationsHtml = p.citations !== null && p.citations !== undefined 
      ? `<div class="flex items-center gap-1 text-xs font-bold text-amber-500">⭐ ${p.citations.toLocaleString()} citas</div>`
      : "";

    // Interests tags
    let interestsHtml = "";
    if (p.interests && p.interests.length > 0) {
      interestsHtml = `
        <div class="flex flex-wrap gap-1.5 pt-1">
          ${p.interests.slice(0, 4).map(i => `<span class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-medium">${escapeHtml(i)}</span>`).join("")}
        </div>
      `;
    }

    card.innerHTML = `
      <div class="space-y-3">
        <div class="flex items-start gap-3">
          ${avatarHtml}
          <div class="flex-1 min-w-0">
            <h4 class="text-base font-bold text-slate-900 dark:text-white truncate">${escapeHtml(p.name)}</h4>
            <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">${escapeHtml(p.affiliation || "Investigador independiente")}</p>
            ${citationsHtml}
          </div>
        </div>

        <div class="flex flex-wrap gap-1.5">
          ${badges.join("")}
        </div>

        ${interestsHtml}
      </div>

      <div class="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
        <button onclick="openWorksModal('${escapeAttr(p.name)}', '${p.orcid_id || ''}', '${p.scholar_id || ''}')" class="px-3 py-1.5 text-xs font-bold rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white shadow transition-all flex items-center gap-1.5">
          <span>📚</span>
          <span>Ver Obras y DOIs</span>
        </button>
        <div class="flex items-center gap-2">
          ${p.scholar_url ? `<a href="${p.scholar_url}" target="_blank" title="Ver en Google Scholar" class="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs">🎓</a>` : ""}
          ${p.orcid_id ? `<a href="https://orcid.org/${p.orcid_id}" target="_blank" title="Ver en ORCID" class="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs">🆔</a>` : ""}
          ${p.scopus_url ? `<a href="${p.scopus_url}" target="_blank" title="Ver en Scopus" class="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs">📙</a>` : ""}
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
}

// ==========================================
// MODAL: CATÁLOGO DE OBRAS DEL INVESTIGADOR
// ==========================================
async function openWorksModal(authorName, orcidId, scholarId) {
  const modal = document.getElementById("worksModal");
  const titleEl = document.getElementById("modalAuthorName");
  const affilEl = document.getElementById("modalAuthorAffil");
  const listEl = document.getElementById("modalWorksList");

  titleEl.textContent = `Publicaciones de ${authorName}`;
  affilEl.textContent = orcidId ? `ORCID iD: ${orcidId}` : `Google Scholar: ${scholarId}`;
  listEl.innerHTML = `
    <div class="text-center py-12">
      <div class="animate-spin inline-block w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full mb-3"></div>
      <p class="text-xs text-slate-500">Recuperando catálogo de publicaciones...</p>
    </div>
  `;
  modal.classList.remove("hidden");

  let works = [];

  // Try ORCID first (reliable for verified DOIs)
  if (orcidId) {
    try {
      const resp = await fetch(`/api/orcid/works?id=${encodeURIComponent(orcidId)}&limit=30`);
      const data = await resp.json();
      if (data && data.works) {
        works = data.works;
      }
    } catch (e) {
      console.error("ORCID works error:", e);
    }
  }

  // Fallback to Scholar publications if ORCID was empty
  if (works.length === 0 && scholarId) {
    try {
      const resp = await fetch(`/api/scholar/author_details?id=${encodeURIComponent(scholarId)}`);
      const data = await resp.json();
      if (data && data.publications) {
        works = data.publications.map(p => ({
          title: p.title,
          year: p.year,
          journal: p.venue,
          citations: p.citations,
          url: p.pub_url,
          doi: null
        }));
      }
    } catch (e) {
      console.error("Scholar details error:", e);
    }
  }

  if (works.length === 0) {
    listEl.innerHTML = `
      <div class="text-center py-8 text-slate-500 text-xs">
        No se encontraron publicaciones públicas listadas en el perfil.
      </div>
    `;
    return;
  }

  listEl.innerHTML = "";
  works.forEach(w => {
    const item = document.createElement("div");
    item.className = "p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3";

    const doiBadge = w.doi 
      ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold">${w.doi}</span>`
      : "";

    const dlBtn = w.doi 
      ? `<button onclick="window.open('http://localhost:8765/?doi=${encodeURIComponent(w.doi)}', '_blank')" class="px-2.5 py-1 text-xs font-bold rounded-lg bg-gradient-to-r from-indigo-600 to-cyan-500 text-white shadow-sm hover:opacity-90 flex items-center gap-1 flex-shrink-0">⚡ Descargar con APS</button>`
      : (w.url ? `<a href="${w.url}" target="_blank" class="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 flex-shrink-0">🔗 Abrir</a>` : "");

    item.innerHTML = `
      <div class="space-y-1 min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-xs font-bold text-slate-400 font-mono">${w.year || "S/F"}</span>
          ${doiBadge}
          <span class="text-[11px] text-slate-500 italic truncate max-w-xs">${w.journal || ""}</span>
        </div>
        <h5 class="text-xs font-bold text-slate-800 dark:text-slate-200 leading-snug">${escapeHtml(w.title)}</h5>
      </div>
      <div>
        ${dlBtn}
      </div>
    `;
    listEl.appendChild(item);
  });
}

function closeWorksModal() {
  document.getElementById("worksModal").classList.add("hidden");
}

// Helpers
function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(text) {
  if (!text) return "";
  return String(text).replace(/'/g, "\\'").replace(/"/g, "&quot;");
}
