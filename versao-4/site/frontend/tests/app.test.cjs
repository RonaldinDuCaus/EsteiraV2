const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const FactoryUI = require("../assets/factory-ui.js");
const source = fs.readFileSync(path.join(__dirname, "../assets/app.js"), "utf8");

class Element {
  constructor() { this.dataset = {}; this.disabled = false; this.hidden = false; this.innerHTML = ""; this.textContent = ""; this.handlers = {}; this.value = ""; }
  addEventListener(name, callback) { this.handlers[name] = callback; }
  querySelector() { return this.child || (this.child = new Element()); }
}
function environment(preview = false) {
  const elements = new Map(), requests = [], timers = new Map();
  let nextTimer = 0;
  const get = (selector) => {
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  };
  const buttons = ["calibrate", "start", "stop"].map((action) => {
    const button = get(`#factory-${action}`); button.dataset.factoryCommand = action; return button;
  });
  const connection = new Element();
  const factory = {
    motor: { online: true, authorized: false, boot_id: "boot", last_seen: new Date().toISOString(), telemetry: { state: "idle", motor_on: false, sensor_valid: true, calibrated: true, area_clear: true, distance_mm: 96.2 } },
    camera: { online: true, telemetry: { ready: true } }, ai: { online: true, status: "ready" },
    command: null, event: null, can_calibrate: true, can_start: true
  };
  const context = vm.createContext({
    console, URLSearchParams, AbortController, Intl, Date, FactoryUI,
    window: { location: { search: preview ? "?preview=1" : "" } },
    document: {
      querySelector: get,
      querySelectorAll: (selector) => selector === "[data-factory-command]" ? buttons : selector === ".server-connection" ? [connection] : []
    },
    setTimeout: (callback, ms) => { const id = ++nextTimer; timers.set(id, { callback, ms }); return id; },
    clearTimeout: (id) => timers.delete(id),
    fetch: async (url, options = {}) => {
      requests.push({ url, options });
      let data;
      if (url === "/api/v1/auth/me") data = { id: 1, username: "operador" };
      else if (url === "/api/v1/factory/status") data = factory;
      else if (url === "/api/v1/factory/commands") {
        const action = JSON.parse(options.body).action;
        factory.command = { id: "command-1", action, status: "pending", created_at: new Date().toISOString() };
        data = { command: factory.command, requested: true };
      } else if (url === "/api/v1/components" || url === "/api/v1/events") data = [];
      else if (url === "/api/v1/dashboard") data = { summary: {}, latest: null };
      else if (url === "/api/v1/auth/logout") data = { ok: true };
      else throw new Error(`Chamada inesperada: ${url}`);
      return { ok: true, status: 200, json: async () => data };
    }
  });
  vm.runInContext(source, context);
  return { context, get, requests, timers, factory };
}
const settle = async () => { for (let i = 0; i < 6; i++) await new Promise(setImmediate); };

(async () => {
  const app = environment();
  await settle();
  assert.equal(app.get("#factory-start").disabled, false);
  assert.equal([...app.timers.values()].filter((timer) => timer.ms === 2000).length, 1, "Um único ciclo de atualização deve estar agendado");
  await app.get("#factory-start").handlers.click();
  assert.equal(JSON.parse(app.requests.find((request) => request.url === "/api/v1/factory/commands").options.body).action, "start");
  assert.match(app.get("#factory-status").innerHTML, /Solicitado — aguardando confirmação/);
  assert.doesNotMatch(app.get("#factory-status").innerHTML, /Confirmado pela placa/);
  assert.equal(app.factory.motor.telemetry.motor_on, false, "Enviar comando não pode alterar telemetria de execução");
  assert.match(app.get("#factory-command-message").textContent, /solicitado ao servidor/);
  await app.get("#logout-button").handlers.click();
  assert.equal(app.timers.size, 0, "Logout deve cancelar as atualizações periódicas");
  assert.equal(app.get("#factory-start").disabled, true);
  assert.equal(app.get("#factory-stop").disabled, true);
  const preview = environment(true);
  await settle();
  assert.equal(preview.requests.length, 0, "Prévia não deve consultar nem comandar equipamento real");
  assert.equal(preview.get("#factory-calibrate").disabled, true);
  assert.equal(preview.get("#factory-start").disabled, true);
  assert.equal(preview.get("#factory-stop").disabled, true);
  await preview.get("#factory-start").handlers.click();
  assert.equal(preview.requests.length, 0);
  console.log("app: pedido sem confirmação falsa, polling único, logout e prévia verificados.");
})().catch((error) => { console.error(error); process.exitCode = 1; });
