// Índice local (SQLite FTS5 via node:sqlite) — porte de `servidor_tjse.py` (seção "Índice local").
// O esquema é IDÊNTICO ao do Python: um banco criado por um abre no outro.
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { AmbienteIncompativel, arqDb, dirBase, dirSecoes } from "./config.js";
import { agoraIso, br, dataPorExtenso, desescapaHtml } from "./texto.js";
import {
  PARSER_VERSAO, NOME_POR_CODIGO, CAMPOS_EMENTA, parseSecao, camposDaEmenta, citacoesDaEmenta, proximaPosicao,
} from "./parse.js";

const ESQUEMA = `
CREATE TABLE IF NOT EXISTS edicoes(edicao INTEGER PRIMARY KEY, rotulo TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS secoes(edicao INTEGER, codigo INTEGER, nome TEXT, itens INTEGER, baixada_em TEXT,
                                  PRIMARY KEY(edicao, codigo));
CREATE TABLE IF NOT EXISTS acordaos(acordao TEXT PRIMARY KEY, processo TEXT, classe TEXT, recurso TEXT,
                                    relator TEXT, relator_rotulo TEXT, orgao TEXT, edicao INTEGER, ementa TEXT);
CREATE TABLE IF NOT EXISTS meta(chave TEXT PRIMARY KEY, valor TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_vocab USING fts5vocab(fts, 'row');
CREATE TABLE IF NOT EXISTS campos(acordao TEXT PRIMARY KEY, cabecalho TEXT, caso TEXT, questao TEXT, razoes TEXT,
                                  dispositivo TEXT, tese TEXT, legislacao TEXT, juris_citada TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_campos USING fts5(acordao UNINDEXED, cabecalho, caso, questao, razoes,
                                  dispositivo, tese, tokenize="unicode61 remove_diacritics 2");
CREATE TABLE IF NOT EXISTS citacoes(origem TEXT, tipo TEXT, ref TEXT, PRIMARY KEY(origem, tipo, ref));
CREATE INDEX IF NOT EXISTS ix_cit_ref ON citacoes(tipo, ref);
CREATE TABLE IF NOT EXISTS republicacoes(acordao TEXT, edicao INTEGER, ementa TEXT, PRIMARY KEY(acordao, edicao));
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(acordao UNINDEXED, ementa, classe, relator,
                                                  tokenize="unicode61 remove_diacritics 2");
`;

export function tx(con, fn) {
  con.exec("BEGIN");
  try { const r = fn(); con.exec("COMMIT"); return r; } catch (e) { try { con.exec("ROLLBACK"); } catch { /* já revertida */ } throw e; }
}

// `node:sqlite` é carregado sem lançar: se o Claude Desktop for antigo demais para tê-lo, o servidor sobe mesmo assim e cada
// ferramenta explica o que fazer (um import estático derrubaria tudo em silêncio, e o usuário não veria nem uma mensagem).
const DatabaseSync = process.getBuiltinModule?.("node:sqlite")?.DatabaseSync;
const SEM_SQLITE = "este ambiente não tem o SQLite embutido no Node (`node:sqlite`, Node 22.13 ou mais novo), que o índice local exige. " +
  "Atualize o Claude Desktop para a versão mais recente e abra-o de novo. Isto NÃO é 'não localizado'.";

let conCache = null, conCaminho = null;
/** Conexão única por processo (o Python abre uma por chamada; o efeito é o mesmo). Cria o esquema e reindexa se o parser mudou. */
export function db() {
  const caminho = arqDb();
  if (conCache && conCaminho === caminho) return conCache;
  if (!DatabaseSync) throw new AmbienteIncompativel(SEM_SQLITE);
  if (conCache) { try { conCache.close(); } catch { /* já fechada */ } conCache = null; }
  fs.mkdirSync(dirBase(), { recursive: true, mode: 0o700 });
  const con = new DatabaseSync(caminho);
  try {
    con.exec("PRAGMA busy_timeout = 5000");
    con.exec(ESQUEMA);
    reindexarSeParserMudou(con);
  } catch (e) {
    try { con.close(); } catch { /* conexão aberta com transação pendente = "database is locked" em tudo depois */ }
    if (/no such module: fts5/i.test(String(e.message)))
      throw new AmbienteIncompativel("o SQLite deste ambiente não tem a extensão FTS5, que a busca exige. Atualize o Claude Desktop para a versão mais recente. Isto NÃO é 'não localizado'.");
    throw e;
  }
  conCache = con; conCaminho = caminho;
  return con;
}
export function fecharDb() { if (conCache) { try { conCache.close(); } catch { /* */ } conCache = null; conCaminho = null; } }

