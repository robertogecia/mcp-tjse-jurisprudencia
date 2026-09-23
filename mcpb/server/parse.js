// Parsers do Boletim Jurídico e do inteiro teor — porte de `servidor_tjse.py` (seção "Parsers").
// As regex são as do Python, transpiladas por `pyre`; qualquer divergência aparece no teste de paridade.
import { pyre, stripChars } from "./pyre.js";
import { limparHtml, desescapaHtml, norm, normOrgao, dataPorExtenso } from "./texto.js";

export const PARSER_VERSAO = 13;  // mudou o parser → reindexa do HTML bruto em disco, sem rede
export const ORGAOS_FECHO = ["Tribunal Pleno", "Seção Especializada Cível", "1ª Câmara Cível", "2ª Câmara Cível",
  "Câmara Criminal", "Turma de Uniformização", "1ª Turma Recursal", "2ª Turma Recursal", "Turma Recursal",
  "Conselho da Magistratura"];
export const NOME_POR_CODIGO = { 5: "Seção Especializada Cível", 6: "1ª Câmara Cível", 7: "2ª Câmara Cível",
  8: "Câmara Criminal", 10: "Tribunal Pleno" };
const SECOES_SEM_ACORDAO = new Set(["abreviaturas", "composicao do tribunal"]);

export function parseEdicoes(h) {
  const out = [];
  for (const m of h.matchAll(pyre(String.raw`ver\('(\d+)'\);\"><b>(\d+)</b><br><i>\(([^)]+)\)</i>`, "g")))
    out.push({ edicao: Number(m[1]), rotulo: m[2], data: dataPorExtenso(desescapaHtml(m[3])) });
  return out;
}

export function parseMenu(h) {
  const out = [], vistos = new Set();
  const re = pyre(String.raw`Page\("((?:[^"\\]|\\.)*?)","[^"]*","javascript:abre\(\'(\d+)\',\'(\d+)\'\)`, "g");
  for (const m of h.matchAll(re)) {
    const nome = limparHtml(m[1].replace(pyre(String.raw`<!--.*?-->`, "g"), ""));
    const cod = Number(m[2]);
    if (vistos.has(cod) || SECOES_SEM_ACORDAO.has(norm(nome))) continue;
    vistos.add(cod);
    out.push({ codigo: cod, nome });
  }
  return out;
}

const RE_LINK_TEOR = pyre(String.raw`relatorio\.wsp\?(?:tmp\.numprocesso=(\d+)&(?:amp;)?tmp\.numacordao=(\d+)|tmp\.numacordao=(\d+)&(?:amp;)?tmp\.numprocesso=(\d+))`);
export function linkTeor(s) {
  const m = RE_LINK_TEOR.exec(s || "");
  if (!m) return null;
  return m[1] ? { processo: m[1], acordao: m[2] } : { processo: m[4], acordao: m[3] };
}
const RE_ROT_RELATOR = pyre(String.raw`(?i)^(relat[\w()\[\]]*(?:\s+[\wÀ-ÿ()\[\]/.-]+){0,4}?)\s*:\s*(.*)$`);
const RE_CARGO_VAGO = pyre(String.raw`(?i)vaga\s+de\s+desembargador|cargo\s+vago|^des(?:a|\(a\))?\.?\s*$`);
const RE_TD = pyre(String.raw`(?is)<td\b[^>]*>(.*?)</td>`, "g");
const RE_CORTE = pyre(String.raw`(?is)PROCESSO:\s*<a\b`, "g");
const RE_COLADO = pyre(String.raw`(?i)(?<=\S)(?=RELATOR(?:\(A\)|A)?\s+(?:ORIG|DESIGN|PARA\s+O|SUBSTIT|CONVOC))`, "g");
const RE_PARA_AC = pyre(String.raw`PARA O AC|DESIGNAD`);
const RE_RECURSO_N = pyre(String.raw`N[ºo°]\s*\d`);
const colapsa = (s) => s.replace(/\s+/g, " ");

