const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.join(__dirname, "..");
const home = fs.readFileSync(path.join(root, "index.html"), "utf8");
const panel = fs.readFileSync(path.join(root, "painel.html"), "utf8");
const app = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
const ids = (html) => [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
for (const [name, html] of [["home", home], ["painel", panel]]) {
  const identifiers = ids(html);
  assert.equal(new Set(identifiers).size, identifiers.length, `${name}: IDs duplicados`);
  for (const match of html.matchAll(/\b(?:src|href)="(\/assets\/[^"?#]+)"/g)) {
    assert.ok(fs.existsSync(path.join(root, match[1].slice(1))), `${name}: ativo ausente ${match[1]}`);
  }
  for (const match of html.matchAll(/\bhref="#([^"]+)"/g)) {
    assert.ok(identifiers.includes(match[1]), `${name}: âncora ausente ${match[1]}`);
  }
}
assert.match(home, /href="https:\/\/minifabrica\.kronux\.com\.br\/"/);
assert.match(home, /href="\/painel"/);
assert.doesNotMatch(home, /<script\b/i, "A home pública não precisa carregar JavaScript ou ferramentas da operação");
assert.doesNotMatch(home, /data-factory-command|DEVICE_API_TOKEN|MOTOR_API_TOKEN|CAMERA_API_TOKEN|\/api\//);
assert.match(home, /<svg\b[^>]*role="img"/);
assert.match(home, /Ilustração da arquitetura/);
assert.match(panel, /name="robots" content="noindex, nofollow"/);
assert.match(panel, /id="app-shell"[^>]*hidden/);
assert.match(panel, /src="\/assets\/factory-ui\.js"/);
assert.match(panel, /src="\/assets\/app\.js"/);
for (const action of ["calibrate", "start", "stop"]) {
  assert.match(panel, new RegExp(`<button[^>]*data-factory-command="${action}"[^>]*disabled`));
}
const panelIDs = new Set(ids(panel));
for (const match of app.matchAll(/\$\("#([a-zA-Z0-9_-]+)"\)/g)) {
  assert.ok(panelIDs.has(match[1]), `Elemento necessário ao app ausente do painel: ${match[1]}`);
}
assert.doesNotMatch(home + panel, /VPS conectada/);
console.log("pages: home pública, links, ativos, IDs do painel e controles iniciais verificados.");