export const um = (con, sql, ...a) => con.prepare(sql).get(...a);
export const todos = (con, sql, ...a) => con.prepare(sql).all(...a);
export const escalar = (con, sql, ...a) => { const r = con.prepare(sql).get(...a); return r ? Object.values(r)[0] : undefined; };

// ---------------------------------------------------------------------------- HTML bruto em disco
const arqSecao = (edicao, codigo, pagina = 1) =>
  path.join(dirSecoes(), `${Number(edicao)}-${Number(codigo)}${pagina === 1 ? "" : `.p${Number(pagina)}`}.html.gz`);

export function lerBruto(edicao, codigo, pagina = 1) {
  try { return zlib.gunzipSync(fs.readFileSync(arqSecao(edicao, codigo, pagina))).toString("utf8"); } catch { return null; }
}

/** (páginas guardadas, completa?) — completa = a última página guardada não tem 'Próximo'. */
export function paginasEmDisco(edicao, codigo) {
  const pags = [];
  for (let h; (h = lerBruto(edicao, codigo, pags.length + 1)) !== null;) {
    pags.push(h);
    if (proximaPosicao(h) === null) return [pags, true];
  }
  return [pags, false];
}

export function guardarBruto(edicao, codigo, h, pagina = 1) {
  fs.mkdirSync(dirSecoes(), { recursive: true, mode: 0o700 });
  fs.writeFileSync(arqSecao(edicao, codigo, pagina), zlib.gzipSync(Buffer.from(h, "utf8")), { mode: 0o600 });
}

// ---------------------------------------------------------------------------- indexação
function apagarSecao(con, edicao, nome) {
  const alvo = "SELECT acordao FROM acordaos WHERE edicao=? AND orgao=?";
  for (const [t, col] of [["fts", "acordao"], ["campos", "acordao"], ["fts_campos", "acordao"], ["citacoes", "origem"]])
    con.prepare(`DELETE FROM ${t} WHERE ${col} IN (${alvo})`).run(edicao, nome);
  con.prepare("DELETE FROM acordaos WHERE edicao=? AND orgao=?").run(edicao, nome);
}

function reindexarSeParserMudou(con) {
  const v = um(con, "SELECT valor FROM meta WHERE chave='parser_versao'");
  if (v && Number(v.valor) === PARSER_VERSAO) return;
  tx(con, () => {
    for (const r of todos(con, "SELECT edicao, codigo, nome FROM secoes")) {
      apagarSecao(con, r.edicao, r.nome);
      const [pags, completa] = paginasEmDisco(r.edicao, r.codigo);
      const itens = parseSecao(pags.join("\n"));   // juntas: a classe aberta na página 1 continua na 2
      if (pags.length && completa) indexarSecao(con, r.edicao, r.codigo, r.nome, itens, false);
      if (!pags.length || !completa)   // sem bruto, ou faltam páginas: volta para a fila da sincronização
        con.prepare("DELETE FROM secoes WHERE edicao=? AND codigo=?").run(r.edicao, r.codigo);
    }
    con.prepare("INSERT OR REPLACE INTO meta VALUES('parser_versao', ?)").run(String(PARSER_VERSAO));
  });
}