export function parseSecao(h) {
  h = h.replaceAll("<!--", "").replaceAll("-->", "");
  let classe = "";
  const itens = [], vistos = new Set();
  for (const mtd of h.matchAll(RE_TD)) {
    const td = mtd[1];
    const lk = RE_LINK_TEOR.exec(td);
    if (!lk) {
      if (td.includes("font-size: 10pt") && limparHtml(td)) classe = colapsa(limparHtml(td));
      continue;
    }
    const [proc, acord] = lk[1] ? [lk[1], lk[2]] : [lk[4], lk[3]];
    if (vistos.has(acord)) continue;
    vistos.add(acord);
    // a ementa termina no ÚLTIMO "PROCESSO:" seguido do link da consulta (a palavra pode ocorrer na ementa)
    const cortes = [...td.matchAll(RE_CORTE)];
    const corte = cortes.length ? cortes[cortes.length - 1].index : lk.index;
    let ementa = colapsa(limparHtml(td.slice(0, corte))).trim();
    ementa = ementa.replace(pyre(String.raw`(?i)^ementa\s*:\s*`), "");
    const caudaTxt = limparHtml(td.slice(lk.index + lk[0].length)).replace(RE_COLADO, "\n");  // "AC Nº 10491/2026RELATORA ORIGINÁRIA: …" vem colado
    const cauda = caudaTxt.split("\n").map((l) => l.trim()).filter(Boolean);
    let recurso = "", rotulo = "", relator = "";
    for (let k = 0; k < cauda.length; k++) {
      const l = cauda[k];
      const m = RE_ROT_RELATOR.exec(l);
      if (m) {
        const pares0 = [];
        let atual = [m[1].toUpperCase(), [m[2]]];
        for (const l2 of cauda.slice(k + 1)) {
          const m2 = RE_ROT_RELATOR.exec(l2);
          if (m2) { pares0.push(atual); atual = [m2[1].toUpperCase(), [m2[2]]]; }
          else atual[1].push(l2);
        }
        pares0.push(atual);
        const pares = pares0.map(([r, n]) => [r, colapsa(n.join(" ")).trim()]);
        const igual = (a, b) => a[0] === b[0] && a[1] === b[1];
        // quem redige o acórdão é o citável; o originário, quando há os dois, ficou vencido
        let esc = pares.find((x) => RE_PARA_AC.test(x[0])) ?? pares[0];
        if (RE_CARGO_VAGO.test(esc[1]) && pares.length > 1) {
          // "VAGA DE DESEMBARGADOR (G-21)" é marcador administrativo: quem julgou é o substituto/convocado
          esc = pares.find((x) => !igual(x, esc) && !RE_CARGO_VAGO.test(x[1])) ?? esc;
        }
        [rotulo, relator] = esc;
        if (RE_CARGO_VAGO.test(relator)) rotulo += " (marcador administrativo do Boletim — o relator real está no cabeçalho do inteiro teor)";
        const outros = pares.filter((p) => !igual(p, esc)).map(([r, n]) => `${r}: ${n}`);
        if (outros.length) rotulo += " (há também " + outros.join("; ") + ")";
        break;
      }
      if (!recurso && RE_RECURSO_N.test(l)) recurso = l;
    }
    itens.push({ acordao: acord, processo: proc, classe, recurso, relator: colapsa(relator), relator_rotulo: rotulo, ementa });
  }
  return itens;
}

const RE_PROXIMA = pyre(String.raw`submitWIGrid\('grid\.lista_conteudoDiario',\s*(\d+)\)"\s*class='nav_go'`);
export function proximaPosicao(h) {
  const m = RE_PROXIMA.exec(h.slice(-6000));
  return m ? Number(m[1]) : null;
}

export function camposGrid(h) {
  const f = pyre(String.raw`(?is)<form id="wiFormGridNav".*?</form>`).exec(h.slice(-6000));
  const out = {};
  if (!f) return out;
  for (const m of f[0].matchAll(pyre(String.raw`<input type="hidden" name="([^"]+)" value="([^"]*)"`, "g"))) out[m[1]] = desescapaHtml(m[2]);
  return out;
}

export function anomaliasSecao(itens) {
  if (!itens.length) return ["nenhum acórdão reconhecido"];
  const n = itens.length, out = [];
  for (const [campo, piso] of [["relator", 6], ["ementa", 60], ["recurso", 4], ["classe", 3]]) {
    const ruins = itens.filter((i) => i[campo].length < piso).length;
    if (ruins) out.push(`${ruins}/${n} com \`${campo}\` vazio ou curto`);
  }
  return out;
}

