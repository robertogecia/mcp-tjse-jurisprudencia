// POSIÇÃO NO JULGADO (06/10/2026, porte do TJRO 1.15) — espelho de _posicao_generica / _posicao_tjse de servidor_tjse.py.
// Localizador, não juiz: diz onde a frase está; decidir se é ratio ou dictum continua sendo de quem lê o acórdão.
// Regex sem a flag `u` (\b ASCII, como o re.ASCII do Python); onde o Python usa \s ASCII vai a classe explícita.
import { norm1 } from "./atribuicao13.js";
import { norm } from "./texto.js";
import { faixaDivergente, bruto as brutoDe } from "./confere.js";

const WS = "[ \\t\\n\\r\\f\\v]";
const RE_DISPOSITIVO_VOTO = /(?<![a-z0-9])(?:ante o exposto|diante do exposto|pelo exposto|em face do exposto|por todo o exposto|posto isso|posto isto|isso posto|isto posto|por tais razoes|por essas razoes|por todas essas razoes|com essas consideracoes|com tais consideracoes|ex positis|forte nessas razoes)(?![a-z0-9])/g;
const RE_RESULTADO_VOTO = /(?<![a-z0-9])(?:nego|dou|conheco|nao conheco|julgo|rejeito|acolho|mantenho|reformo|provimento|provido|desprovido|improcedente|procedente|prejudicado|homologo|declaro|defiro|indefiro|concedo|denego|extingo|anulo|casso|confirmo|voto (?:pelo|por|no sentido))(?![a-z0-9])/;
const ROTULO = {
  "caso em exame": "ementa › I. CASO EM EXAME — resumo do caso, não tese",
  "questao em discussao": "ementa › II. QUESTÃO EM DISCUSSÃO — a pergunta posta, não a resposta",
  "razoes de decidir": "ementa › III. RAZÕES DE DECIDIR — fundamento que a ementa apresenta como razão de decidir (candidato a ratio; confira no voto se o resultado dependeu dele)",
  "dispositivo e tese": "ementa › IV. DISPOSITIVO E TESE — resultado e tese enunciada",
  "dispositivo": "ementa › IV. DISPOSITIVO — resultado do julgamento",
  "cauda": "ementa › parte final (dispositivos e jurisprudência citados, resumo) — referência, não tese",
};

const RE_SECAO_EMENTA_N1 = /(?<![a-z0-9])(?:(i{1,3}|iv|v)[ \t\n\r\f\v]*[.)-]?[ \t\n\r\f\v]*)?(caso em exame|quest(?:ao|oes) em discussao|razoes de decidir|dispositivos? e teses?|dispositivo)(?![a-z0-9])/g;
const RE_CAUDA_EMENTA = /\b(?:Dispositivos? relevantes? citados?|Jurisprud[êe]ncia relevante citada|Legisla[çc][ãa]o relevante citada|Resumo em linguagem simples|RESUMO[ \t]*:)/;
/** Seções da ementa do CNJ em [ini, fim) — espelho de _secoes_da_ementa (06/10/2026): número romano em qualquer caixa, ou nome
 * abrindo a linha e fechando com ".", ":", quebra ou o item numerado. Busca sobre norm1 (1:1); a linha confere no bruto. */
export function secoesDaEmenta(texto, ini, fim) {
  const seg = texto.slice(ini, fim), nt = norm1(seg);
  const marcas = [];
  for (const m of nt.matchAll(RE_SECAO_EMENTA_N1)) {
    const i2 = m.index + m[0].length - m[2].length;
    if (!m[1]) {
      const antes = seg.slice(0, i2).replace(/[ \t]+$/, "");
      const depois = seg.slice(i2 + m[2].length, i2 + m[2].length + 4).replace(/^[ \t]+/, "");
      const c = depois.slice(0, 1);
      if (!(antes === "" || antes.endsWith("\n")) || !(c === "." || c === ":" || c === "\n" || (c !== "" && "0123456789".includes(c)))) continue;
    }
    const nome = m[2].replace(/^quest(?:ao|oes) em discussao$/, "questao em discussao").replace(/^dispositivos? e teses?$/, "dispositivo e tese");
    if (marcas.length && marcas[marcas.length - 1].nome === nome && ini + m.index - marcas[marcas.length - 1].a < 40) continue;
    marcas.push({ nome, a: ini + m.index });
  }
  if (!marcas.length) return [];
  const cauda = seg.search(RE_CAUDA_EMENTA);
  const out = marcas.map((mk, i) => ({ nome: mk.nome, a: mk.a, b: i + 1 < marcas.length ? marcas[i + 1].a : (cauda >= 0 && ini + cauda > mk.a ? ini + cauda : fim) }));
  if (cauda >= 0 && ini + cauda > out[out.length - 1].a) out.push({ nome: "cauda", a: ini + cauda, b: fim });
  return out;
}

