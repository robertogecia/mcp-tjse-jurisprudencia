// Texto: limpeza de HTML, normalização de comparação, datas. Porte de `servidor_tjse.py` (seção "Texto").
// A referência é o Python: cada função aqui foi conferida contra ele sobre o corpus real (test/paridade).
import { HTML5, CHARREF_INVALIDO, CODEPOINTS_INVALIDOS } from "./entidades.js";

export const MESES = Object.fromEntries(
  ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro",
    "outubro", "novembro", "dezembro"].map((m, i) => [m, i + 1]));

// O Boletim emite &#19; &#24; &#25; (byte baixo de U+2013/2018/2019): antes do unescape, senão o travessão some.
const CP1252_BAIXO = { 0x13: "–", 0x14: "—", 0x18: "‘", 0x19: "’", 0x1c: "“", 0x1d: "”" };

// html.unescape do CPython, sem dependência. Só decodifica o que o CPython decodifica.
const RE_CHARREF = /&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)/g;

function substituiCharref(_m, s) {
  if (s[0] === "#") {
    const num = (s[1] === "x" || s[1] === "X") ? parseInt(s.slice(2).replace(/;$/, ""), 16) : parseInt(s.slice(1).replace(/;$/, ""), 10);
    if (Object.hasOwn(CHARREF_INVALIDO, String(num))) return CHARREF_INVALIDO[String(num)];
    if ((num >= 0xd800 && num <= 0xdfff) || num > 0x10ffff) return "�";
    if (CODEPOINTS_INVALIDOS.has(num)) return "";
    return String.fromCodePoint(num);
  }
  if (Object.hasOwn(HTML5, s)) return HTML5[s];
  for (let x = s.length - 1; x > 1; x--) {  // o CPython procura o MAIOR prefixo conhecido (entidade legada sem ";")
    const pref = s.slice(0, x);
    if (Object.hasOwn(HTML5, pref)) return HTML5[pref] + s.slice(x);
  }
  return "&" + s;
}

export function desescapaHtml(s) {
  return s.includes("&") ? s.replace(RE_CHARREF, substituiCharref) : s;
}

export function limparHtml(frag) {
  frag = frag.replace(/<(script|style)\b[\s\S]*?<\/\1>/gi, " ");
  frag = frag.replace(/<br\s*\/?>|<\/p>|<\/div>|<\/tr>|<\/td>|<\/h\d>/gi, "\n");
  frag = frag.replace(/<[^>]+>/g, "");
  frag = frag.replace(/&#(\d{1,2});/g, (m, n) => CP1252_BAIXO[parseInt(n, 10)] ?? m);
  let t = desescapaHtml(frag).replaceAll(" ", " ");
  t = t.replace(/[ \t\r]+/g, " ");
  return t.replace(/\n\s*\n+/g, "\n").trim();
}

export function semAcento(s) {
  // ASCII puro é o caso comum e não precisa decompor nada
  // eslint-disable-next-line no-control-regex
  if (/^[\x00-\x7f]*$/.test(s)) return s;
  return s.normalize("NFD").replace(/\p{Mn}/gu, "");
}

export function norm(s) {
  s = s.normalize("NFKC");                                   // desfaz ligaduras de PDF e leva º/ª a o/a
  s = semAcento(s).toLowerCase();
  s = s.replace(/(?<![\p{L}\p{N}_])n[o.°]\s*(?=\d)/gu, "n "); // "nº 123", "n. 123", "n° 123" → mesma forma
  s = s.replace(/§\s+/g, "§");
  s = s.replace(/[“”‘’"'`´]/g, "'");
  s = s.replace(/[–—-]/g, "-");
  s = s.replace(/\s+([.,;:)\]])/g, "$1");                    // "art . 42" sai assim do portal
  s = s.replace(/([(\[])\s+/g, "$1");
  return s.replace(/\s+/g, " ").trim();
}

const ORDINAL_EXTENSO = {
  primeira: "1a", segunda: "2a", terceira: "3a", quarta: "4a", quinta: "5a", sexta: "6a", setima: "7a",
  oitava: "8a", nona: "9a", decima: "10a", primeiro: "1a", segundo: "2a", terceiro: "3a",
};
const RE_ORDINAL_EXTENSO = new RegExp(`(?<![\\p{L}\\p{N}_])(${Object.keys(ORDINAL_EXTENSO).join("|")})\\s+(?=camara|turma|secao|grupo)`, "gu");

/** norm() + ordinal por extenso em algarismo, para casar "Primeira Câmara Cível" com "1ª Câmara Cível". */
export function normOrgao(s) {
  return norm(s).replace(RE_ORDINAL_EXTENSO, (_m, o) => ORDINAL_EXTENSO[o] + " ");
}

export function dataPorExtenso(s) {
  const m = /(\d{1,2})\s*(?:º)?\s+de\s+([A-Za-zçÇ]+)\s+de\s+(\d{4})/.exec(s);
  if (!m) return null;
  const mes = MESES[semAcento(m[2]).toLowerCase()];
  if (!mes) return null;
  return isoValida(Number(m[3]), mes, Number(m[1]));
}

/** aaaa-mm-dd se a data existe; null se não (31/02). Equivale ao ValueError de datetime.date. */
export function isoValida(a, m, d) {
  if (a < 1 || a > 9999) return null;
  const dt = new Date(Date.UTC(a, m - 1, d));
  dt.setUTCFullYear(a);  // Date.UTC trata anos 0-99 como 19xx
  if (dt.getUTCFullYear() !== a || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return null;
  return `${String(a).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function br(iso) {
  if (!iso) return "?";
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

/** datetime.now().isoformat(timespec="seconds"): hora LOCAL, sem fuso. */
export function agoraIso() {
  const d = new Date(), p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/** Python `str.split()` sem argumento: quebra em qualquer espaço, ignora vazios. */
export const palavras = (s) => s.split(/\s+/).filter(Boolean);

/** urllib.parse.quote(bytes latin-1, safe=""): o portal é ISO-8859-1. Fora de latin-1 vira "?" (errors="replace"). */
export function quoteLatin1(v) {
  let out = "";
  for (const ch of String(v)) {
    const c = ch.codePointAt(0);
    const b = c <= 0xff ? c : 0x3f;
    const chr = String.fromCharCode(b);
    out += /[A-Za-z0-9_.\-~]/.test(chr) ? chr : "%" + b.toString(16).toUpperCase().padStart(2, "0");
  }
  return out;
}
