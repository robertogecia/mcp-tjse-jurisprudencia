// Conferência literal de citação e alertas de ATRIBUIÇÃO (de quem é a frase) — porte de `servidor_tjse.py`.
// É a parte que mais importa: um "confere" que aponta para ementa do STJ transcrita no voto, ou para o voto
// vencido, produz peça errada. Funções puras; testadas contra o Python em test/paridade.
import { pyre, escapaRe } from "./pyre.js";
import { norm, palavras } from "./texto.js";

const TRIB = String.raw`(?:tj-?[a-z]{2}|stj|stf|trf-?\d|tst|trt-?\d+|tnu)`;
const RE_ATRIB = pyre(
  String.raw`\(` + TRIB + String.raw`\b` +   // "(TJ-MG - …)", "(tj-pr 0048…)", "(STJ, REsp …)"
  String.raw`|\((?:resp|aresp|agint|agrg|edcl|eresp|rms|adi|adpf|apelacao(?: civel)?|agravo de instrumento)\b[^()]{0,220}` +
  String.raw`\brel(?:ator[a]?|\.)?\s*(?:p/|para|min|des|juiz|dr)` +
  String.raw`|\b` + TRIB + String.raw`\s*[-,–]\s*(?:resp|aresp|agint|agrg|edcl|re|are|hc|rhc|apelacao|ac|ai)\b[^.\n]{0,200}\brel`, "g");
const RE_ABRE_BLOCO = pyre(
  String.raw`\bementa\s*:|\bementa\b(?=\s*[-.]?\s*[a-z])|\bacordao\s*:|\bprecedentes?\s*:|\btranscrevo\b|` +
  String.raw`\bin verbis\b|\bnos seguintes termos\s*:|\bassim (?:decidiu|se manifestou|ementado)\b|\bsumula\s+(?:vinculante\s+)?n?\s*\d+\s*[:-]`, "g");
const RE_VOZ_PROPRIA = pyre(String.raw`\b(nesse sentido|neste sentido|com efeito|no caso dos autos|no caso em tela|entendo|ante o exposto|diante do exposto|pelo exposto|e como voto|voto por|voto pelo|passo a|compulsando)\b`);
const RE_CARA_DE_EMENTA = pyre(
  String.raw`\brecurso\s+(?:\w+\s+){0,3}(?:conhecido|provido|desprovido|improvido|nao provido)\b|` +
  String.raw`\btese de julgamento\b|\bcaso em exame\b|\bquestao em discussao\b|\bdispositivos? relevantes?\b|` +
  String.raw`\bsentenca (?:mantida|reformada)\b|\bapelacao\s+(?:civel\s+)?(?:conhecida|provida|desprovida)\b`);
const RE_DIVERGENCIA = pyre(String.raw`\b(?:peco|pedi[dn]o\s+de?|com a devida|data)\s+venia\b[^.]{0,120}\b(?:diverg|discord)|\bdivirjo\b|\bvoto\s+(?:vencido|divergente|vista)\b|\bouso\s+divergir\b|\bvoto[- ]vista\b`);
const RE_ALEGACAO = pyre(String.raw`\b(sustent\w+|aleg\w+|aduz\w*|argument\w+|pugn\w+|requer\w*|assever\w+|defende\w*|afirm\w+|em suas razoes|nas razoes|em contrarrazoes|irresignad\w+)\b`, "g");
const RE_QUEM_ALEGA = pyre(String.raw`\b(apelante|apelad[oa]|agravante|agravad[oa]|recorrente|recorrid[oa]|embargante|embargad[oa]|autor[a]?|reu|re\b|requerente|requerid[oa]|impetrante|parte|banco|ministerio publico|parquet|procuradoria)\b`);
const RE_NEGACAO = pyre(String.raw`\b(nao|jamais|nunca|inexist\w*|descab\w*|incabivel|incabiveis|afasta\w*|inaplicav\w*|indevid\w*|improced\w*|nega\w*|rejeit\w*|sem\s+raz(?:ao|oes)|carece\w*|impossibilidade|vedad[oa]s?)\b[^.;:]{0,60}$`);
const RE_NEGACAO_FALSA = pyre(String.raw`\bnao\s+(obstante|so\b|apenas|somente|se\s+confunde)`);
export const PISO_TRECHO_PALAVRAS = 4, PISO_TRECHO_CHARS = 25, VAO_MAXIMO = 1500, ENCADEIA_MAX = 1200;

/** iterador de matches de `re` (global) começando em `pos` e como se a string acabasse em `endpos` (semântica pos/endpos do Python). */
function* matches(re, s, pos = 0, endpos = null) {
  const alvo = endpos === null ? s : s.slice(0, endpos);
  const r = new RegExp(re.source, re.flags);
  r.lastIndex = pos;
  for (let m; (m = r.exec(alvo));) {
    yield m;
    if (m[0] === "") r.lastIndex++;
  }
}