export function posicaoGenerica(texto, meio, { ementa = null, relatorio = null, votos = [], outros = [], fecho = null, cabecalho = null, certidao = null } = {}) {
  const dentro = (r) => r !== null && r[0] <= meio && meio < r[1];
  if (dentro(cabecalho)) return "cabeçalho da peça (autuação)";
  if (dentro(ementa)) {
    const s = secoesDaEmenta(texto, ementa[0], ementa[1]).find((x) => x.a <= meio && meio < x.b);
    return s ? ROTULO[s.nome] || s.nome : "ementa (modelo antigo, sem seções) — síntese do julgado";
  }
  if (dentro(fecho)) return "acórdão/fecho (o que o colegiado proclamou)";
  if (dentro(certidao)) return "certidão de julgamento (quem votou e como; não é fundamentação)";
  if (dentro(relatorio)) return "RELATÓRIO — narração do processo e das teses das partes, não decisão";
  for (const [a, b, rot] of outros) if (a <= meio && meio < b) return `${rot} — não é o voto condutor (vencido, vista, vogal ou ementa proposta em outro voto); veja quem venceu`;
  for (const [a, b] of votos) {
    if (!(a <= meio && meio < b)) continue;
    const tn = norm1(texto.slice(a, b));
    let disp = -1;
    for (const m of tn.matchAll(RE_DISPOSITIVO_VOTO)) if (RE_RESULTADO_VOTO.test(tn.slice(m.index, m.index + 300))) disp = a + m.index;
    if (disp >= 0 && meio >= disp) return "DISPOSITIVO do voto — é o que foi decidido, não a razão de decidir";
    if (disp >= 0) return `fundamentação do voto condutor, antes do dispositivo (o dispositivo começa ${disp - meio} caracteres adiante, em «${texto.slice(disp, disp + 60).replace(/[ \t\n\r\f\v]+/g, " ")}…»)`;
    return "fundamentação do voto condutor (dispositivo não localizado por fórmula)";
  }
  return "";
}

/** _posicao_tjse: EMENTA → fecho "ACORDAM… Estado de Sergipe" → RELATÓRIO → VOTO; depois de sinal de divergência, outro voto. */
export function posicaoTjse(bruto, meio) {
  const nt = norm1(bruto), n = bruto.length;
  const mRel = /\bRELAT[ÓO]RIO\b/.exec(bruto);
  const rel = mRel ? mRel.index : -1;
  // fecho: espelho de _posicao_tjse (medição cega 06/10)
  let cands = [];
  for (const m of nt.matchAll(/(?<![a-z0-9])acordam(?![a-z0-9])/g)) if (nt.slice(m.index, m.index + 450).includes("estado de sergipe")) cands.push(m.index);
  for (const m of nt.matchAll(/(?<![a-z0-9])acordao[ \t\n\r\f\v]+(?:vistos|acordam)(?![a-z0-9])/g)) cands.push(m.index);
  for (const m of nt.matchAll(/(?<![a-z0-9])acordam[ \t\n\r\f\v]+(?:os|as)[ \t\n\r\f\v]+(?:membros|desembargador|integrantes|juiz|juizes|magistrad)/g)) cands.push(m.index);
  cands = cands.filter((c) => rel < 0 || c < rel);
  const fechoIni = cands.length ? Math.min(...cands) : -1;
  const rv = /\bVOTO\b/g; rv.lastIndex = Math.max(0, rel);
  const mVoto = rv.exec(bruto);
  const voto = mVoto && rel >= 0 ? mVoto.index : -1;
  const fimEm = Math.min(...[fechoIni, rel, voto, n].filter((x) => x >= 0));
  const ementa = new RegExp(`^${WS}*EMENTA\\b`).test(bruto) ? [0, fimEm] : null;
  const fecho = fechoIni >= 0 ? [fechoIni, rel > fechoIni ? rel : n] : null;
  const relatorio = rel >= 0 ? [rel, voto > rel ? voto : n] : null;
  const tnN = norm(bruto);
  const div = faixaDivergente(tnN, 0);
  let votos = [], outros = [];
  if (voto >= 0) {
    let fimV = n;
    if (div) {
      const d0 = brutoDe(bruto, tnN, div[0]);
      if (d0 > voto) { fimV = d0; outros = [[d0, n, "depois de sinal de divergência"]]; }
    }
    votos = [[voto, fimV]];
  }
  return posicaoGenerica(bruto, meio, { ementa, relatorio, votos, outros, fecho });
}

