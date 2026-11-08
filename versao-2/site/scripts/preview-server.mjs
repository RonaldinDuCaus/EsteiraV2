import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";

const root = new URL("../frontend/", import.meta.url).pathname;
const port = Number(process.env.PORT || 4173);
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml"
};

createServer((request, response) => {
  const url = new URL(request.url || "/", `http://${request.headers.host}`);
  if (url.pathname === "/" && !url.searchParams.has("preview")) {
    response.writeHead(302, { Location: "/?preview=1" });
    return response.end();
  }

  const relative = url.pathname === "/"
    ? "index.html"
    : url.pathname === "/favicon.svg"
      ? "assets/favicon.svg"
      : url.pathname.replace(/^\/(assets\/)?/, (_, assets = "") => assets);
  const target = normalize(join(root, relative));
  if (!target.startsWith(normalize(root)) || !existsSync(target) || !statSync(target).isFile()) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    return response.end("Não encontrado");
  }

  response.writeHead(200, { "Content-Type": types[extname(target)] || "application/octet-stream" });
  createReadStream(target).pipe(response);
}).listen(port, "0.0.0.0", () => {
  process.stdout.write(`Prévia disponível na porta ${port}\n`);
});
