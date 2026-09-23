// Bateria de casos_busca.json no NODE. Uso: TJSE_DIR_DADOS=<cópia> node busca_node.mjs > busca_node.json
import fs from "node:fs";
import { buscar, mapaCitacoes } from "../../server/busca.js";
const casos = JSON.parse(fs.readFileSync(new URL("./casos_busca.json", import.meta.url), "utf8"));
const out = {};
for (const c of casos) out[c.nome] = c.mapa ? mapaCitacoes(c.p.referencia ?? null, c.p.limite ?? 15) : buscar(c.p);
process.stdout.write(JSON.stringify(out));