// ---------------------------------------------------------------------------- inteiro teor
const RE_FECHO_ACORDAM = pyre(String.raw`(?i)\bacordam\b`, "g");
const RE_EMENTA_CAB = pyre(String.raw`\bE\s?M\s?E\s?N\s?T\s?A\b`);
const RE_JS_INLINE = pyre(String.raw`function carregarTurma\(\)[\s\S]*?\n(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ ]{4,}\n)`);
const RE_DATA_ARACAJU = pyre(String.raw`Aracaju(?:\s*/\s*SE)?\s*,\s*([^\n]{8,40})`, "g");
const RE_ANTES_RELATORIO = pyre(String.raw`\n\s*RELAT[ÓO]RIO\b`);

export function parseTeor(h) {
  let t = limparHtml(h);
  t = t.replace(RE_JS_INLINE, "");  // resíduo de JS inline
  const campo = (rot) => {
    const m = pyre(rot + String.raw`:\s*\n?\s*([^\n]+)`).exec(t);
    return m ? m[1].trim() : "";
  };
  const d = { acordao: campo("ACÓRDÃO"), recurso: campo("RECURSO"), processo: campo("PROCESSO"), relator: campo("RELATOR"), texto: t };
  const mEm = RE_EMENTA_CAB.exec(t);
  d.inicio_conteudo = mEm ? mEm.index : 0;
  d.partes_cortadas = Boolean(mEm);
  // Fecho: só "acordam" seguido de "Estado de Sergipe" (o voto transcreve fechos de outros tribunais). O órgão é o
  // que aparece PRIMEIRO no texto da janela — não o primeiro da lista.
  const fechos = [];
  for (const m of t.matchAll(RE_FECHO_ACORDAM)) {
    let jan = normOrgao(t.slice(m.index, m.index + 450));
    const k = jan.indexOf("estado de sergipe");
    if (k < 0) continue;
    jan = jan.slice(0, k + 140);
    const achados = ORGAOS_FECHO.filter((o) => jan.includes(normOrgao(o)))
      .map((o) => [jan.indexOf(normOrgao(o)), -o.length, o])
      .sort((a, b) => a[0] - b[0] || a[1] - b[1] || (a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0));
    if (achados.length) fechos.push([achados[0][2], m.index]);
  }
  const orgs = new Set(fechos.map((f) => f[0]));
  d.orgao_fecho = orgs.size === 1 ? fechos[0][0] : null;
  d.fecho_ambiguo = orgs.size > 1;
  d.data_julgamento = null;
  d.datas_fecho = [];
  if (fechos.length) {
    let jan = t.slice(fechos[0][1], fechos[0][1] + 900);
    jan = jan.split(RE_ANTES_RELATORIO)[0];
    const datas = [...jan.matchAll(RE_DATA_ARACAJU)].map((g) => dataPorExtenso(g[1])).filter(Boolean);
    d.datas_fecho = [...new Set(datas)].sort();
    if (datas.length) d.data_julgamento = datas[datas.length - 1];
  }
  return d;
}

// ---------------------------------------------------------------------------- ementa estruturada (Res. CNJ)
export const CAMPOS_EMENTA = ["cabecalho", "caso", "questao", "razoes", "dispositivo", "tese", "legislacao", "juris_citada"];
const SECOES_EMENTA = [
  ["caso", String.raw`caso em exame`],
  ["questao", String.raw`quest(?:[aã]o|[õo]es) em discuss[aã]o`],
  ["razoes", String.raw`raz[oõ]es de decidir`],
  ["dispositivo", String.raw`dispositivo(?:\s+e\s+tese)?`],
];
const RE_SECAO = pyre(
  String.raw`(?i)(?:^|[\s.;:]|(?<=[a-zà-ÿ])(?=[IVX]{2,4}[.\-–—)]))` +
  String.raw`(?P<num>(?:[ivx]{1,4}|\d{1,2})\s*[.\-–—)]?\s*)?(?P<rot>` + SECOES_EMENTA.map(([, p]) => p).join("|") +
  String.raw`)(?:\s*[.:\-–—]\s*|\s+|(?=[\dA-ZÀ-Ý]))`, "gd");
const SUBCAMPOS = [
  ["tese", String.raw`teses?\s+de\s+julgamento`],
  ["legislacao", String.raw`(?:dispositivos?|legisla[çc][aã]o)\s+relevantes?\s+citad[oa]s?`],
  ["juris_citada", String.raw`jurisprud[eê]ncia\s+relevante\s+citada`],
];
const RE_SUBCAMPO = pyre(String.raw`(?i)\b(` + SUBCAMPOS.map(([, p]) => p).join("|") + String.raw`)(?:\s*[.:\-–—]\s*|\s+)`, "gd");
const fullmatchI = (p, s) => pyre("^(?:" + p + ")$", "i").test(s);
const RE_E_TESE = pyre(String.raw`(?i)e\s+tese`);

