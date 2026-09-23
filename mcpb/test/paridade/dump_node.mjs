// Igual a dump_py.py, do lado Node. Uso: TJSE_DIR_DADOS=<pasta> node dump_node.mjs > node.jsonl
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { parseSecao, camposDaEmenta, citacoesDaEmenta, ancoras, resultadoDeclarado, proximaPosicao } from "../../server/parse.js";
import { norm } from "../../server/texto.js";

// json.dumps(ensure_ascii=False, sort_keys=True) do Python: separadores ", " e ": ", chaves ordenadas
function pyJson(v) {
  if (v === null || v === undefined) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") return String(v);
  if (typeof v === "string") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(pyJson).join(", ") + "]";
  return "{" + Object.keys(v).sort().map((k) => JSON.stringify(k) + ": " + pyJson(v[k])).join(", ") + "}";
}
const h = (x) => crypto.createHash("sha1").update(pyJson(x), "utf8").digest("hex").slice(0, 16);
const dir = path.join(process.env.TJSE_DIR_DADOS, "base", "secoes");
const lerPag = (ed, cod, p) => {
  try { return zlib.gunzipSync(fs.readFileSync(path.join(dir, `${ed}-${cod}${p === 1 ? "" : ".p" + p}.html.gz`))).toString("utf8"); } catch { return null; }
};
const pares = [...new Set(fs.readdirSync(dir).filter((n) => n.endsWith(".html.gz"))
  .map((n) => n.split("-")[0] + "|" + n.split("-")[1].split(".")[0]))].map((x) => x.split("|").map(Number))
  .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
const out = [];
for (const [ed, cod] of pares) {
  const pags = [];
  for (let p = 1; ; p++) { const pg = lerPag(ed, cod, p); if (pg === null) break; pags.push(pg); if (proximaPosicao(pg) === null) break; }
  for (const it of parseSecao(pags.join("\n"))) {
    const cps = camposDaEmenta(it.ementa);
    const rec = { id: it.acordao, ed, cod };
    for (const [k, v] of Object.entries(it)) rec["f_" + k] = h(v);
    for (const [k, v] of Object.entries(cps)) rec["c_" + k] = h(v);
    rec.cit = h(citacoesDaEmenta(cps, it.ementa));
    rec.anc = h(ancoras(it.ementa, 12));
    rec.res = h(resultadoDeclarado(it.ementa));
    rec.norm = h(norm(it.ementa));
    out.push(JSON.stringify(rec));
  }
}
process.stdout.write(out.join("\n") + "\n");
