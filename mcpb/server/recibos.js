// Recibos de inteiro teor (sha256, campos de custódia) — porte de `servidor_tjse.py` (seção "Recibos e conferência").
// O formato é o mesmo do Python (e dos MCPs do TJRO e do STJ): um lint de citações confere a peça contra o recibo.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { dirRecibos, URL_TEOR } from "./config.js";
import { pausar } from "./disjuntor.js";
import { agoraIso, br, norm } from "./texto.js";
import { parseTeor } from "./parse.js";
import { bruto, faixaDivergente, faixasTranscritas } from "./confere.js";

export const arqRecibo = (acordao) => path.join(dirRecibos(), `${acordao}.json`);
const sha256 = (s) => crypto.createHash("sha256").update(s, "utf8").digest("hex");

/** Campos no formato dos recibos dos MCPs do TJRO e do STJ — `id_documento`, `nr_processo`, `texto` — para que um
 * verificador de fichas (lint de citações de peça) confira o que foi citado contra o que o portal entregou. */
export function camposDeCustodia(rec) {
  const d = parseTeor(rec.html);
  const corpo = d.texto.slice(d.inicio_conteudo);
  // O voto transcreve ementas inteiras de outros tribunais: o recibo leva também O QUE NÃO É palavra do tribunal,
  // para que a conferência avise em vez de aprovar.
  const tn = norm(corpo);
  let ini = 0;
  for (const m of tn.matchAll(/(?<![\p{L}\p{N}_])acordam(?![\p{L}\p{N}_])/gu))
    if (tn.slice(m.index, m.index + 450).includes("estado de sergipe")) { ini = m.index; break; }
  const div = faixaDivergente(tn, ini);
  return {
    id_documento: rec.acordao, nr_processo: rec.processo, tribunal: "TJSE", tipo: "ACÓRDÃO",
    data_julgamento: br(d.data_julgamento), orgao: d.orgao_fecho || "", relator: d.relator || "",
    texto: corpo,
    // EM BRUTO, recortado do próprio `texto`: quem lê o recibo aplica a SUA normalização (duas normalizações quase
    // iguais deixam passar exatamente o que o alerta existe para pegar).
    trechos_transcritos: faixasTranscritas(tn, ini).map(([a, b]) => corpo.slice(bruto(corpo, tn, a), bruto(corpo, tn, b))),
    trecho_divergente: div ? corpo.slice(bruto(corpo, tn, div[0])) : "",
    normalizacao: "trechos em bruto, recortados de `texto` — normalize com a sua própria função",
  };
}

export function gravarRecibo(acordao, processo, htmlBruto) {
  fs.mkdirSync(dirRecibos(), { recursive: true, mode: 0o700 });
  try { fs.chmodSync(dirRecibos(), 0o700); } catch { /* makedirs não corrige pasta que já existia com 0755 */ }
  const rec = {
    acordao, processo, obtido_em: agoraIso(),
    url: `${URL_TEOR}?tmp.numprocesso=${processo}&tmp.numacordao=${acordao}`,
    sha256: sha256(htmlBruto), html: htmlBruto,
  };
  Object.assign(rec, camposDeCustodia(rec));
  fs.writeFileSync(arqRecibo(acordao), JSON.stringify(rec), { mode: 0o600 });
  return rec;
}

const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/** sha256 divergente = corrupção → posto de lado (com incidente). Cabeçalho que o parser ATUAL não reconhece NÃO
 * destrói o recibo (um bug de parser apagaria o acervo inteiro): devolve com `aviso`. HTML de OUTRO acórdão → posto de lado. */
export function lerRecibo(acordao) {
  const num = String(acordao || "").replace(/\D/g, "");
  const caminho = arqRecibo(num);
  let rec = null, shaOk = false, cab = "";
  try {
    rec = JSON.parse(fs.readFileSync(caminho, "utf8"));
    shaOk = sha256(rec.html) === rec.sha256;
    cab = parseTeor(rec.html).acordao;
  } catch (e) {
    if (e.code === "ENOENT") return null;
    shaOk = false; cab = ""; rec = null;
  }
  if (rec !== null && shaOk && rec.acordao === num && (cab === "" || cab === num)) {
    let atual = {};
    try { atual = camposDeCustodia(rec); } catch { atual = {}; }   // parser que falha não atualiza nem destrói o recibo
    if (Object.keys(atual).length && Object.entries(atual).some(([k, v]) => !igual(rec[k], v))) {   // parser melhorou: atualiza sem rede
      try {
        Object.assign(rec, atual);
        const tmp = `${caminho}.${process.pid}.tmp`;
        fs.writeFileSync(tmp, JSON.stringify(rec), { mode: 0o600 });
        fs.renameSync(tmp, caminho);
      } catch { /* melhor esforço */ }
    }
    if (cab === "") rec.aviso = "o cabeçalho deste recibo não foi reconhecido pelo parser atual; conteúdo íntegro (sha256 confere)";
    return rec;
  }
  try { fs.renameSync(caminho, caminho + ".inconsistente"); } catch { /* já movido */ }
  try { pausar(0, `recibo ${num} posto de lado (${!shaOk ? "sha256 não confere" : "HTML de outro acórdão"})`); } catch { /* */ }
  return null;
}
