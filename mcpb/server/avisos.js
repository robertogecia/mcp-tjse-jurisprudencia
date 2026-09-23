// Crédito de autoria, aviso de versão nova e link de relato — porte de `servidor_tjse.py` (seção "crédito e aviso de versão").
// A consulta a `releases/latest` roda em SEGUNDO PLANO desde a subida do servidor: nenhuma resposta é atrasada, as tools
// só leem o resultado se ele já chegou. O endereço mostrado é FIXO, nunca vem do corpo da resposta da API. Sem rede, com
// erro, com repositório sem release (404) ou em mais de 2 s: silêncio. Só o GitHub vê o IP; nada da pesquisa ou do caso sai.
// Desligar: TJSE_MCP_SEM_AVISO_ATUALIZACAO=1.
import os from "node:os";
import { REPO_GITHUB, VERSAO } from "./config.js";

export const RELEASES_API = `https://api.github.com/repos/${REPO_GITHUB}/releases/latest`;
export const RELEASES_PAGINA = `https://github.com/${REPO_GITHUB}/releases/latest`;
export const ISSUES_NOVA = `https://github.com/${REPO_GITHUB}/issues/new`;
export const CREDITO = "_Esta extensão foi desenvolvida por @robertogrecia (Roberto Grécia Bessa, OAB/RO 7865-A). Obrigado por usar!_";
const RE_TAG = /^v?(\d{1,4})\.(\d{1,4})\.(\d{1,4})$/;

let creditoDado = false, avisoDado = false, versaoNova = null;

/** true só se `outra` for estritamente maior que `atual`. Formato estranho é false: aviso errado é pior que aviso nenhum. */
export function versaoMaisNova(atual, outra) {
  const a = RE_TAG.exec(String(atual ?? "").trim()), b = RE_TAG.exec(String(outra ?? "").trim());
  if (!a || !b) return false;
  for (let i = 1; i <= 3; i++) { const x = Number(a[i]), y = Number(b[i]); if (y !== x) return y > x; }
  return false;
}

/** Nunca lança: qualquer falha é silêncio. */
export async function checarVersao({ fetchImpl = globalThis.fetch, timeoutMs = 2000, env = process.env } = {}) {
  try {
    if (env.TJSE_MCP_SEM_AVISO_ATUALIZACAO === "1" || typeof fetchImpl !== "function") return null;
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const r = await fetchImpl(RELEASES_API, { signal: ctrl.signal, headers: { Accept: "application/vnd.github+json", "User-Agent": "mcp-tjse-jurisprudencia" } });
      if (!r.ok) return null;
      const tag = String(((await r.json()) ?? {}).tag_name ?? "").trim();
      return versaoMaisNova(VERSAO, tag) ? tag.replace(/^v/, "") : null;
    } finally { clearTimeout(t); }
  } catch { return null; }
}

export function iniciarChecagemVersao(opcoes) {
  checarVersao(opcoes).then((v) => { if (v) versaoNova = v; }, () => {});
}

export const avisoAtualizacao = (nova) => `_Há uma versão mais nova desta extensão (v${nova}; a instalada é a v${VERSAO}): ${RELEASES_PAGINA}_`;

/** Crédito (uma vez por processo) e, se houver, aviso de versão (uma vez). Nunca espera rede. */
export function comAvisos(texto) {
  const partes = [texto];
  if (!creditoDado) { creditoDado = true; partes.push(CREDITO); }
  if (versaoNova && !avisoDado) { avisoDado = true; partes.push(avisoAtualizacao(versaoNova)); }
  return partes.join("\n\n");
}
export function _resetAvisosParaTeste() { creditoDado = avisoDado = false; versaoNova = null; }
export function _definirVersaoNovaParaTeste(v) { versaoNova = v; }

/** urllib.parse.quote (safe="/"): o que o Python usa para montar a URL da issue. */
export const quotePy = (s) => encodeURIComponent(s).replace(/%2F/g, "/").replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());

/** URL de nova issue no GitHub, JÁ PREENCHIDA só com dado técnico — NUNCA com o texto da busca, número de acórdão/processo
 * ou nome de parte (issues são públicas). Só para ERRO DE VERDADE (bug), nunca para PESQUISA NÃO REALIZADA (isso é o
 * portal/disjuntor, não defeito da ferramenta). */
export function linkRelato(tipo) {
  const titulo = `Erro ${tipo} na v${VERSAO}`;
  const corpo = "**Relato gerado pela extensão** (revise antes de enviar; não inclua nome de parte, número de acórdão/processo nem o texto da sua busca — issues são públicas)\n\n" +
    `- Versão: ${VERSAO}\n- Sistema: ${os.type()} ${os.release()}\n- Tipo do erro: ${tipo}\n` + "\n**O que eu estava fazendo:** \n\n**Desde quando acontece?** \n";
  return `${ISSUES_NOVA}?title=${quotePy(titulo)}&body=${quotePy(corpo)}`;
}
