const previewMode = new URLSearchParams(window.location.search).has("preview");
const state = { user: null, components: [], events: [], dashboard: null };

const mock = {
  user: { id: 1, username: "admin" },
  dashboard: {
    summary: { active_components: 3, events_today: 18, unknown_today: 2 },
    latest: { id: 127, detected_name: "Capacitor eletrolítico", confidence: 0.964, status: "recognized", image_url: null, device_id: "esp32-cam-01", created_at: new Date().toISOString() },
    devices: { esp32: "awaiting", camera: "awaiting" }
  },
  components: [
    { id: 1, name: "Capacitor eletrolítico", category: "Capacitor", code: "100 µF 25 V", active: true, image_url: null, image_count: 6 },
    { id: 2, name: "LED vermelho", category: "LED", code: "5 mm", active: true, image_url: null, image_count: 5 },
    { id: 3, name: "Resistor", category: "Resistor", code: "1 kΩ", active: true, image_url: null, image_count: 8 }
  ],
  events: [
    { id: 127, detected_name: "Capacitor eletrolítico", confidence: 0.964, status: "recognized", device_id: "esp32-cam-01", created_at: new Date().toISOString(), image_url: null },
    { id: 126, detected_name: "LED vermelho", confidence: 0.941, status: "recognized", device_id: "esp32-cam-01", created_at: new Date(Date.now() - 61000).toISOString(), image_url: null }
  ]
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const formatDate = (value) => value ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium" }).format(new Date(value)) : "—";
const formatConfidence = (value) => value == null ? "—" : `${(Number(value) * 100).toFixed(1).replace(".", ",")}%`;
const safeImage = (url) => typeof url === "string" && url.startsWith("/uploads/") ? url : null;
const statusLabel = (status) => ({ recognized: "Reconhecido", unknown: "Desconhecido", pending: "Processando", error: "Erro" })[status] || status || "Aguardando";

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.detail || "Não foi possível concluir a operação.");
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

function placeholder(label = "Sem imagem") {
  return `<div class="image-placeholder"><span>${escapeHtml(label)}</span></div>`;
}

function showApp(user) {
  state.user = user;
  $("#login-screen").hidden = true;
  $("#app-shell").hidden = false;
  $("#user-label").textContent = user.username;
  loadAll();
}

function showLogin() {
  $("#app-shell").hidden = true;
  $("#login-screen").hidden = false;
}

async function loadAll() {
  if (previewMode) {
    state.dashboard = mock.dashboard;
    state.components = mock.components;
    state.events = mock.events;
  } else {
    [state.dashboard, state.components, state.events] = await Promise.all([
      api("/api/v1/dashboard"), api("/api/v1/components"), api("/api/v1/events")
    ]);
  }
  renderDashboard();
  renderComponents();
  renderHistory();
}

