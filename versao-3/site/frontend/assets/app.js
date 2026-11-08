"use strict";
const previewMode = new URLSearchParams(window.location.search).has("preview");
const state = { user: null, components: [], events: [], dashboard: null, factory: null, serverOnline: false, commandBusy: 0, stopBusy: false, networkError: "", generation: 0 };
let pollTimer = null;
let commandSequence = 0;
const mock = {
  user: { id: 1, username: "admin" },
  dashboard: {
    summary: { active_components: 3, events_today: 18, unknown_today: 2 },
    latest: { id: 127, detected_name: "Capacitor eletrolítico", confidence: 0.964, status: "recognized", image_url: null, device_id: "esp32-cam-01", created_at: new Date().toISOString() }
  },
  factory: {
    motor: { online: false, boot_id: null, telemetry: {} }, camera: { online: false, telemetry: {} },
    ai: { online: false, status: "awaiting", reason: "Prévia com dados demonstrativos." },
    event: null, command: null, can_calibrate: false, can_start: false
  },
  components: [
    { id: 1, name: "Capacitor eletrolítico", category: "Capacitor", code: "100 µF 25 V", active: true, image_url: null, image_count: 6 },
    { id: 2, name: "LED vermelho", category: "LED", code: "5 mm", active: true, image_url: null, image_count: 5 },
    { id: 3, name: "Resistor", category: "Resistor", code: "1 kΩ", active: true, image_url: null, image_count: 8 }
  ],
  events: [
    { id: 127, detected_name: "Capacitor eletrolítico", confidence: 0.964, status: "recognized", device_id: "esp32-cam-01", created_at: new Date().toISOString(), image_url: null },
    { id: 126, detected_name: "Não identificado", confidence: null, status: "unknown", device_id: "esp32-cam-01", created_at: new Date(Date.now() - 61000).toISOString(), image_url: null }
  ]
};
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const escapeHtml = (value = "") => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const formatDate = (value) => {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.valueOf()) ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium", timeZone: "America/Sao_Paulo" }).format(date) : "—";
};
const formatConfidence = (value) => value == null || !Number.isFinite(Number(value)) ? "—" : `${(Number(value) * 100).toFixed(1).replace(".", ",")}%`;
const formatDistance = (value) => value == null || !Number.isFinite(Number(value)) ? "—" : `${Number(value).toFixed(1).replace(".", ",")} mm`;
const safeImage = (url) => typeof url === "string" && /^\/uploads\/[A-Za-z0-9_.-]+$/.test(url) ? url : null;
const statusLabel = FactoryUI.eventLabel;
const stateLabel = (value) => ({ disabled: "Desabilitada", idle: "Parada", ready: "Pronta", moving: "Aguardando peça", detecting: "Peça detectada", awaiting_analysis: "Aguardando análise", waiting_analysis: "Aguardando análise", waiting_result: "Aguardando resultado", waiting_capture: "Aguardando captura", awaiting_capture: "Aguardando captura", waiting_review: "Aguardando conferência", awaiting_review: "Aguardando conferência", exiting: "Saída controlada", releasing: "Saída controlada", calibrating: "Calibrando", fault: "Falha", stopped: "Parada" })[value] || value || "Sem telemetria";

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(path, { credentials: "same-origin", ...options, signal: controller.signal });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = typeof body.detail === "string" ? body.detail : "Não foi possível concluir a operação.";
      const error = new Error(detail);
      error.status = response.status;
      if (response.status === 401 && state.user) showLogin();
      throw error;
    }
    return response.status === 204 ? null : response.json();
  } catch (error) {
    if (error.name === "AbortError") throw new Error("O servidor demorou a responder. A execução do comando não foi confirmada.");
    throw error;
  } finally { clearTimeout(timeout); }
}
function placeholder(label = "Sem imagem") {
  return `<div class="image-placeholder"><span>${escapeHtml(label)}</span></div>`;
}
function setHTML(selector, content) {
  const element = $(selector);
  if (element.innerHTML !== content) element.innerHTML = content;
}
function updateConnection() {
  const label = previewMode ? "Prévia — sem conexão real" : state.serverOnline ? "Servidor atualizado" : state.networkError ? "Sem atualização do servidor" : "Conectando ao servidor";
  $$(".server-connection").forEach((element) => {
    element.dataset.state = previewMode ? "preview" : state.serverOnline ? "online" : "offline";
    element.querySelector(".server-connection-text").textContent = label;
  });
}
function stopPolling() { clearTimeout(pollTimer); pollTimer = null; }
function showLogin() {
  stopPolling();
  state.generation += 1;
  state.user = null;
  state.serverOnline = false;
  state.factory = null;
  $("#app-shell").hidden = true;
  $("#login-screen").hidden = false;
  renderFactory();
}
function showApp(user) {
  stopPolling();
  state.generation += 1;
  state.user = user;
  state.commandBusy = 0;
  state.stopBusy = false;
  state.networkError = "";
  state.serverOnline = false;
  state.factory = null;
  $("#factory-command-message").textContent = "";
  $("#login-screen").hidden = true;
  $("#app-shell").hidden = false;
  $("#user-label").textContent = user.username;
  renderFactory();
  const generation = state.generation;
  loadAll(generation).finally(() => schedulePoll(generation));
}
function reportNetworkError(error, generation) {
  if (!state.user || state.generation !== generation) return;
  state.serverOnline = false;
  state.networkError = error.message || "Não foi possível atualizar o servidor.";
  renderFactory();
}
async function loadAll(generation) {
  if (previewMode) {
    state.dashboard = mock.dashboard; state.factory = mock.factory;
    state.components = mock.components; state.events = mock.events;
    renderFactory(); renderDashboard(); renderComponents(); renderHistory();
    return;
  }
  try {
    const [dashboard, components, events, factory] = await Promise.all([
      api("/api/v1/dashboard"), api("/api/v1/components"), api("/api/v1/events"), api("/api/v1/factory/status")
    ]);
    if (!state.user || state.generation !== generation) return;
    Object.assign(state, { dashboard, components, events, factory, serverOnline: true, networkError: "" });
    renderFactory(); renderDashboard(); renderComponents(); renderHistory();
  } catch (error) { reportNetworkError(error, generation); }
}
function schedulePoll(generation) {
  stopPolling();
  if (!state.user || previewMode || generation !== state.generation) return;
  pollTimer = setTimeout(async () => {
    await refreshOperational(generation);
    schedulePoll(generation);
  }, 2000);
}
async function refreshOperational(generation = state.generation) {
  if (!state.user || previewMode) return;
  try {
    const [dashboard, events, factory] = await Promise.all([
      api("/api/v1/dashboard"), api("/api/v1/events"), api("/api/v1/factory/status")
    ]);
    if (!state.user || generation !== state.generation) return;
    Object.assign(state, { dashboard, events, factory, serverOnline: true, networkError: "" });
    renderFactory(); renderDashboard(); renderHistory();
  } catch (error) { reportNetworkError(error, generation); }
}
function renderFactory() {
  updateConnection();
  const f = state.factory;
  const motor = f?.motor || {}, camera = f?.camera || {}, ai = f?.ai || {};
  const telemetry = motor.telemetry || {}, command = f?.command, event = f?.event;
  const enabled = FactoryUI.controls(f, { authenticated: !!state.user, preview: previewMode, serverOnline: state.serverOnline, commandBusy: state.commandBusy > 0, stopBusy: state.stopBusy });
  $("#factory-calibrate").disabled = !enabled.calibrate;
  $("#factory-start").disabled = !enabled.start;
  $("#factory-stop").disabled = !enabled.stop;
  $("#factory-mode").textContent = previewMode ? "Demonstração — comandos desativados" : motor.authorized ? "Ciclo autorizado nesta inicialização" : "Aguardando autorização";
  $("#factory-network-error").hidden = !state.networkError;
  $("#factory-network-error").textContent = state.networkError ? `${state.networkError} Os dados abaixo podem estar desatualizados.` : "";
  const onlineBadge = (device) => `<span class="badge ${device.online === true ? "badge-success" : "badge-muted"}">${device.online === true ? "Online" : "Sem comunicação recente"}</span>`;
  const commandHTML = command
    ? `<strong>${escapeHtml(FactoryUI.actionLabel(command.action))}</strong><span class="badge ${command.status === "applied" ? "badge-success" : ""}">${escapeHtml(FactoryUI.commandLabel(command.status))}</span><p>Comando ${escapeHtml(command.id)} · solicitado ${formatDate(command.created_at)}</p>${command.ack_reason ? `<p>${escapeHtml(command.ack_reason)}</p>` : ""}`
    : `<strong>Nenhum comando registrado</strong><p>Um pedido só aparece como confirmado depois da resposta da placa.</p>`;
  const eventImage = safeImage(event?.image_url);
  const eventHTML = event
    ? `${eventImage ? `<img class="factory-event-image" src="${eventImage}" alt="Fotografia da peça deste evento">` : ""}<div><strong>${escapeHtml(event.component_name || statusLabel(event.status))}</strong><span class="badge ${event.status === "recognized" ? "badge-success" : ""}">${escapeHtml(statusLabel(event.status))}</span><p>Evento ${escapeHtml(event.id)}</p>${event.confidence != null ? `<p>Pontuação YOLO: ${formatConfidence(event.confidence)}</p>` : ""}${event.reason ? `<p class="event-reason">${escapeHtml(event.reason)}</p>` : ""}<p>${event.approved === true ? "Resultado aprovado para este evento. A saída ainda depende da confirmação da esteira." : "A esteira aguarda um resultado aprovado para esta peça."}</p></div>`
    : `<div><strong>Aguardando peça</strong><p>A captura e o resultado ficarão vinculados ao evento criado pela esteira.</p></div>`;
  setHTML("#factory-status", `
    <div class="factory-device-grid">
      <section class="factory-device"><div class="device-title"><h3>ESP32 da esteira</h3>${onlineBadge(motor)}</div>
        <dl><div><dt>Estado reportado</dt><dd>${escapeHtml(stateLabel(telemetry.state))}</dd></div><div><dt>Saída do motor reportada</dt><dd>${telemetry.motor_on === true ? "Ligada" : telemetry.motor_on === false ? "Desligada" : "Sem informação"}</dd></div><div><dt>Calibração</dt><dd>${telemetry.calibrated === true ? "Concluída" : "Pendente"}</dd></div><div><dt>Distância</dt><dd>${formatDistance(telemetry.distance_mm)}</dd></div><div><dt>Última telemetria</dt><dd>${formatDate(motor.last_seen)}</dd></div></dl>
      </section>
      <section class="factory-device"><div class="device-title"><h3>ESP32-CAM</h3>${onlineBadge(camera)}</div>
        <p>${camera.telemetry?.ready === true ? "Pronta para capturar" : "Aguardando câmera pronta"}</p><p>Última telemetria: ${formatDate(camera.last_seen)}</p>
        <div class="device-title ai-title"><h3>YOLOv8 no servidor</h3><span class="badge ${ai.online && ai.status === "ready" ? "badge-success" : "badge-muted"}">${ai.online && ai.status === "ready" ? "Pronto" : ai.status === "error" ? "Indisponível" : "Aguardando serviço"}</span></div>
        ${ai.reason ? `<p class="event-reason">${escapeHtml(ai.reason)}</p>` : ""}
      </section>
    </div>
    <div class="factory-details-grid"><section class="factory-command"><h3>Último comando</h3>${commandHTML}</section><section class="factory-event"><h3>Peça em análise / último ciclo</h3><div class="factory-event-content">${eventHTML}</div></section></div>
    <p class="factory-footnote">A saída do motor é informada pela placa; este equipamento ainda não mede a rotação do eixo. Pontuação YOLO não é uma probabilidade garantida de acerto.</p>`);
}
function renderDashboard() {
  const data = state.dashboard, latest = data?.latest, summary = data?.summary || {};
  const image = latest && safeImage(latest.image_url) ? `<img class="capture-image" src="${latest.image_url}" alt="Fotografia do último componente analisado">` : placeholder(latest ? "Imagem capturada" : "Aguardando a primeira captura");
  setHTML("#dashboard-content", `<div class="stats-grid">
    <article class="stat-card"><span>Componentes ativos</span><strong>${summary.active_components || 0}</strong></article>
    <article class="stat-card"><span>Peças analisadas hoje</span><strong>${summary.events_today || 0}</strong></article>
    <article class="stat-card"><span>Não identificadas hoje</span><strong>${summary.unknown_today || 0}</strong></article>
    </div><article class="panel latest-panel"><div class="panel-title"><h2>Último resultado</h2><span class="badge">${latest ? escapeHtml(statusLabel(latest.status)) : "Aguardando"}</span></div>
    ${latest ? `<div class="latest-grid">${image}<div><h3 class="recognition-name">${escapeHtml(latest.detected_name || "Componente desconhecido")}</h3><p class="recognition-meta">Evento #${escapeHtml(latest.id)}</p><p class="recognition-meta">${formatDate(latest.created_at)}</p><p class="recognition-meta">Câmera: ${escapeHtml(latest.device_id || "não informada")}</p>${latest.confidence != null ? `<span class="confidence">Pontuação YOLO: ${formatConfidence(latest.confidence)}</span>` : ""}${latest.reason ? `<p class="event-reason">${escapeHtml(latest.reason)}</p>` : ""}</div></div>` : image}</article>`);
}
function renderComponents() {
  if (!state.components.length) {
    setHTML("#components-content", `<div class="empty-state"><strong>Nenhum componente cadastrado</strong>Use a aba Cadastro para adicionar a primeira referência.</div>`);
    return;
  }
  setHTML("#components-content", state.components.map((item) => {
    const image = safeImage(item.image_url) ? `<img src="${item.image_url}" alt="${escapeHtml(item.name)}">` : placeholder("Referência visual");
    return `<article class="component-card ${item.active ? "" : "inactive"}">${image}<div class="component-info"><h2>${escapeHtml(item.name)}</h2><p>ID interno: ${escapeHtml(item.id)} · ${escapeHtml(item.category || "Sem categoria")}</p><p>${escapeHtml(item.code || "Sem código")} · ${item.image_count} imagem(ns)</p><div class="component-actions"><span class="badge">${item.active ? "Ativo" : "Inativo"}</span><button class="secondary-button" data-component-status="${item.id}" data-active="${!item.active}">${item.active ? "Desativar" : "Ativar"}</button></div></div></article>`;
  }).join(""));
}
function renderHistory() {
  if (!state.events.length) {
    setHTML("#history-content", `<div class="empty-state"><strong>Nenhum reconhecimento registrado</strong>As capturas da ESP32-CAM aparecerão aqui.</div>`);
    return;
  }
  setHTML("#history-content", `<div class="table-panel"><div class="responsive-table"><table><thead><tr><th>Imagem</th><th>Componente</th><th>Pontuação YOLO</th><th>Status / motivo</th><th>Data e hora</th></tr></thead><tbody>${state.events.map((event) => `<tr><td>${safeImage(event.image_url) ? `<img class="table-thumb" src="${event.image_url}" alt="">` : `<div class="table-thumb"></div>`}</td><td>${escapeHtml(event.detected_name || "Desconhecido")}</td><td>${formatConfidence(event.confidence)}</td><td><span class="badge">${escapeHtml(statusLabel(event.status))}</span>${event.reason ? `<p class="history-reason">${escapeHtml(event.reason)}</p>` : ""}</td><td>${formatDate(event.created_at)}</td></tr>`).join("")}</tbody></table></div></div>`);
}
function selectView(name) {
  $$(".view").forEach((view) => view.classList.toggle("active-view", view.id === `view-${name}`));
  $$(".nav-button").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
}

$$("[data-factory-command]").forEach((button) => button.addEventListener("click", async () => {
  const action = button.dataset.factoryCommand;
  if (previewMode || !state.user || button.disabled) return;
  const generation = state.generation, sequence = ++commandSequence;
  const message = $("#factory-command-message");
  state.commandBusy += 1;
  if (action === "stop") state.stopBusy = true;
  message.textContent = `Enviando pedido de ${FactoryUI.actionLabel(action).toLowerCase()}…`;
  renderFactory();
  try {
    const result = await api("/api/v1/factory/commands", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
    if (!state.user || generation !== state.generation || sequence !== commandSequence) return;
    if (result.command && state.factory) state.factory.command = result.command;
    message.textContent = `${FactoryUI.actionLabel(action)} solicitado ao servidor. Aguarde a confirmação da placa no estado abaixo.`;
    if (action === "stop") message.textContent = "Parada solicitada ao servidor. Confira a confirmação da placa; sem conexão, o pedido ficará registrado.";
    await refreshOperational(generation);
  } catch (error) {
    if (!state.user || generation !== state.generation || sequence !== commandSequence) return;
    message.textContent = `${FactoryUI.actionLabel(action)}: ${error.message} A execução não foi confirmada.`;
    if (!error.status || error.status >= 500) reportNetworkError(error, generation);
  } finally {
    if (generation === state.generation) {
      state.commandBusy = Math.max(0, state.commandBusy - 1);
      if (action === "stop") state.stopBusy = false;
      renderFactory();
    }
  }
}));
$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#login-error").textContent = "";
  if (previewMode) return showApp(mock.user);
  try {
    const user = await api("/api/v1/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: $("#login-username").value, password: $("#login-password").value }) });
    showApp(user);
  } catch (error) { $("#login-error").textContent = error.message; }
});
$("#logout-button").addEventListener("click", async () => {
  stopPolling();
  try {
    if (!previewMode) await api("/api/v1/auth/logout", { method: "POST" });
    showLogin();
  } catch (error) {
    reportNetworkError(error, state.generation);
    $("#factory-command-message").textContent = "Não foi possível encerrar a sessão no servidor. Tente sair novamente.";
    schedulePoll(state.generation);
  }
});
$$(".nav-button").forEach((button) => button.addEventListener("click", () => selectView(button.dataset.view)));
$("#component-images").addEventListener("change", (event) => {
  const root = $("#image-preview"); root.innerHTML = "";
  [...event.target.files].slice(0, 10).forEach((file) => {
    const image = document.createElement("img"); image.src = URL.createObjectURL(file); image.alt = `Prévia de ${file.name}`;
    image.onload = () => URL.revokeObjectURL(image.src); root.appendChild(image);
  });
});
$("#component-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget, button = form.querySelector("button[type=submit]"), message = $("#component-form-message");
  button.disabled = true; message.textContent = "Salvando...";
  try {
    if (previewMode) throw new Error("O modo de prévia não grava dados.");
    await api("/api/v1/components", { method: "POST", body: new FormData(form) });
    form.reset(); $("#image-preview").innerHTML = ""; message.textContent = "Componente cadastrado com sucesso.";
    state.components = await api("/api/v1/components"); renderComponents();
  } catch (error) { message.textContent = error.message; }
  finally { button.disabled = false; }
});
$("#components-content").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-component-status]");
  if (!button || previewMode) return;
  button.disabled = true;
  try {
    await api(`/api/v1/components/${button.dataset.componentStatus}/status?active=${button.dataset.active}`, { method: "PATCH" });
    state.components = await api("/api/v1/components"); renderComponents();
  } catch (error) {
    $("#factory-command-message").textContent = `Não foi possível alterar o componente: ${error.message}`;
    button.disabled = false;
  }
});
async function boot() {
  if (previewMode) return showApp(mock.user);
  try { showApp(await api("/api/v1/auth/me")); }
  catch { showLogin(); }
}
boot();