export function camposDaEmenta(ementa) {
  const out = Object.fromEntries(CAMPOS_EMENTA.map((k) => [k, ""]));
  const e = ementa || "";
  let marcas = [], comNum = false;
  for (const m of e.matchAll(RE_SECAO)) {
    const rot = SECOES_EMENTA.find(([, p]) => fullmatchI(p, m.groups.rot))[0];
    // "dispositivo" sozinho é palavra comum de ementa ("dispositivo legal"): só vale como seção com numeral antes ou "e tese" depois
    const num = (m.groups.num || "").trim();
    if (rot === "dispositivo" && !num && !RE_E_TESE.test(m.groups.rot)) continue;
    marcas.push([rot, m.indices.groups.rot[0], m.index + m[0].length, Boolean(num)]);
    comNum = comNum || Boolean(num);
  }
  // "a questão em discussão nos autos" no meio de uma frase também casa: com algum numeral romano, só valem as com numeral
  if (comNum) marcas = marcas.filter((x) => x[3]);
  const orig = marcas;
  marcas = orig.filter((x, i) => i === 0 || x[0] !== orig[i - 1][0]);
  out.cabecalho = stripChars(marcas.length ? e.slice(0, marcas[0][1]) : e, " .;:-–—");
  marcas.forEach(([rot, , fim], i) => {
    const trecho = e.slice(fim, i + 1 < marcas.length ? marcas[i + 1][1] : e.length).trim();
    if (trecho.length > out[rot].length) out[rot] = trecho;  // rótulo repetido: fica a ocorrência com mais conteúdo
  });
  const base = out.dispositivo || out.cabecalho;
  const subs = [...base.matchAll(RE_SUBCAMPO)].map((m) =>
    [SUBCAMPOS.find(([, p]) => fullmatchI(p, m[1]))[0], m.indices[1][0], m.index + m[0].length]);
  subs.forEach(([rot, , fim], i) => { out[rot] = base.slice(fim, i + 1 < subs.length ? subs[i + 1][1] : base.length).trim(); });
  if (subs.length) {
    const cortado = base.slice(0, subs[0][1]).trim();
    if (out.dispositivo) out.dispositivo = cortado;
  }
  return out;
}

// ---------------------------------------------------------------------------- âncoras (súmula/tema/IRDR/IAC)
const RE_ANCORAS = [
  [pyre(String.raw`(?i)s[úu]mula\s+vinculante\s+n?[º°.]*\s*(\d{1,4})`, "g"), "Súmula Vinculante %s"],
  // o número da súmula colide entre tribunais (Súmula 7 do STJ ≠ do TJSE): quando o texto diz de quem é, o rótulo diz
  [pyre(String.raw`(?i)s[úu]mula\s+n?[º°.]*\s*(\d{1,4})(?:\s*/\s*|\s+d[oa]\s+)?(STJ|STF|TJSE|TST)?`, "g"), "Súmula %s"],
  [pyre(String.raw`(?i)tema\s+(?:repetitivo\s+|de\s+repercuss[ãa]o\s+geral\s+)?n?[º°.]*\s*(\d{1,4}(?:\.\d{3})?)`, "g"), "Tema %s"],
  [pyre(String.raw`\bSV\s*n?[º°.]*\s*(\d{1,3})\b`, "g"), "Súmula Vinculante %s"],
  [pyre(String.raw`(?i)\bIRDR\s+n?[º°.]*\s*(\d{1,4})`, "g"), "IRDR %s"],
  [pyre(String.raw`(?i)\bIAC\s+n?[º°.]*\s*(\d{1,4})`, "g"), "IAC %s"],
];
const RE_TRIB_ANTES = pyre(String.raw`(?i)\b(STJ|STF|TJSE|TST|TNU)\b[^.;]{0,12}$`);

/** Precedentes qualificados citados. O tribunal pode vir DEPOIS ("Súmula 297/STJ") ou ANTES ("STJ, Súmula 297"):
 * as duas formas têm de virar a MESMA chave, senão o grafo conta a mesma súmula duas vezes. */