export function indexarSecao(con, edicao, codigo, nome, itens, commit = true) {
  const corpo = () => {
    let novos = 0;
    const selJa = con.prepare("SELECT edicao FROM acordaos WHERE acordao=?");
    const insRep = con.prepare("INSERT OR REPLACE INTO republicacoes VALUES(?,?,?)");
    const dels = ["fts", "acordaos", "campos", "fts_campos", "citacoes"].map((t) =>
      con.prepare(`DELETE FROM ${t} WHERE ${t === "citacoes" ? "origem" : "acordao"}=?`));
    const insAc = con.prepare("INSERT INTO acordaos VALUES(?,?,?,?,?,?,?,?,?)");
    const insFts = con.prepare("INSERT INTO fts(acordao, ementa, classe, relator) VALUES(?,?,?,?)");
    const insCampos = con.prepare("INSERT OR REPLACE INTO campos VALUES(?,?,?,?,?,?,?,?,?)");
    const insFtsC = con.prepare("INSERT INTO fts_campos(acordao, cabecalho, caso, questao, razoes, dispositivo, tese) VALUES(?,?,?,?,?,?,?)");
    const insCit = con.prepare("INSERT OR IGNORE INTO citacoes VALUES(?,?,?)");
    for (const it of itens) {
      const ja = selJa.get(it.acordao);
      if (ja && ja.edicao !== edicao) {
        // mesmo acórdão em outra edição: pode ser RETIFICAÇÃO. Fica a primeira no índice, a outra é guardada e avisada.
        insRep.run(it.acordao, edicao, it.ementa);
        continue;
      }
      if (ja) for (const d of dels) d.run(it.acordao); else novos++;
      insAc.run(it.acordao, it.processo, it.classe, it.recurso, it.relator, it.relator_rotulo, nome, edicao, it.ementa);
      insFts.run(it.acordao, it.ementa, it.classe, it.relator);
      const cps = camposDaEmenta(it.ementa);
      insCampos.run(it.acordao, ...CAMPOS_EMENTA.map((k) => cps[k]));
      insFtsC.run(it.acordao, cps.cabecalho, cps.caso, cps.questao, cps.razoes, cps.dispositivo, cps.tese);
      for (const [tipo, ref] of citacoesDaEmenta(cps, it.ementa)) insCit.run(it.acordao, tipo, ref);
    }
    con.prepare("INSERT OR REPLACE INTO secoes VALUES(?,?,?,?,?)").run(edicao, codigo, nome, itens.length, agoraIso());
    return novos;
  };
  return commit ? tx(con, corpo) : corpo();
}

const RE_ARQ_SECAO = /^(\d+)-(\d+)(?:\.p\d+)?\.html\.gz$/;
const RE_ROTULO_BOLETIM = /boletim\s*n\.?\s*(\d+)\s+de\s+([^<\n]{3,40}\d{4})/i;

/** Reconstrói `edicoes`, `secoes` e o índice inteiro só a partir de `base/secoes/*.html.gz` — zero rede, mesmo com as
 * tabelas vazias. Código de seção sem nome conhecido é ignorado e listado à parte — melhor buraco declarado que nome inventado. */
