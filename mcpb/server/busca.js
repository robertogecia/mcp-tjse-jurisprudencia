// Busca no índice local — porte de `servidor_tjse.py` (consulta FTS5, panorama, diagnóstico de zero, grafo de citações).
import { pyre } from "./pyre.js";
import { norm, semAcento, br, palavras, isoValida } from "./texto.js";
import { ancoras, resultadoDeclarado } from "./parse.js";
import { URL_TEOR, PedidoRecusado, ondeMaisProcurar } from "./config.js";
import { db, um, todos, escalar, cobertura } from "./indice.js";
import { lerRecibo } from "./recibos.js";

const W = String.raw`\p{L}\p{N}_`;

// palavras curtas e invariáveis/funcionais não ganham variante: "pais→pal", "onus→onu", "nao→noes"
const SEM_VARIANTE = new Set(("pais leis seis dois reis jamais demais quais tais onus lapis tres caos simples pires atras alias apenas antes depois menos " +
  "mais entao senao orgao sotao virus bonus campus status habeas corpus versus reus deus juros custas ferias nupcias viveres anais arredores pesames oculos").split(" "));

/** Singular/plural de uma palavra já sem acento e minúscula. FTS5 não tem stemmer de português e prefixo não resolve
 * plural irregular (moral→morais, acao→acoes). Variante inexistente é inofensiva: só não casa. */
export function variantesNumero(w) {
  const v = [w];
  if ([...w].length < 4 || !/^\p{L}+$/u.test(w) || SEM_VARIANTE.has(w)) return v;
  const regras = [["oes", ["ao"]], ["aes", ["ao"]], ["aos", ["ao"]], ["ais", ["al"]], ["eis", ["el"]], ["ois", ["ol"]],
    ["ns", ["m"]], ["res", ["r"]], ["zes", ["z"]], ["ses", ["s"]], ["ao", ["oes", "aos", "aes"]], ["al", ["ais"]],
    ["el", ["eis"]], ["ol", ["ois"]], ["il", ["is"]], ["m", ["ns"]], ["r", ["res"]], ["z", ["zes"]]];
  let achou = false;
  for (const [suf, trocas] of regras) {
    if (w.endsWith(suf)) { for (const t of trocas) v.push(w.slice(0, -suf.length) + t); achou = true; break; }
  }
  if (!achou) v.push(w.endsWith("s") ? w.slice(0, -1) : w + "s");
  return v.slice(0, 4);
}

export function fraseFts(termo, exato = false) {
  termo = termo.trim();
  const radical = new RegExp(String.raw`[\p{L}\p{Nl}\p{No}]{3,}[$*]$`, "u").test(termo);   // "R$" não é radical
  const pal = palavras(semAcento(termo).toLowerCase().replace(new RegExp(`[^${W}\\s]`, "gu"), " "));
  if (!pal.length) return "";
  if (radical) return '"' + pal.join(" ") + '"*';
  if (exato) return '"' + pal.join(" ") + '"';
  let combos = [[]];
  for (const w of pal) {
    let vs = variantesNumero(w);
    if (combos.length * vs.length > 36) vs = vs.slice(0, 1);
    combos = combos.flatMap((c) => vs.map((x) => [...c, x]));
  }
  const fr = combos.map((c) => '"' + c.join(" ") + '"');
  return fr.length === 1 ? fr[0] : "(" + fr.join(" OR ") + ")";
}

// Palavras que não distinguem um acórdão de outro. Sem removê-las, a pergunta em português vira um E lógico com
// artigo e preposição dentro — o harness mediu 0 % de recall. "nao", "sem" e "menor" NÃO entram: mudam o sentido jurídico.
const VAZIAS = new Set(`a o as os um uma uns umas de do da dos das em no na nos nas por para pelo pela pelos pelas com
sob sobre entre ate apos ante e ou mas que se qual quais quando onde como porque pois ja sim ha he ser sao foi
era eram tem tinha teve havia deve devem pode podem existe existem qualquer algum alguma
seguinte seguintes mesmo mesma outro outra seu sua seus suas este esta isso aquilo lhe lhes ao aos`.split(/\s+/).filter(Boolean));

/** [(rótulo legível, expressão FTS, obrigatório?)] — um item por grupo e um por palavra solta da consulta.
 * Palavras soltas combinam por OU (o ranking põe no topo quem tem mais delas); "entre aspas" e `grupos` são obrigatórios. */