/** Faixas do texto NORMALIZADO que são palavra de outro julgado: da abertura do bloco ("Ementa:", "Precedentes:",
 * "transcrevo") até a atribuição que o fecha ("(TJ-MG - …)", "STJ - REsp …, Rel."). Alerta por PERTENCIMENTO. */
export function faixasTranscritas(tn, inicio = 0) {
  const faixas = [];
  let piso = inicio;
  for (const m of matches(RE_ATRIB, tn, inicio)) {
    if (m.index < piso) continue;
    let prof = 0, fim = m.index + m[0].length;
    if (tn[m.index] === "(") {
      for (let k = m.index; k < Math.min(tn.length, m.index + 700); k++) {   // parênteses aninhados: "Des.(a) Fulana"
        prof += (tn[k] === "(") - (tn[k] === ")");
        if (prof === 0) { fim = k + 1; break; }
      }
    } else {
      const pt = tn.indexOf(".", m.index + m[0].length);
      fim = (pt >= 0 && pt - (m.index + m[0].length) < 300) ? pt + 1 : m.index + m[0].length;
    }
    const aberturas = [...matches(RE_ABRE_BLOCO, tn, piso, m.index)].map((a) => a.index);
    const intervalo = tn.slice(piso, m.index);
    let ini;
    if (aberturas.length && m.index - aberturas[aberturas.length - 1] <= 9000) {
      // a abertura mais próxima cuja distância até a atribuição não contenha voz própria; senão, a última
      ini = aberturas.find((a) => !RE_VOZ_PROPRIA.test(tn.slice(a, m.index))) ?? aberturas[aberturas.length - 1];
    } else if (faixas.length && !RE_VOZ_PROPRIA.test(intervalo) &&
      (intervalo.length < ENCADEIA_MAX || (intervalo.length < 6000 && RE_CARA_DE_EMENTA.test(intervalo)))) {
      ini = piso;
    } else {
      ini = Math.max(piso, m.index - 300);   // sem abertura reconhecida: recuo curto, para não marcar voto próprio
    }
    faixas.push([ini, fim]);
    piso = fim;
  }
  return faixas;
}

/** Do primeiro sinal de divergência ("peço vênia para divergir", "voto vencido", "voto-vista") até o fim: o que está
 * ali pode ser o voto VENCIDO. Citar voto vencido como se fosse o acórdão é erro sem conserto. */
export function faixaDivergente(tn, inicio = 0) {
  const r = new RegExp(RE_DIVERGENCIA.source, "gu");
  r.lastIndex = inicio;
  const m = r.exec(tn);
  return m ? [m.index, tn.length] : null;
}

const inicioDoVoto = (tn) => {
  const r = pyre(String.raw`\bacordam\b`, "g");
  for (let m; (m = r.exec(tn));) if (tn.slice(m.index, m.index + 450).includes("estado de sergipe")) return m.index;
  return -1;
};
export const inicioDoVotoNormalizado = (tn) => Math.max(inicioDoVoto(tn), 0);