export function importarSecoesDoBruto(con, { prazoMs = null } = {}) {
  if (!fs.existsSync(dirSecoes()) || !fs.statSync(dirSecoes()).isDirectory()) return `Nada em \`${dirSecoes()}\` para importar.`;
  const pares = new Map();
  for (const n of fs.readdirSync(dirSecoes())) {
    const m = RE_ARQ_SECAO.exec(n);
    if (m) pares.set(`${Number(m[1])}|${Number(m[2])}`, [Number(m[1]), Number(m[2])]);
  }
  const lista = [...pares.values()].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const ignorados = [...new Set(lista.map((p) => p[1]).filter((c) => !(c in NOME_POR_CODIGO)))].sort((a, b) => a - b);
  const linhas = [];
  let novosAcordaos = 0, jaIndexadas = 0, restantes = 0;
  for (const [edicao, codigo] of lista) {
    if (!(codigo in NOME_POR_CODIGO)) continue;
    if (um(con, "SELECT 1 x FROM secoes WHERE edicao=? AND codigo=?", edicao, codigo)) { jaIndexadas++; continue; }   // retomável: o que já entrou não se refaz
    if (prazoMs !== null && Date.now() > prazoMs) { restantes++; continue; }   // orçamento de tempo da chamada esgotado
    const [pags, completa] = paginasEmDisco(edicao, codigo);
    if (!pags.length) continue;
    if (!completa) linhas.push(`  edição ${edicao} · seção ${codigo}: só ${pags.length} página(s) em disco, SEM a marca de fim — importada mesmo assim, mas pode faltar conteúdo.`);
    const rot = RE_ROTULO_BOLETIM.exec(pags[0]);
    const dataEd = rot ? dataPorExtenso(desescapaHtml(rot[2])) : null;
    if (rot) con.prepare("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)").run(edicao, rot[1], dataEd);
    else if (!um(con, "SELECT 1 x FROM edicoes WHERE edicao=?", edicao)) {
      con.prepare("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)").run(edicao, String(edicao), null);
      linhas.push(`  ⚠ edição ${edicao}: rótulo/data não reconhecidos na página — gravada só com o número.`);
    }
    const nome = NOME_POR_CODIGO[codigo];
    const itens = parseSecao(pags.join("\n"));
    const novos = indexarSecao(con, edicao, codigo, nome, itens);
    novosAcordaos += novos;
    linhas.push(`  edição ${edicao} · ${nome}: ${itens.length} acórdãos (${novos} novos)`);
  }
  con.prepare("INSERT OR REPLACE INTO meta VALUES('parser_versao', ?)").run(String(PARSER_VERSAO));
  if (!linhas.length && !jaIndexadas && !restantes) return `Nenhuma seção reconhecível em \`${dirSecoes()}\` (esperado: \`<edição>-<código>.html.gz\`).`;
  const avisoIgnorados = ignorados.length
    ? `\n⚠ código(s) de seção sem nome conhecido, ignorado(s): [${ignorados.join(", ")}] — avise o mantenedor do projeto, o Boletim pode ter uma seção nova.` : "";
  const resto = restantes ? `\n⏳ Faltam ${restantes} seção(ões): o tempo desta chamada acabou. Chame de novo — o que já entrou não se refaz.` : "";
  const ja = jaIndexadas ? `\n(${jaIndexadas} seção(ões) já estavam no índice e foram mantidas.)` : "";
  return `Importação do HTML bruto (zero rede) — ${novosAcordaos} acórdão(s) novo(s):\n${linhas.join("\n")}${ja}${resto}${avisoIgnorados}\nÍndice: ${cobertura(con)}`;
}

// ---------------------------------------------------------------------------- cobertura
export function avisoIncompletas(con) {
  const inc = todos(con, `SELECT e.edicao FROM edicoes e WHERE e.edicao BETWEEN (SELECT MIN(edicao) FROM secoes) AND (SELECT MAX(edicao) FROM secoes)
    AND (SELECT COUNT(*) FROM secoes s WHERE s.edicao=e.edicao) < 5 ORDER BY 1`).map((r) => `ed. ${r.edicao}`);
  return inc.length
    ? `. ⚠ EDIÇÕES INCOMPLETAS no intervalo (${inc.join(", ")}): há seções faltando ou só parcialmente baixadas — zero resultado vale ainda menos; rode \`sincronizar_boletim_tjse\``
    : "";
}

export function cobertura(con) {
  const r = um(con, `SELECT COUNT(DISTINCT s.edicao) n, MIN(e.data) a, MAX(e.data) b FROM secoes s JOIN edicoes e USING(edicao)`);
  const tot = escalar(con, "SELECT COUNT(*) FROM acordaos");
  if (!r.n) return "índice local VAZIO — peça `importar_pacote_tjse` (baixa o pacote pronto, sem tocar o portal do tribunal) ou `sincronizar_boletim_tjse` (baixa direto do portal, mais lento) antes de buscar";
  const nulas = escalar(con, "SELECT COUNT(*) FROM edicoes e WHERE data IS NULL AND EXISTS(SELECT 1 FROM secoes s WHERE s.edicao=e.edicao)");
  return `${tot} acórdãos de ${r.n} edição(ões) do Boletim, publicadas de ${br(r.a)} a ${br(r.b)} ` +
    (nulas ? `[+${nulas} edição(ões) com data não reconhecida, fora deste intervalo] ` : "") +
    "(cada edição traz os julgados do mês anterior)" + avisoIncompletas(con);
}

export function gravaMeta(con, chave, valor) {
  con.prepare("INSERT OR REPLACE INTO meta VALUES(?,?)").run(chave, valor);
}