export function partesFts(consulta, grupos, exato = false) {
  const partes = [];
  for (const g of grupos || []) {
    const fr = g.map((x) => fraseFts(x, exato)).filter(Boolean);
    if (!fr.length) throw new PedidoRecusado(`o grupo ${pyRepr(g)} não tem nenhum termo pesquisável (só pontuação?) — se ele sumisse em silêncio, o E entre grupos deixaria de valer.`);
    partes.push(["[" + g.join(" | ") + "]", "(" + fr.join(" OR ") + ")", true]);
  }
  if (consulta) {
    const foraDeAspas = consulta.replace(/"[^"]*"/g, " ");
    if (pyre(String.raw`\b(E|OU|NAO|NÃO|ADJ\d*|PROX\d*|AND|OR|NOT|NEAR)\b`).test(foraDeAspas))
      throw new PedidoRecusado("operador em caixa alta não é aceito na `consulta` (índice local FTS5): use `grupos` — cada grupo é OU entre sinônimos, grupos se combinam em E.");
    const soltas = [], ignoradas = [];
    for (const m of consulta.matchAll(pyre(String.raw`"([^"]+)"|(\S+)`, "g"))) {
      const aspas = Boolean(m[1]), tok = m[1] || m[2];
      const f = fraseFts(tok, exato);
      if (!f) continue;
      if (aspas) partes.push([`"${tok}"`, fraseFts(tok, true), true]);   // aspas = exatamente isso: sem variante
      else if (VAZIAS.has(norm(tok)) || norm(tok).replace(new RegExp(`[^${W}]`, "gu"), "").length <= 2) ignoradas.push(tok);
      else soltas.push([tok, f, Boolean(exato)]);   // `exato` também obriga cada palavra da consulta
    }
    partes.push(...soltas);
    if (ignoradas.length) partes.push(["__ignoradas__:" + ignoradas.join(", "), "", null]);
    if (!partes.some((x) => x[2] !== null))
      throw new PedidoRecusado("a consulta só tem palavras comuns (artigos, preposições, palavras de praxe do jargão), que não distinguem um acórdão de outro — use termos do tema, ou `grupos`.");
  }
  return partes;
}

/** repr() de uma lista de strings do Python — só para a mensagem de erro do grupo vazio. */
const pyRepr = (g) => "[" + g.map((x) => `'${x}'`).join(", ") + "]";

export function expressaoFts(partes) {
  const obrig = partes.filter((p) => p[2] === true).map((p) => p[1]);
  const opc = partes.filter((p) => p[2] === false).map((p) => p[1]);
  if (opc.length) obrig.push(opc.length > 1 ? "(" + opc.join(" OR ") + ")" : opc[0]);
  return obrig.join(" AND ");
}

// ---------------------------------------------------------------------------- panorama
export const PANORAMA_MAX = 800;
const STOP_VOCAB = new Set(`recurso conhecido provido desprovido acordao decisao agravo apelacao relator camara civel interposto contra
    embargos direito processual civil ementa turma tribunal justica sergipe tese julgamento unanimidade unanime votos voto
    dispositivo relevantes citados jurisprudencia constituicao federal codigo artigo artigos casos exame razoes decidir
    questao discussao apelante apelado agravante agravado recorrente recorrido sentenca juizo primeiro grau parte partes`.split(/\s+/).filter(Boolean));

/** round() do Python (meio para o par) — `f"{x:.0f}"` usa o mesmo critério e o toFixed do JS não. */
const arredondaPar = (x) => { const r = Math.round(x); return (Math.abs(x % 1) === 0.5 && r % 2 !== 0) ? r - 1 : r; };

/** Palavras bem mais frequentes nas ementas que casam do que no índice inteiro (lift), candidatas a novo grupo de sinônimos. */
export function pistasVocabulario(con, ementas, excluir, maxItens = 12, jaNormalizado = false) {
  const n = ementas.length;
  if (n < 8) return [];
  const df = new Map();
  for (const e of ementas) for (const w of new Set((jaNormalizado ? e : norm(e)).match(/[a-z]{5,}/g) || [])) df.set(w, (df.get(w) || 0) + 1);
  const piso = Math.max(4, Math.trunc(n * 0.06));
  const cand = [...df].filter(([w, c]) => c >= piso && !STOP_VOCAB.has(w) && !excluir.has(w)).map(([w]) => w);
  if (!cand.length) return [];
  const total = escalar(con, "SELECT COUNT(*) FROM acordaos") || 1;
  const geral = new Map();
  for (let k = 0; k < cand.length; k += 400) {
    const lote = cand.slice(k, k + 400);
    for (const r of todos(con, `SELECT term, doc FROM fts_vocab WHERE term IN (${lote.map(() => "?").join(",")})`, ...lote)) geral.set(r.term, r.doc);
  }
  const pont = [];
  for (const w of cand) {
    const lift = (df.get(w) / n) / (Math.max(geral.get(w) ?? 1, 1) / total);
    if (lift >= 2.5) pont.push([lift * Math.sqrt(df.get(w)), w, df.get(w), lift]);
  }
  // sorted(pont, reverse=True): tuplas em ordem decrescente
  pont.sort((a, b) => (b[0] - a[0]) || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0) || (b[2] - a[2]) || (b[3] - a[3]));
  return pont.slice(0, maxItens).map(([, w, c, l]) => `${w} (${c}, ×${arredondaPar(l)})`);
}