export function ancoras(texto, maxItens = 6) {
  const t = String(texto ?? "");
  const achado = new Map();
  for (const [rx, molde] of RE_ANCORAS) {
    for (const m of t.matchAll(rx)) {
      const n = m[1].replaceAll(".", "");
      if (!n || n === "0") continue;
      let nome = molde.replace("%s", n);
      let trib = m[2] || null;
      if (!trib) {
        const antes = RE_TRIB_ANTES.exec(t.slice(Math.max(0, m.index - 30), m.index));
        trib = antes ? antes[1] : null;
      }
      if (trib && !nome.startsWith("Tema") && !nome.startsWith("IRDR") && !nome.startsWith("IAC")) nome += `/${trib.toUpperCase()}`;
      if (nome.startsWith("Súmula ") && achado.has(`Súmula Vinculante ${n}`)) continue;
      if (!achado.has(nome)) achado.set(nome, m.index);
    }
  }
  // "Súmula 297" e "Súmula 297/STJ" no mesmo texto são a mesma coisa: fica a forma com tribunal
  for (const k of [...achado.keys()].filter((x) => x.includes("/"))) achado.delete(k.split("/")[0]);
  return [...achado.entries()].sort((a, b) => a[1] - b[1]).map(([n]) => n).slice(0, maxItens);
}

const RE_PROC_TJSE_SRC = String.raw`\b((?:19|20)\d{10})\b`;
/** [(tipo, ref)] — o grafo vem do campo "Jurisprudência relevante citada" que o tribunal preenche, mais as âncoras. */
export function citacoesDaEmenta(campos, ementa) {
  const out = new Map();
  const jc = campos.juris_citada || "";
  // processo do próprio TJSE citado: só dentro do campo de jurisprudência, e só quando "TJSE" aparece antes
  for (const m of jc.matchAll(pyre(String.raw`(?i)tjse[^;]{0,160}?` + RE_PROC_TJSE_SRC, "g"))) out.set("tjse\u0000" + m[1], ["tjse", m[1]]);
  for (const a of ancoras(ementa, 20)) out.set("qualificado\u0000" + a, ["qualificado", a]);
  return [...out.values()].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0));
}

// ---------------------------------------------------------------------------- resultado declarado
const RE_NAO_CONHECIDO = pyre(String.raw`\b(?:recurso|apelacao|agravo|embargos|acao|revisao criminal|mandado de seguranca|incidente|reclamacao|conflito|apelo)s?(?: \w+){0,4}? (?:nao (?:se )?conhecid\w+|nao conhecimento)|\bnao conhec(?:o|eram|eu|er|imento) d[oa]s? (?:recurso|apelacao|agravo|embargos|apelo)`);
const RE_PARCIAL = pyre(String.raw`\bparcialmente provid\w+|\bprovid\w+ em parte|\bparcial provimento|\bdar? (?:-se )?parcial provimento|\bdeu-se parcial provimento|\bdera(?:m)? parcial provimento`, "g");
const RE_DESPROV = pyre(String.raw`\bdesprovi\w+|\bimprovi\w+|\bnao provid\w+|\bnegar? (?:-se )?provimento|\bnega-se provimento|\bnegou provimento|\bnegado provimento|\bprovimento negado`, "g");
const RE_PROV = pyre(String.raw`(?<!des)(?<!im)(?<!nao )\bprovid[oa]s?\b|\bdar? (?:-se )?provimento|\bdeu-se provimento|\bderam provimento|\bdou provimento`);

/** 'desprovido' | 'provido' | 'parcialmente provido' | 'não conhecido' | null (ausente ou ambíguo). */
export function resultadoDeclarado(ementa, jaNormalizado = false) {
  let t = jaNormalizado ? ementa : norm(ementa);
  const achou = new Set();
  if (RE_NAO_CONHECIDO.test(t)) achou.add("não conhecido");
  RE_PARCIAL.lastIndex = 0;
  if (RE_PARCIAL.test(t)) { achou.add("parcialmente provido"); t = t.replace(RE_PARCIAL, " "); }
  RE_DESPROV.lastIndex = 0;
  if (RE_DESPROV.test(t)) { achou.add("desprovido"); t = t.replace(RE_DESPROV, " "); }
  if (RE_PROV.test(t)) achou.add("provido");
  return achou.size === 1 ? [...achou][0] : null;
}
