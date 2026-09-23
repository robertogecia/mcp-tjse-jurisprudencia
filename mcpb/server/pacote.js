// Pacote de HTML bruto do Boletim (asset do release): baixa, confere o hash, extrai só o que se espera e devolve.
// Existe para o usuário leigo: no `.mcpb` ninguém vai abrir um Terminal para extrair um .tar.gz. O endereço é FIXO
// no código; o hash vem de SHA256SUMS.txt do MESMO release (conferência de integridade do download, não de autoria:
// quem controla o release controla os dois). O conteúdo só é lido como texto para o parser, nunca executado.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { dirBase, dirSecoes, PesquisaNaoRealizada, REPO_GITHUB } from "./config.js";

export const ARQUIVO_PACOTE = "base-secoes-tjse.tar.gz";
export const URL_PACOTE = `https://github.com/${REPO_GITHUB}/releases/latest/download/${ARQUIVO_PACOTE}`;
export const URL_SOMAS = `https://github.com/${REPO_GITHUB}/releases/latest/download/SHA256SUMS.txt`;
const NOME_VALIDO = /^(?:\.\/)?secoes\/(\d{1,6})-(\d{1,3})(?:\.p\d{1,3})?\.html\.gz$/;
const MAX_ENTRADA = 64 * 1024 * 1024, MAX_TOTAL = 600 * 1024 * 1024;

/** Leitor de tar mínimo (ustar + cabeçalhos PAX/GNU de nome longo) sobre um fluxo já descompactado. */
export async function* lerTar(fluxo) {
  let buf = Buffer.alloc(0), nomeLongo = null;
  const precisa = async (n, it) => { while (buf.length < n) { const r = await it.next(); if (r.done) return false; buf = Buffer.concat([buf, r.value]); } return true; };
  const it = fluxo[Symbol.asyncIterator]();
  for (;;) {
    if (!(await precisa(512, it))) return;
    const cab = buf.subarray(0, 512);
    if (cab.every((b) => b === 0)) { while (!(await it.next()).done); return; }   // drena o resto: todo byte baixado passa pelo hash
    const txt = (a, b) => cab.subarray(a, b).toString("utf8").replace(/\0.*$/s, "");
    let nome = txt(0, 100);
    const prefixo = txt(345, 500);
    if (prefixo) nome = prefixo + "/" + nome;
    const tamanho = parseInt(txt(124, 136).trim() || "0", 8);
    const tipo = String.fromCharCode(cab[156] || 48);
    const total = 512 + Math.ceil(tamanho / 512) * 512;
    if (tamanho > MAX_ENTRADA) throw new PesquisaNaoRealizada(`pacote com entrada acima do limite (${tamanho} bytes): recusado.`);
    if (!(await precisa(total, it))) throw new PesquisaNaoRealizada("pacote truncado (tar incompleto).");
    const dados = buf.subarray(512, 512 + tamanho);
    buf = buf.subarray(total);
    if (tipo === "L") { nomeLongo = dados.toString("utf8").replace(/\0+$/, ""); continue; }
    if (tipo === "x") {   // PAX: "<len> path=<nome>\n"
      const m = /\d+ path=([^\n]+)\n/.exec(dados.toString("utf8"));
      if (m) nomeLongo = m[1];
      continue;
    }
    yield { nome: nomeLongo ?? nome, tipo, dados };
    nomeLongo = null;
  }
}

async function obterTexto(url, fetchImpl, timeoutMs = 20_000) {
  const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetchImpl(url, { signal: ctrl.signal, redirect: "follow", headers: { "User-Agent": "mcp-tjse-jurisprudencia" } });
    if (!r.ok) throw new PesquisaNaoRealizada(`o GitHub respondeu HTTP ${r.status} para ${url.split("/").pop()}.`);
    return await r.text();
  } finally { clearTimeout(t); }
}