const contar = (mapa, k) => mapa.set(k, (mapa.get(k) || 0) + 1);
const topN = (mapa, n = 6) => [...mapa].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `${k} ${v}`).join(" · ");

export function panorama(con, sql, args, porBm25, total, excluir) {
  const ordem = porBm25 ? "r.rk" : "a.edicao DESC";
  const linhas = todos(con, `SELECT a.orgao, a.classe, a.ementa${sql} ORDER BY ${ordem} LIMIT ${PANORAMA_MAX}`, ...args);
  if (linhas.length < 5) return "";
  const res = new Map(), orgs = new Map(), clas = new Map(), cit = new Map();
  const normalizadas = linhas.map((x) => norm(x.ementa));
  linhas.forEach((x, i) => {
    contar(res, resultadoDeclarado(normalizadas[i], true) || "sem resultado identificável");
    contar(orgs, x.orgao); contar(clas, x.classe);
    for (const a of new Set(ancoras(x.ementa, 12))) contar(cit, a);
  });
  const ordemRes = ["desprovido", "provido", "parcialmente provido", "não conhecido", "sem resultado identificável"];
  const resumo = ordemRes.filter((k) => res.has(k)).map((k) => `${k} ${res.get(k)}`).join(" · ");
  const pistas = pistasVocabulario(con, normalizadas, excluir, 12, true);
  const ancs = [...cit].sort((a, b) => b[1] - a[1]).slice(0, 8).filter(([, v]) => v >= 2).map(([k, v]) => `${k} (${v})`).join(" · ");
  const parcial = total > PANORAMA_MAX ? ` (as ${PANORAMA_MAX} mais relevantes de ${total})` : "";
  const out = [`PANORAMA das ${linhas.length} ementas que casam${parcial} — indício para decidir o que ler, NÃO posição sobre a tese (recurso provido por outro fundamento também conta como provido):`,
    `  Resultado declarado na ementa: ${resumo}`, `  Por órgão (seção do Boletim): ${topN(orgs)}`, `  Por classe: ${topN(clas)}`];
  if (ancs) out.push(`  Citados nas ementas: ${ancs} — precedentes qualificados: âncora para novo grupo de busca; confirme a situação de cada um na fonte própria (súmula/tema/IRDR se confere no BNP do CNJ, e superação na fonte oficial)`);
  if (pistas.length) out.push("  Vocabulário que distingue estas ementas do resto do índice (termo (ementas, × frequência relativa)): " + pistas.join(", ") + " — hipótese de sinônimo/conceito vizinho para um novo grupo; a busca confirma ou descarta");
  return out.join("\n") + "\n";
}

/** Busca que zerou: qual grupo/termo zera, e o que aconteceria sem cada um. */
export function diagnosticoZero(con, partes) {
  if (partes.length < 2) return "";
  const cont = (ex) => escalar(con, "SELECT COUNT(*) FROM fts WHERE fts MATCH ?", ex);
  const linhas = [];
  partes.map((x, i) => [x, i]).filter(([x]) => x[2] !== null).slice(0, 8).forEach(([[rot, ex], k]) => {
    const so = cont(ex);
    const sem = cont(expressaoFts(partes.filter((_, i) => i !== k)) || ex);
    linhas.push(`  ${rot}: sozinho ${so} · sem ele, o resto tem ${sem}`);
  });
  return "\nO que zerou a busca (contagem por grupo/termo no índice inteiro):\n" + linhas.join("\n") +
    "\n  → o grupo com 'sozinho 0' não existe no índice (vocabulário: tente outros sinônimos); se todos existem, é a combinação que não ocorre — afrouxe o grupo cuja retirada mais devolve.";
}

export function outrosAcordaosDoProcesso(con, processo, acordao) {
  const rows = todos(con, "SELECT acordao, recurso FROM acordaos WHERE processo=? AND acordao<>? ORDER BY acordao", processo, acordao);
  if (!rows.length) return "";
  const lista = rows.slice(0, 5).map((r) => `${r.acordao} (${r.recurso || "acórdão"})`).join("; ");
  return `⚠ este PROCESSO tem outro(s) acórdão(s) no índice: ${lista}${rows.length > 5 ? " …" : ""} — embargos ou recurso posterior podem ter alterado ou esclarecido o julgado; a citação vale para o acórdão que você abriu`;
}

