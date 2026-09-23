// Transpilador de expressões regulares Python (`re`) → JavaScript. Existe para que as regex do servidor
// Python possam ser copiadas VERBATIM: Python e JS divergem em \b, \w, \s, ".", "$" e em escapes de
// pontuação (o modo `u` do JS recusa "\-" fora de classe). Cada divergência é resolvida aqui, uma vez.
const W = String.raw`\p{L}\p{N}_`;
const WS = String.raw`\t\n\v\f\r\x1c-\x20\x85\xa0  -     　`;
const FRONTEIRA = `(?:(?<=[${W}])(?![${W}])|(?<![${W}])(?=[${W}]))`;   // \b de Python (Unicode)
const SINTAXE = new Set("^$\\.*+?()[]{}|/".split(""));

export function pyre(src, flags = "") {
  const f = new Set(flags.split("").filter(Boolean));
  const inline = /^\(\?([imsx]+)\)/.exec(src);
  if (inline) { for (const c of inline[1]) f.add(c); src = src.slice(inline[0].length); }
  const dotall = f.has("s");
  const multiline = f.has("m");
  let out = "", classe = false;
  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    if (c === "\\") {
      const n = src[++i];
      if (n === undefined) throw new Error("pyre: barra no fim");
      if (n === "b" && !classe) out += FRONTEIRA;
      else if (n === "w") out += classe ? W : `[${W}]`;
      else if (n === "W") { if (classe) throw new Error("pyre: \\W em classe"); out += `[^${W}]`; }
      else if (n === "s") out += classe ? WS : `[${WS}]`;
      else if (n === "S") out += classe ? "\\S" : `[^${WS}]`;   // em classe só aparece em [\s\S] (qualquer caractere): o \S nativo basta
      else if (/[A-Za-z0-9]/.test(n)) out += "\\" + n;               // \d \n \t \1 …: iguais nas duas
      else if (classe && (n === "-" || n === "]" || n === "[" || n === "\\" || n === "^")) out += "\\" + n;
      else if (SINTAXE.has(n)) out += "\\" + n;
      else out += n;                                                // \' \" \, \: \! …: o modo u recusa
      continue;
    }
    if (classe) { if (c === "]") classe = false; out += c; continue; }
    if (c === "[") {
      classe = true; out += c;
      if (src[i + 1] === "^") { out += "^"; i++; }
      if (src[i + 1] === "]") { out += "\\]"; i++; }                // "]" logo após "[" é literal em Python
      continue;
    }
    if (c === "(" && src.startsWith("(?P<", i)) { out += "(?<"; i += 3; continue; }
    if (c === ".") { out += dotall ? "[\\s\\S]" : "[^\\n]"; continue; }
    if (c === "$" && !multiline) { out += "(?=\\n?(?![\\s\\S]))"; continue; }   // Python: fim ou antes do \n final
    out += c;
  }
  const js = new Set(["u"]);
  if (f.has("i")) js.add("i");
  if (multiline) js.add("m");
  if (f.has("g")) js.add("g");
  if (f.has("d")) js.add("d");
  return new RegExp(out, [...js].join(""));
}

/** re.escape: só o que tem significado no modo `u`. */
export const escapaRe = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");

/** str.strip(chars): tira dos dois lados qualquer caractere do conjunto. */
export function stripChars(s, chars) {
  const set = new Set([...chars]);
  let a = 0, b = s.length;
  while (a < b && set.has(s[a])) a++;
  while (b > a && set.has(s[b - 1])) b--;
  return s.slice(a, b);
}