/** Conferência literal por palavra inteira; `[...]` separa fragmentos que devem vir em ordem, a no máximo VAO_MAXIMO caracteres um do outro. */
export function conferir(texto, trecho, inicioVoto = 0) {
  const frags = trecho.split(/\[\s*\.\.\.\s*\]|\(\s*\.\.\.\s*\)/).map((f) => f.trim()).filter(Boolean);
  if (!frags.length) return { ok: false, erro: "trecho vazio" };
  const util = norm(frags.join(" "));
  if (palavras(util).length < PISO_TRECHO_PALAVRAS || util.length < PISO_TRECHO_CHARS)
    return { ok: false, erro: `trecho curto demais para conferência útil (mínimo ${PISO_TRECHO_PALAVRAS} palavras e ${PISO_TRECHO_CHARS} caracteres): qualquer acórdão contém isso` };
  const tn = norm(texto);
  let pos = 0, ini0 = null;
  const spans = [];
  for (const f of frags) {
    const fn = norm(f);
    const re = new RegExp(String.raw`(?<![\p{L}\p{N}_])` + escapaRe(fn) + String.raw`(?![\p{L}\p{N}_])`, "u");
    const m = re.exec(tn.slice(pos));
    if (!m) return { ok: false, fragmento: f };
    const a = pos + m.index, b = pos + m.index + m[0].length;
    if (spans.length && a - spans[spans.length - 1][1] > VAO_MAXIMO)
      return { ok: false, fragmento: f, erro: `o fragmento aparece, mas a ${a - spans[spans.length - 1][1]} caracteres do anterior (máximo ${VAO_MAXIMO}): \`[...]\` não pode costurar partes distantes do acórdão` };
    spans.push([a, b]);
    if (ini0 === null) ini0 = a;
    pos = b;
  }
  const alertas = [];
  if (!inicioVoto) {   // transcrição só existe depois do fecho do próprio TJSE; antes dele é a ementa da casa
    const i = inicioDoVoto(tn);
    if (i >= 0) inicioVoto = i;
  }
  const faixas = faixasTranscritas(tn, inicioVoto);
  const emTranscricao = spans.some(([a, b]) => faixas.some(([fa, fb]) => a < fb && b > fa));
  if (emTranscricao)
    alertas.push("TRANSCRIÇÃO: o trecho está dentro de bloco que o voto transcreve de OUTRO julgado/tribunal — não é palavra do TJSE. Se for citar, cite como o TJSE citando; melhor: pesquise o original.");
  const div = faixaDivergente(tn, inicioVoto);
  if (div && spans.some(([, b]) => b > div[0]))
    alertas.push("VOTO DIVERGENTE: o trecho vem depois de um sinal de divergência no acórdão (pedido de vênia, voto vencido ou voto-vista). Pode ser o voto VENCIDO — leia quem venceu antes de citar como entendimento do órgão.");
  if (!emTranscricao) {
    // aspas: norm() leva todas a ' — ímpar antes + uma depois, perto, = o tribunal está citando alguém
    const antesQ = tn.slice(Math.max(0, ini0 - 1200), ini0), depoisQ = tn.slice(pos, pos + 1200);
    const nQ = (antesQ.match(/(?<![a-z])'|'(?![a-z])/g) || []).length;
    if (nQ % 2 === 1 && /'(?![a-z])/.test(depoisQ))
      alertas.push("ENTRE ASPAS: o trecho parece estar dentro de aspas no acórdão — é o tribunal citando alguém (doutrina, lei, decisão recorrida, outro julgado). Confira de quem é a frase antes de atribuí-la ao TJSE.");
    const jan = tn.slice(Math.max(0, ini0 - 400), ini0);
    let ult = -1;
    for (const x of matches(RE_ALEGACAO, jan)) ult = Math.max(ult, x.index + x[0].length);
    if (ult >= 0 && RE_QUEM_ALEGA.test(jan.slice(Math.max(0, ult - 160), ult + 160)) && !RE_VOZ_PROPRIA.test(jan.slice(ult)))
      alertas.push("ALEGAÇÃO DA PARTE: pouco antes do trecho o texto relata o que uma parte (ou o MP) sustenta/alega — o trecho pode ser tese da parte, não decisão do tribunal. Confira no relatório/voto quem fala.");
  }
  const antes = tn.slice(Math.max(0, ini0 - 90), ini0);
  if (RE_NEGACAO.test(antes) && !RE_NEGACAO_FALSA.test(antes.slice(-40)))
    alertas.push("NEGAÇÃO: há negativa logo antes do trecho — o recorte pode inverter o julgado. Não citar sem ler.");
  return { ok: true, alertas, contexto: tn.slice(Math.max(0, ini0 - 120), pos + 120).replace(/\s+/g, " ") };
}

/** Posição no texto BRUTO equivalente a `posNorm` no texto normalizado. norm() só colapsa e remove: a razão entre os
 * comprimentos é estável, então caminha-se do palpite proporcional até casar o contexto. */
export function bruto(corpo, tn, posNorm) {
  if (posNorm <= 0) return 0;
  if (posNorm >= tn.length) return corpo.length;
  const alvo = norm(tn.slice(posNorm, posNorm + 40)).slice(0, 24);
  const proporcional = Math.trunc(posNorm * corpo.length / Math.max(tn.length, 1));
  if (!alvo) return Math.min(corpo.length, proporcional);
  const chute = Math.min(corpo.length - 1, proporcional);
  for (const raio of [60, 400, 2000, corpo.length]) {
    const ini = Math.max(0, chute - raio), fim = Math.min(corpo.length, chute + raio);
    const k = norm(corpo.slice(ini, fim)).indexOf(alvo);
    if (k < 0) continue;
    // k é índice no normalizado do recorte: reconstrói caminhando caractere a caractere
    let conta = 0;
    for (let i = ini; i < fim; i++) {
      const n = norm(corpo.slice(ini, i + 1)).length;
      if (n > conta) conta = n;
      if (conta > k) return i;
    }
    return ini;
  }
  return chute;
}

const PARTICULAS = new Set(["de", "da", "do", "das", "dos", "e", "d'"]);
export const nomeProprio = (s) => palavras(s).map((w, i) =>
  (PARTICULAS.has(w.toLowerCase()) && i) ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ");