function renderDashboard() {
  const data = state.dashboard;
  const latest = data?.latest;
  const summary = data?.summary || {};
  const image = latest && safeImage(latest.image_url)
    ? `<img class="capture-image" src="${latest.image_url}" alt="Fotografia do último componente reconhecido">`
    : placeholder(latest ? "Imagem capturada" : "Aguardando a primeira captura");
  $("#dashboard-content").innerHTML = `
    <div class="stats-grid">
      <article class="stat-card"><span>Componentes ativos</span><strong>${summary.active_components || 0}</strong></article>
      <article class="stat-card"><span>Reconhecimentos hoje</span><strong>${summary.events_today || 0}</strong></article>
      <article class="stat-card"><span>Não identificados</span><strong>${summary.unknown_today || 0}</strong></article>
    </div>
    <div class="dashboard-grid">
      <article class="panel">
        <div class="panel-title"><h2>Último item</h2><span class="badge">${latest ? escapeHtml(statusLabel(latest.status)) : "Aguardando"}</span></div>
        ${latest ? `<div class="latest-grid">${image}<div><h3 class="recognition-name">${escapeHtml(latest.detected_name || "Componente desconhecido")}</h3><p class="recognition-meta">Evento #${latest.id}</p><p class="recognition-meta">${formatDate(latest.created_at)}</p><p class="recognition-meta">Câmera: ${escapeHtml(latest.device_id || "não informada")}</p><span class="confidence">${formatConfidence(latest.confidence)} de confiança</span></div></div>` : image}
      </article>
      <article class="panel">
        <div class="panel-title"><h2>Dispositivos</h2></div>
        <div class="device-list">
          <div class="device-row"><span>ESP32 da esteira</span><span class="badge">Aguardando integração</span></div>
          <div class="device-row"><span>ESP32-CAM</span><span class="badge">Aguardando integração</span></div>
        </div>
      </article>
    </div>`;
}

function renderComponents() {
  const root = $("#components-content");
  if (!state.components.length) {
    root.innerHTML = `<div class="empty-state"><strong>Nenhum componente cadastrado</strong>Use a aba Cadastro para adicionar a primeira referência.</div>`;
    return;
  }
  root.innerHTML = state.components.map((item) => {
    const image = safeImage(item.image_url) ? `<img src="${item.image_url}" alt="${escapeHtml(item.name)}">` : placeholder("Referência visual");
    return `<article class="component-card ${item.active ? "" : "inactive"}">${image}<div class="component-info"><h2>${escapeHtml(item.name)}</h2><p>${escapeHtml(item.category || "Sem categoria")}</p><p>${escapeHtml(item.code || "Sem código")} · ${item.image_count} imagem(ns)</p><div class="component-actions"><span class="badge">${item.active ? "Ativo" : "Inativo"}</span><button class="secondary-button" data-component-status="${item.id}" data-active="${!item.active}">${item.active ? "Desativar" : "Ativar"}</button></div></div></article>`;
  }).join("");
}

function renderHistory() {
  const root = $("#history-content");
  if (!state.events.length) {
    root.innerHTML = `<div class="empty-state"><strong>Nenhum reconhecimento registrado</strong>As capturas da ESP32-CAM aparecerão aqui.</div>`;
    return;
  }
  root.innerHTML = `<div class="table-panel"><div class="responsive-table"><table><thead><tr><th>Imagem</th><th>Componente</th><th>Confiança</th><th>Status</th><th>Data e hora</th></tr></thead><tbody>${state.events.map((event) => `<tr><td>${safeImage(event.image_url) ? `<img class="table-thumb" src="${event.image_url}" alt="">` : `<div class="table-thumb"></div>`}</td><td>${escapeHtml(event.detected_name || "Desconhecido")}</td><td>${formatConfidence(event.confidence)}</td><td><span class="badge">${escapeHtml(statusLabel(event.status))}</span></td><td>${formatDate(event.created_at)}</td></tr>`).join("")}</tbody></table></div></div>`;
}

function selectView(name) {
  $$(".view").forEach((view) => view.classList.toggle("active-view", view.id === `view-${name}`));
  $$(".nav-button").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
}

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#login-error").textContent = "";
  if (previewMode) return showApp(mock.user);
  try {
    const user = await api("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: $("#login-username").value, password: $("#login-password").value })
    });
    showApp(user);
  } catch (error) {
    $("#login-error").textContent = error.message;
  }
});

$("#logout-button").addEventListener("click", async () => {
  if (!previewMode) await api("/api/v1/auth/logout", { method: "POST" });
  showLogin();
});

$$('.nav-button').forEach((button) => button.addEventListener("click", () => selectView(button.dataset.view)));

$("#component-images").addEventListener("change", (event) => {
  const root = $("#image-preview");
  root.innerHTML = "";
  [...event.target.files].slice(0, 10).forEach((file) => {
    const image = document.createElement("img");
    image.src = URL.createObjectURL(file);
    image.alt = `Prévia de ${file.name}`;
    image.onload = () => URL.revokeObjectURL(image.src);
    root.appendChild(image);
  });
});

$("#component-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type=submit]");
  const message = $("#component-form-message");
  button.disabled = true;
  message.textContent = "Salvando...";
  try {
    if (previewMode) throw new Error("O modo de prévia não grava dados.");
    await api("/api/v1/components", { method: "POST", body: new FormData(event.currentTarget) });
    event.currentTarget.reset();
    $("#image-preview").innerHTML = "";
    message.textContent = "Componente cadastrado com sucesso.";
    state.components = await api("/api/v1/components");
    renderComponents();
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

$("#components-content").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-component-status]");
  if (!button || previewMode) return;
  await api(`/api/v1/components/${button.dataset.componentStatus}/status?active=${button.dataset.active}`, { method: "PATCH" });
  state.components = await api("/api/v1/components");
  renderComponents();
});

async function boot() {
  if (previewMode) return showApp(mock.user);
  try {
    showApp(await api("/api/v1/auth/me"));
  } catch {
    showLogin();
  }
}

boot();