// ---------------------------------------------------------------------------- busca
export const CAMPOS_BUSCAVEIS = ["cabecalho", "caso", "questao", "razoes", "dispositivo", "tese"];
const PESO_CAMPO = { cabecalho: 3.0, caso: 1.0, questao: 5.0, razoes: 2.0, dispositivo: 1.0, tese: 5.0 };
const pyFloat = (x) => (Number.isInteger(x) ? x.toFixed(1) : String(x));   // str(3.0) == "3.0"

/** Chave sem o tribunal: "Súmula 297" e "Súmula 297/STJ" são o MESMO precedente. */
export const baseRef = (ref) => (ref || "").split("/")[0].trim();

/** Normaliza o que o usuário pediu em `cita` para a chave do grafo. */
export function refCitada(cita) {
  const dig = (cita || "").replace(/\D/g, "");
  if (dig.length === 12) return ["tjse", dig];
  const a = ancoras(cita || "", 1);
  if (a.length) return ["qualificado", a[0]];
  const m = pyre(String.raw`(?i)\s*(sv|s[uú]mula\s+vinculante)\s*n?[º°.]*\s*(\d{1,4})`).exec(cita || "");
  return m && m.index === 0 ? ["qualificado", `Súmula Vinculante ${m[2]}`] : null;
}

function dataIso(v, rotulo) {
  if (!v) return null;
  let m = /^\s*(\d{2})\/(\d{2})\/(\d{4})\s*$/.exec(v), d, me, a;
  if (m) [, d, me, a] = m;
  else {
    m = /^\s*(\d{4})-(\d{2})-(\d{2})\s*$/.exec(v);
    if (!m) throw new PedidoRecusado(`\`${rotulo}\` deve ser dd/mm/aaaa ou aaaa-mm-dd`);
    [, a, me, d] = m;
  }
  const iso = isoValida(Number(a), Number(me), Number(d));
  if (!iso) throw new PedidoRecusado(Number(me) < 1 || Number(me) > 12 ? "month must be in 1..12" : "day is out of range for month");
  return iso;
}

export function buscar(p) {
  try { return _buscar(p); } catch (ex) {
    return `BUSCA NÃO REALIZADA — erro do índice local (${ex.name}: ${ex.message}). Isto NÃO é 'nada encontrado': reformule sem pontuação especial ou rode \`diagnostico_tjse\`.` + (p._relato ? p._relato("busca_indice_local") : "");
  }
}

