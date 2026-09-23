// Confere, no NODE, exatamente os casos que o Python gerou. Uso: node confere_node.mjs <dir recibos> <confere_py.json>
import fs from "node:fs";
import path from "node:path";
import { parseTeor } from "../../server/parse.js";
import { conferir } from "../../server/confere.js";
const [, , dir, casosPath] = process.argv;
const casos = JSON.parse(fs.readFileSync(casosPath, "utf8"));
const cache = {};
const out = {};
for (const [k, c] of Object.entries(casos)) {
  const d = cache[c.f] ??= parseTeor(JSON.parse(fs.readFileSync(path.join(dir, c.f), "utf8")).html);
  out[k] = { f: c.f, t: c.t, r: conferir(d.texto.slice(d.inicio_conteudo), c.t) };
}
process.stdout.write(JSON.stringify(out));