/** Estado do download em andamento (um por processo): a chamada da ferramenta espera um pouco e devolve o progresso. */
export const estado = { rodando: false, baixado: 0, total: 0, erro: null, concluido: null, promessa: null };

export function baixarEExtrair({ fetchImpl = globalThis.fetch } = {}) {
  if (estado.rodando && estado.promessa) return estado.promessa;
  Object.assign(estado, { rodando: true, baixado: 0, total: 0, erro: null, concluido: null });
  estado.promessa = (async () => {
    const tmp = path.join(dirBase(), ".pacote-tmp");
    try {
      const somas = await obterTexto(URL_SOMAS, fetchImpl);
      const esperado = somas.split(/\r?\n/).map((l) => l.trim().split(/\s+/)).find((p) => p[1]?.replace(/^\*/, "") === ARQUIVO_PACOTE)?.[0]?.toLowerCase();
      if (!/^[0-9a-f]{64}$/.test(esperado || "")) throw new PesquisaNaoRealizada(`SHA256SUMS.txt do release não traz o hash de ${ARQUIVO_PACOTE}.`);
      fs.rmSync(tmp, { recursive: true, force: true });
      fs.mkdirSync(tmp, { recursive: true, mode: 0o700 });
      const r = await fetchImpl(URL_PACOTE, { redirect: "follow", headers: { "User-Agent": "mcp-tjse-jurisprudencia" } });
      if (!r.ok || !r.body) throw new PesquisaNaoRealizada(`o GitHub respondeu HTTP ${r.status} para o pacote.`);
      estado.total = Number(r.headers.get("content-length") || 0);
      const hash = crypto.createHash("sha256");
      const gun = zlib.createGunzip();
      let total = 0, arquivos = 0;
      const consumidor = (async () => {
        for await (const e of lerTar(gun)) {
          if (e.tipo !== "0" && e.tipo !== "\0") continue;   // só arquivo comum; diretórios e links são ignorados
          const m = NOME_VALIDO.exec(e.nome);
          if (!m) continue;                                  // nome fora do padrão esperado: ignorado (nunca se cria caminho vindo do pacote)
          total += e.dados.length;
          if (total > MAX_TOTAL) throw new PesquisaNaoRealizada("pacote acima do limite total de tamanho: recusado.");
          fs.writeFileSync(path.join(tmp, path.basename(e.nome)), e.dados, { mode: 0o600 });
          arquivos++;
        }
      })();
      const produtor = (async () => {
        for await (const chunk of r.body) {
          hash.update(chunk); estado.baixado += chunk.length;
          if (!gun.write(chunk)) await new Promise((res) => gun.once("drain", res));
        }
        gun.end();
      })();
      try { await Promise.all([produtor, consumidor]); } catch (e) { gun.destroy(); try { await r.body.cancel(); } catch { /* já encerrado */ } throw e; }
      if (hash.digest("hex") !== esperado) throw new PesquisaNaoRealizada("o hash do pacote baixado NÃO confere com SHA256SUMS.txt (download corrompido ou alterado): nada foi instalado.");
      if (!arquivos) throw new PesquisaNaoRealizada("o pacote não continha nenhuma seção reconhecível: nada foi instalado.");
      fs.mkdirSync(dirSecoes(), { recursive: true, mode: 0o700 });
      for (const f of fs.readdirSync(tmp)) fs.renameSync(path.join(tmp, f), path.join(dirSecoes(), f));
      estado.concluido = { arquivos, bytes: total };
    } catch (e) {
      estado.erro = e instanceof PesquisaNaoRealizada ? e.message
        : (e.code === "Z_BUF_ERROR" || /unexpected end of file|terminated|fetch failed/i.test(String(e.message)))
          ? "o download foi interrompido antes do fim (conexão caiu ou o arquivo veio incompleto): nada foi instalado — tente de novo."
          : `${e.name}: ${e.message}`;
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
      estado.rodando = false;
    }
  })();
  return estado.promessa;
}