function _buscar({ consulta = null, grupos = null, orgao = null, classe = null, relator = null, numero = null, por_pagina = 10, pagina = 1,
  data_inicio = null, data_fim = null, ordenacao = "relevantes", exato = false, em = "tudo", cita = null, triagem = false }) {
  const con = db();
  const cab = `Índice local do Boletim Jurídico do TJSE: ${cobertura(con)}.\n`;
  const rodape = "\nLIMITES: só 2º grau publicado no Boletim — sem Turmas Recursais, Turma de Uniformização nem monocráticas, e só as edições sincronizadas. " +
    "Zero resultado aqui NÃO é 'não localizado no TJSE'. " + ondeMaisProcurar() + " Ementa do Boletim vem em CAIXA ALTA: para citar entre aspas, `verificar_citacao_tjse` (confere no inteiro teor).";
  const where = []; let args = [];
  if (numero) {
    const n = numero.replace(/\D/g, "");
    // acórdão = ano + sequencial SEM zeros à esquerda ("2026" + "6743" = 20266743): 5 a 9 dígitos. Achado em 23/09/2026:
    // 16,5% do índice tem acórdão com menos de 9 dígitos, e a validação antiga (só 9 ou 12) os recusava.
    if (!((n.length >= 5 && n.length <= 9) || n.length === 12))
      return `Pedido recusado: \`numero\` com ${n.length} dígitos. O TJSE numera por PROCESSO (12 dígitos, ex. 202600737656) e ACÓRDÃO (ano + sequencial, de 5 a 9 dígitos, ex. 202561964 ou 20266743); o Boletim e o inteiro teor não trazem número CNJ, então não há como buscar por ele aqui. Isto NÃO é 'não localizado'.`;
    where.push("(a.acordao=? OR a.processo=?)"); args.push(n, n);
  }
  let partes, q, di, df;
  try {
    partes = partesFts(consulta, grupos, exato);
    q = expressaoFts(partes);
    di = dataIso(data_inicio, "data_inicio"); df = dataIso(data_fim, "data_fim");
    if (di && df && di > df) throw new PedidoRecusado(`\`data_inicio\` (${br(di)}) é posterior a \`data_fim\` (${br(df)}) — filtro impossível, não ausência de julgado`);
  } catch (ex) {
    if (ex instanceof PedidoRecusado) return `Consulta recusada: ${ex.message}`;
    throw ex;
  }
  if (!q && !numero && !cita) return "Informe `consulta`, `grupos`, `numero` ou `cita`.";
  let colunas = [];
  let camposPedidos = (em || "tudo").split(/[,;+ ]+/).map((c) => c.trim().toLowerCase()).filter(Boolean);
  if (!camposPedidos.length) camposPedidos = ["tudo"];   // `em=" "` montava "{} : (…)" e derrubava a busca com erro de sintaxe do FTS5
  const tudo = camposPedidos.length === 1 && camposPedidos[0] === "tudo";
  let tabFts, qFts, pesos;
  if (tudo) { tabFts = "fts"; qFts = q; pesos = "0, 5.0, 2.0, 1.0"; }
  else {
    const ruins = camposPedidos.filter((c) => !CAMPOS_BUSCAVEIS.includes(c));
    if (ruins.length)
      return `\`em\` não conhece [${ruins.map((r) => `'${r}'`).join(", ")}]. Use 'tudo' ou um ou mais de: ${CAMPOS_BUSCAVEIS.join(", ")} (são as partes da ementa estruturada; ~2/3 dos acórdãos a seguem). O \`cabecalho\` — o resumo em caixa alta, que toda ementa tem — entra junto com peso baixo, para que o acórdão sem ementa estruturada não desapareça da busca por campo.`;
    tabFts = "fts_campos";
    // 1/3 das ementas não segue o padrão CNJ e tem TUDO em `cabecalho`. Sem incluí-lo, buscar por `questao` perde esses acórdãos.
    colunas = [...camposPedidos, ...(camposPedidos.includes("cabecalho") ? [] : ["cabecalho"])];
    qFts = q ? "{" + colunas.join(" ") + "} : (" + q + ")" : q;
    pesos = "0, " + CAMPOS_BUSCAVEIS.map((c) => pyFloat(camposPedidos.includes(c) ? PESO_CAMPO[c] : (c === "cabecalho" ? 0.5 : 0.0))).join(", ");
  }
  let filtrosCita = "";
  if (cita) {
    const ref = refCitada(cita);
    if (!ref) return `\`cita\`=${pyRepr1(cita)} não é uma referência que o grafo conheça. Use 'Tema 1061', 'Súmula 479/STJ', 'IRDR 15', 'SV 47' ou o nº de PROCESSO do TJSE (12 dígitos).`;
    const b = baseRef(ref[1]);
    where.push("a.acordao IN (SELECT origem FROM citacoes WHERE tipo=? AND (ref=? OR ref LIKE ?))");
    args.push(ref[0], b, b + "/%");
    filtrosCita = `cita=${ref[1]}`;
  }
  const porBm25 = Boolean(q) && ordenacao === "relevantes";
  if (q && !porBm25) { where.push(`a.acordao IN (SELECT acordao FROM ${tabFts} WHERE ${tabFts} MATCH ?)`); args.push(qFts); }
  for (const [col, val] of [["orgao", orgao], ["classe", classe], ["relator", relator]]) {
    if (val) {
      const esc = val.replaceAll("\\", "\\\\").replaceAll("%", "\\%").replaceAll("_", "\\_");
      where.push(`a.${col} LIKE ? ESCAPE '\\'`); args.push(`%${esc}%`);
    }
  }
  if (di) { where.push("e.data >= ?"); args.push(di); }
  if (df) { where.push("e.data <= ?"); args.push(df); }
  const filtros = [["orgao", orgao], ["classe", classe], ["relator", relator], ["numero", numero], ["data_inicio", data_inicio], ["data_fim", data_fim], ["cita", cita]]
    .filter(([, v]) => v).map(([k, v]) => `${k}=${pyRepr1(v)}`);
  const cond = where.join(" AND ") || "1=1";
  // COBERTURA: quantas unidades da consulta o acórdão casa. Sem isso, com palavras soltas em OU, um acórdão que casa um
  // único termo periférico disputa o topo com outro que casa todos — e o advogado só olha os 10 primeiros.
  const unidades = partes.filter((x) => x[2] === false).map((x) => x[1]);
  const ignoradas = partes.filter((x) => x[2] === null).map((x) => x[0].split(":").slice(1).join(":"));
  partes = partes.filter((x) => x[2] !== null);
  const usaCobertura = porBm25 && unidades.length > 1;
  let base, uniArgs = [];
  if (porBm25) {
    if (usaCobertura) {
      const uniSql = unidades.map(() => `SELECT acordao FROM ${tabFts} WHERE ${tabFts} MATCH ?`).join(" UNION ALL ");
      uniArgs = unidades.map((u) => (!tudo ? "{" + colunas.join(" ") + "} : (" + u + ")" : u));
      base = `(SELECT acordao ac, bm25(${tabFts}, ${pesos}) rk FROM ${tabFts} WHERE ${tabFts} MATCH ?) r JOIN acordaos a ON a.acordao = r.ac JOIN edicoes e USING(edicao) ` +
        `LEFT JOIN (SELECT acordao, COUNT(*) k FROM (${uniSql}) GROUP BY acordao) cob ON cob.acordao = a.acordao`;
      args = [qFts, ...uniArgs, ...args];
    } else {
      base = `(SELECT acordao ac, bm25(${tabFts}, ${pesos}) rk FROM ${tabFts} WHERE ${tabFts} MATCH ?) r JOIN acordaos a ON a.acordao = r.ac JOIN edicoes e USING(edicao)`;
      args = [qFts, ...args];
    }
  } else base = "acordaos a JOIN edicoes e USING(edicao)";
  const sql = ` FROM ${base} WHERE ${cond}`;
  const total = escalar(con, "SELECT COUNT(*) n" + sql, ...args);
  if (!q) ordenacao = ordenacao === "relevantes" ? "recentes" : ordenacao;   // sem texto não há relevância: diz a ordem real
  por_pagina = triagem ? 30 : (por_pagina <= 5 ? 5 : (por_pagina <= 10 ? 10 : 20));
  pagina = Math.max(1, Math.trunc(pagina));
  if (!["relevantes", "recentes", "antigos"].includes(ordenacao)) return "`ordenacao` deve ser 'relevantes', 'recentes' ou 'antigos'.";
  let rows;
  if (porBm25) {
    const ordemRk = usaCobertura ? "COALESCE(cob.k, 0) DESC, r.rk" : "r.rk";
    rows = todos(con, `SELECT a.*, e.data ed_data${usaCobertura ? ", COALESCE(cob.k, 0) cobertura" : ""}${sql} ORDER BY ${ordemRk}, a.edicao DESC, a.acordao DESC LIMIT ? OFFSET ?`,
      ...args, por_pagina, (pagina - 1) * por_pagina);
  } else {
    const ord = ordenacao === "antigos" ? "ASC" : "DESC";
    rows = todos(con, `SELECT a.*, e.data ed_data${sql} ORDER BY a.edicao ${ord}, a.acordao ${ord} LIMIT ? OFFSET ?`, ...args, por_pagina, (pagina - 1) * por_pagina);
  }
  const nUni = unidades.length;
  const filtroData = (di || df) ? ` · publicação de ${br(di)} a ${br(df)} (data do BOLETIM, não do julgamento)` : "";
  if (!rows.length && total) return cab + `${total} resultado(s), mas a página ${pagina} está além do fim (última: ${Math.ceil(total / por_pagina)}).` + rodape;
  if (!rows.length) {
    let semFiltro = "";
    if (q && filtros.length) {
      const n0 = escalar(con, `SELECT COUNT(*) n FROM ${tabFts} WHERE ${tabFts} MATCH ?`, qFts);
      if (n0) semFiltro = ` SEM os filtros (${filtros.join(", ")}) a mesma expressão tem ${n0} resultado(s) — foi o filtro que zerou, não a falta de julgado.`;
    }
    return cab + `Nada no índice local para ${pyRepr1(q || numero)}${filtroData}.${semFiltro}` + (q ? diagnosticoZero(con, partes) : "") + rodape;
  }
  if (triagem) {
    // Reordenação por quem lê (experimento de 23/09/2026, juiz cego: precisão@10 de 40% para 53% com reranker); aqui o reranker é o próprio Claude.
    const lin = [cab + `MODO TRIAGEM — ${total} resultado(s); ${rows.length} candidatos abaixo (página ${pagina}, ordem: ${ordenacao}${filtroData}). ` +
      "LEIA cada ementa e ordene você: descarte o que não trata do problema jurídico pedido e promova o que trata; só depois aprofunde (`obter_inteiro_teor_tjse`) e, para aspas, `verificar_citacao_tjse`.\n" +
      `expressão: ${q.length < 700 ? q : q.slice(0, 700) + "…"}\n`];
    rows.forEach((r, i) => {
      const et = r.ementa;
      lin.push(`${i + 1}. Acórdão ${r.acordao} · processo ${r.processo} · ${r.recurso || r.classe} · ${r.orgao} · ${r.relator}\n   ${et.length <= 700 ? et : et.slice(0, 700) + "…"}\n`);
    });
    return lin.join("\n") + rodape;
  }
  const termos = (grupos || []).flatMap((g) => g.map(norm));
  for (const m of (consulta || "").matchAll(pyre(String.raw`"([^"]+)"|(\S+)`, "g"))) termos.push(norm(m[1] || m[2]));
  const out = [cab + `${total} resultado(s) — página ${Math.max(1, pagina)} (${por_pagina}/pág.) — ordem: ${ordenacao}${filtroData}` +
    (usaCobertura ? ` · ordenado primeiro por quantos dos ${nUni} termos o acórdão casa` : "") +
    (ignoradas.length ? ` · palavras ignoradas por serem de praxe: ${ignoradas.join(", ")}` : "") +
    (!tudo ? ` · campo: ${camposPedidos.join("+")} (+ cabeçalho, peso baixo, para não perder o acórdão sem ementa estruturada)` : "") +
    (filtrosCita ? ` · ${filtrosCita}` : "") + "\n" +
    `expressão${exato ? "" : " (com variação singular/plural; `exato=true` desliga)"}: ${q.length < 700 ? q : q.slice(0, 700) + "…"}\n`];
  if (pagina === 1 && total >= 5) out.push(panorama(con, sql, args, porBm25, total, new Set(q.match(/[a-z]{5,}/g) || [])));
  for (const r of rows) {
    const emTxt = r.ementa, en = norm(emTxt);
    const pos = termos.map((t) => en.indexOf(t.replace(/[$*]+$/, ""))).filter((x) => x >= 0);
    const p = pos.length ? Math.min(...pos) : 0;
    const trecho = emTxt.length <= 900 ? emTxt : (p > 200 ? "…" : "") + emTxt.slice(Math.max(0, p - 200), Math.max(0, p - 200) + 900) + "…";
    const link = `${URL_TEOR}?tmp.numprocesso=${r.processo}&tmp.numacordao=${r.acordao}`;
    let rec = lerRecibo(r.acordao) ? " · recibo do inteiro teor já em disco" : "";
    const rep = todos(con, "SELECT edicao FROM republicacoes WHERE acordao=?", r.acordao).map((x) => x.edicao);
    if (rep.length) rec += `\n  ⚠ REPUBLICADO na(s) edição(ões) [${rep.join(", ")}] — pode haver retificação de ementa: confira no inteiro teor`;
    const cita_ = ancoras(emTxt);
    const outros = outrosAcordaosDoProcesso(con, r.processo, r.acordao);
    const aut = escalar(con, "SELECT COUNT(DISTINCT origem) n FROM citacoes WHERE tipo='tjse' AND ref=?", r.processo);
    rec += cita_.length ? "\n  Cita: " + cita_.join(" · ") : "";
    rec += aut ? `\n  ⬆ CITADO por ${aut} acórdão(s) deste índice — autoridade interna: julgado que a própria câmara reusa` : "";
    rec += outros ? "\n  " + outros : "";
    const cobTxt = usaCobertura ? ` · casa ${r.cobertura}/${nUni} termos` : "";
    out.push(`■ Acórdão ${r.acordao} · processo ${r.processo} · ${r.recurso || r.classe}${cobTxt}\n` +
      `  ${r.orgao} (seção do Boletim; o órgão citável é o do FECHO) · ${r.relator_rotulo || "Relator"}: ${r.relator}\n` +
      `  Boletim ed. ${r.edicao}, publicado em ${br(r.ed_data)} (data do julgamento só no inteiro teor)${rec}\n` +
      `  Ementa (Boletim, caixa alta): ${trecho}\n  Inteiro teor: ${link}\n  verificação: só ementa/índice\n`);
  }
  if (usaCobertura && unidades.length <= 8) {
    const plenos = escalar(con, "SELECT COUNT(*) n FROM (" + unidades.map(() => `SELECT acordao FROM ${tabFts} WHERE ${tabFts} MATCH ?`).join(" INTERSECT ") + ")", ...uniArgs);
    out.splice(1, 0, `⚠ ${total} acórdão(s) casam AO MENOS UM dos ${nUni} termos; ${plenos} casam TODOS. O número grande é o alcance da busca, não o tamanho da corrente: para contar julgados sobre a tese use \`grupos\`, que exige um termo de cada.\n`);
  }
  out.push("Próximo passo: `obter_inteiro_teor_tjse(numero_acordao=…)` no que interessar (lê o voto, fixa órgão e data pelo fecho); antes de aspas, `verificar_citacao_tjse`.");
  return out.join("\n") + rodape;
}

/** repr() de uma string do Python (aspas simples, como em `f"{x!r}"`). */
function pyRepr1(s) {
  s = String(s);
  const q = s.includes("'") && !s.includes('"') ? '"' : "'";
  return q + s.replaceAll("\\", "\\\\").replaceAll("\n", "\\n").replaceAll(q, "\\" + q) + q;
}

// ---------------------------------------------------------------------------- grafo de citações
export function mapaCitacoes(referencia = null, limite = 15) {
  const con = db();
  const n = escalar(con, "SELECT COUNT(*) n FROM citacoes");
  if (!n) return "O grafo de citações está vazio — o índice precisa ser (re)sincronizado para extrair o campo 'Jurisprudência relevante citada' das ementas. Rode `diagnostico_tjse`.";
  limite = Math.max(3, Math.min(Math.trunc(limite || 15), 50));
  if (!referencia) {
    const qual = todos(con, `SELECT MAX(ref) ref, COUNT(DISTINCT origem) k FROM citacoes WHERE tipo='qualificado'
      GROUP BY CASE WHEN INSTR(ref,'/')>0 THEN SUBSTR(ref,1,INSTR(ref,'/')-1) ELSE ref END ORDER BY k DESC LIMIT ?`, limite);
    const lid = todos(con, "SELECT ref, COUNT(DISTINCT origem) k FROM citacoes WHERE tipo='tjse' GROUP BY ref ORDER BY k DESC LIMIT ?", limite);
    const dentro = new Set(todos(con, "SELECT processo FROM acordaos").map((r) => r.processo));
    const linhas = [`Grafo de citações do índice (${n} arestas, extraídas das ementas — zero rede).`, "\nPrecedentes QUALIFICADOS mais citados (súmula, tema, IRDR, IAC):"];
    linhas.push(...(qual.length ? qual.map((r) => `  ${r.ref}: ${r.k} acórdão(s)`) : ["  —"]));
    linhas.push("\nAcórdãos do próprio TJSE mais citados pelos pares (candidatos a julgado-líder):");
    for (const r of lid) linhas.push(`  processo ${r.ref}: citado por ${r.k} — ${dentro.has(r.ref) ? "no índice" : "FORA do índice (anterior ao período sincronizado)"}`);
    const fora = escalar(con, "SELECT COUNT(DISTINCT ref) n FROM citacoes WHERE tipo='tjse' AND ref NOT IN (SELECT processo FROM acordaos)");
    linhas.push(`\n${fora} processo(s) do TJSE são citados pelos acórdãos do índice mas estão FORA dele (julgados anteriores ao período sincronizado): o grafo enxerga além da janela, mas para LER cada um é preciso o nº do ACÓRDÃO (ano + sequencial), que a ementa citante não traz — busque-o na base que você assinar, ou no portal oficial, e confira aqui com \`obter_inteiro_teor_tjse\`.`);
    linhas.push("Para ver quem cita um deles: `mapa_de_citacoes_tjse(referencia='Tema 1061')` ou o nº do processo.");
    return linhas.join("\n");
  }
  const ref = refCitada(referencia);
  if (!ref) return `Não reconheci ${pyRepr1(referencia)}. Use 'Tema 1061', 'Súmula 479/STJ', 'IRDR 15', 'SV 47' ou o nº de PROCESSO do TJSE (12 dígitos).`;
  const b = baseRef(ref[1]);
  const tot = escalar(con, "SELECT COUNT(DISTINCT origem) n FROM citacoes WHERE tipo=? AND (ref=? OR ref LIKE ?)", ref[0], b, b + "/%");
  if (!tot) return `Nenhum acórdão do índice cita ${ref[1]} — no período coberto (${cobertura(con)}). Isso NÃO significa que o TJSE não tenha aplicado: o grafo só vê o campo 'Jurisprudência relevante citada', que ~1/3 das ementas preenche.`;
  const rows = todos(con, `SELECT DISTINCT a.acordao, a.processo, a.orgao, a.relator, a.classe, SUBSTR(a.ementa,1,220) e, a.edicao
    FROM citacoes c JOIN acordaos a ON a.acordao=c.origem WHERE c.tipo=? AND (c.ref=? OR c.ref LIKE ?) ORDER BY a.edicao DESC LIMIT ?`, ref[0], b, b + "/%", limite);
  const out = [`${tot} acórdão(s) do índice citam ${ref[1]} (mostrando ${rows.length}):`];
  for (const r of rows)
    out.push(`■ Acórdão ${r.acordao} · processo ${r.processo} · ${r.classe}\n  ${r.orgao} · ${r.relator}\n  ${r.e.replace(/\s+/g, " ")}…\n  Inteiro teor: ${URL_TEOR}?tmp.numprocesso=${r.processo}&tmp.numacordao=${r.acordao}`);
  out.push("\nO campo 'Jurisprudência relevante citada' existe em ~1/3 das ementas: quem não o preenche não aparece aqui, ainda que aplique o mesmo precedente. Para esses, use `buscar_jurisprudencia_tjse`.");
  return out.join("\n");
}
