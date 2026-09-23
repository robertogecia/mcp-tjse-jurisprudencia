// Disjuntor (estado em disco, compartilhado entre processos) e cliente HTTP — porte de `servidor_tjse.py`.
// O Python usa flock; Node não tem, então a exclusão mútua é um diretório criado de forma atômica (mkdir),
// com quebra de trava abandonada. Sem a trava não há requisição (fail-closed), como no Python.
import fs from "node:fs";
import path from "node:path";
import {
  arqEstado, dirDados, ESCADA, JANELA_S, DIA_MAX, PAUSA_ILEGIVEL_S, PAUSA_BLOQUEIO_S, PAUSA_DESAFIO_S, PAUSA_ERRO_S,
  SUCESSOS_PARA_RELAXAR, MARCAS_DESAFIO, userAgent, PesquisaNaoRealizada,
} from "./config.js";
import { agoraIso, quoteLatin1 } from "./texto.js";

let pausaMemoria = 0.0;   // vale mesmo se o disco falhar
const agora = () => Date.now() / 1000;
const dormirSync = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
export const dormir = (s) => new Promise((r) => setTimeout(r, s * 1000));

const TRAVA_ESPERA_MS = 5000;
const TRAVA_ABANDONADA_MS = 15000;

/** Executa fn(travou) segurando a trava entre processos. travou=false: não conseguiu (pasta sem permissão, disputa longa). */
export function comTrava(fn) {
  const trava = arqEstado() + ".lockdir";
  let travou = false;
  try {
    fs.mkdirSync(dirDados(), { recursive: true });
    const fim = Date.now() + TRAVA_ESPERA_MS;
    while (Date.now() < fim) {
      try { fs.mkdirSync(trava); travou = true; break; } catch (e) {
        if (e.code !== "EEXIST") break;
        try { if (Date.now() - fs.statSync(trava).mtimeMs > TRAVA_ABANDONADA_MS) { fs.rmdirSync(trava); continue; } } catch { /* outro processo liberou */ }
        dormirSync(25);
      }
    }
  } catch { travou = false; }
  try { return fn(travou); } finally {
    if (travou) { try { fs.rmdirSync(trava); } catch { /* já liberada */ } }
  }
}

const estadoVazio = () => ({ requisicoes: [], pausa_ate: 0, motivo: "", incidentes: [], nivel: 0, sucessos: 0 });

export function lerEstado() {
  if (!fs.existsSync(arqEstado())) return estadoVazio();
  try {
    const e = JSON.parse(fs.readFileSync(arqEstado(), "utf8"));
    const t = agora();
    const num = (v) => { const n = Number(v); if (!Number.isFinite(n)) throw new Error("tipo"); return n; };
    return {  // tipos saneados: JSON válido com tipo errado também é "ilegível"
      requisicoes: e.requisicoes.map(num).filter((x) => x >= 0 && t - x >= 0 && t - x < 86400),
      pausa_ate: num(e.pausa_ate || 0), motivo: String(e.motivo || ""),
      incidentes: (e.incidentes || []).filter((i) => i && typeof i === "object" && !Array.isArray(i)).slice(-30),
      nivel: Math.min(Math.max(parseInt(e.nivel || 0, 10) || 0, 0), ESCADA.length - 1),
      sucessos: Math.max(parseInt(e.sucessos || 0, 10) || 0, 0),
    };
  } catch {
    // fail-closed: estado ilegível não libera requisição
    return { requisicoes: [], pausa_ate: agora() + PAUSA_ILEGIVEL_S, motivo: "estado do disjuntor ilegível (fail-closed)",
      incidentes: [], nivel: ESCADA.length - 1, sucessos: 0 };
  }
}

export function gravarEstado(e) {
  const tmp = `${arqEstado()}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(e), "utf8");
  fs.renameSync(tmp, arqEstado());
}

export function pausar(segundos, motivo, sobeEscada = false) {
  pausaMemoria = Math.max(pausaMemoria, agora() + segundos);
  try {
    comTrava(() => {
      const e = lerEstado();
      e.pausa_ate = Math.max(e.pausa_ate || 0, agora() + segundos);   // pausa só cresce
      e.motivo = motivo;
      e.incidentes = [...(e.incidentes || []), { quando: agoraIso(), motivo }].slice(-30);
      if (sobeEscada) {   // só recusa do portal aperta o ritmo; timeout e erro interno, não
        e.nivel = Math.min((e.nivel || 0) + 1, ESCADA.length - 1);
        e.sucessos = 0;
      }
      gravarEstado(e);
    });
  } catch { /* o disco falhou: a pausa em memória já vale */ }
}

export function registrarSucesso() {
  try {
    comTrava(() => {
      const e = lerEstado();
      if (e.nivel === 0) return;
      e.sucessos += 1;
      if (e.sucessos >= SUCESSOS_PARA_RELAXAR) { e.nivel -= 1; e.sucessos = 0; }
      gravarEstado(e);
    });
  } catch { /* melhor esforço */ }
}

/** Reserva uma requisição ou lança PesquisaNaoRealizada. Espera só o espaçamento curto (laço limitado). */
export async function pedirVez() {
  for (let tentativa = 0; tentativa < 12; tentativa++) {
    const espera = comTrava((travou) => {
      if (!travou) throw new PesquisaNaoRealizada(`não consegui a trava do disjuntor (permissão em \`${arqEstado()}.lockdir\`?); sem trava não há requisição (fail-closed).`);
      const e = lerEstado();
      const t = agora();
      const pausa = Math.max(e.pausa_ate || 0, pausaMemoria);
      if (pausa > t) {
        const falta = Math.floor((pausa - t) / 60) + 1;
        throw new PesquisaNaoRealizada(`disjuntor em pausa por mais ~${falta} min (${e.motivo || "pausa em memória"}). Não contornar por navegador, proxy ou outro cliente.`);
      }
      const reqs = e.requisicoes;
      if (reqs.length >= DIA_MAX) throw new PesquisaNaoRealizada(`teto diário de ${DIA_MAX} requisições atingido.`);
      const [espacamento, janelaMax] = ESCADA[e.nivel];
      if (reqs.filter((x) => t - x < JANELA_S).length >= janelaMax)
        throw new PesquisaNaoRealizada(`teto de ${janelaMax} requisições em ${Math.floor(JANELA_S / 60)} min atingido` +
          (e.nivel ? ` (ritmo apertado, degrau ${e.nivel} da escada, por recusa anterior do portal)` : "") + "; tente de novo em alguns minutos.");
      const esp = reqs.length ? Math.max(...reqs) + espacamento - t : 0;
      if (esp <= 0) {
        e.requisicoes = [...reqs, t];
        try { gravarEstado(e); } catch (ex) {
          throw new PesquisaNaoRealizada(`não consegui registrar a requisição no disjuntor (${ex.code || ex.name}); sem registro não há requisição (fail-closed).`);
        }
        return 0;
      }
      return esp;
    });
    if (espera === 0) return;
    await dormir(Math.min(Math.max(espera, 0.05), ESCADA[ESCADA.length - 1][0]));
  }
  throw new PesquisaNaoRealizada("disputa pelo disjuntor com outro processo; tente de novo em instantes.");
}

/** Timeout/queda de conexão x recusa do portal. Só a segunda arma o disjuntor: seção de câmara cível passa de 2 MB,
 * então estourar o timeout é normal e não é sinal de bloqueio. No fetch do Node toda falha de REDE é `TypeError: fetch failed`. */
export function falhaTransitoria(ex) {
  if (!ex) return false;
  if (ex.name === "AbortError" || ex.name === "TimeoutError") return true;
  return ex instanceof TypeError && /fetch failed|terminated|network/i.test(String(ex.message));
}

let fetchImpl = (...a) => globalThis.fetch(...a);
/** Só para teste: troca o fetch por um simulado. */
export function _trocarFetch(f) { const antes = fetchImpl; fetchImpl = f ?? ((...a) => globalThis.fetch(...a)); return antes; }

export async function http(metodo, url, { params = null, data = null, referer = null } = {}) {
  await pedirVez();
  const h = { "User-Agent": userAgent(), "Accept-Language": "pt-BR,pt;q=0.9" };
  if (referer) h.Referer = referer;
  let corpo;
  if (data) {   // o portal é ISO-8859-1
    corpo = Object.entries(data).map(([k, v]) => `${k}=${quoteLatin1(v)}`).join("&");
    h["Content-Type"] = "application/x-www-form-urlencoded";
  }
  let alvo = url;
  if (params) alvo += "?" + Object.entries(params).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
  let r, buf;
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 90_000);
    try {
      r = await fetchImpl(alvo, { method: metodo, headers: h, body: corpo, redirect: "manual", signal: ctrl.signal });
      buf = r.status === 200 ? Buffer.from(await r.arrayBuffer()) : null;
    } finally { clearTimeout(t); }
  } catch (ex) {
    if (falhaTransitoria(ex))
      throw new PesquisaNaoRealizada(`falha de rede transitória (${ex.name}); nada foi pausado, chame de novo. Isto NÃO é 'não localizado'.`);
    pausar(PAUSA_ERRO_S, `falha de rede: ${ex.name}`);
    throw new PesquisaNaoRealizada(`falha de rede (${ex.name}); pausa de 30 min, sem retentativa.`);
  }
  if (r.status === 429 || r.status === 403) {
    pausar(PAUSA_BLOQUEIO_S, `HTTP ${r.status}`, true);
    throw new PesquisaNaoRealizada(`HTTP ${r.status} — possível bloqueio; pausa de 6 h, zero retentativa.`);
  }
  if (r.status !== 200) {
    pausar(PAUSA_ERRO_S, `HTTP ${r.status}`);
    throw new PesquisaNaoRealizada(`HTTP ${r.status}; pausa de 30 min.`);
  }
  const texto = buf.toString("latin1");   // ISO-8859-1 estrito (o TextDecoder("iso-8859-1") do navegador é windows-1252)
  const baixo = texto.toLowerCase();
  const ib = baixo.indexOf("<body");
  const janelas = baixo.slice(0, 1500) + (ib >= 0 ? baixo.slice(ib, ib + 1500) : "");
  const conteudoEsperado = ["relatorio.wsp", "<h4>boletim n", "wiformgridnav", "onclick=\"ver('", "javascript:abre(", "function submitwigrid"]
    .some((x) => baixo.includes(x));
  // a marca só vale como desafio se a página NÃO for o que pedimos: ementa de consumidor fala em "código de segurança"
  if (MARCAS_DESAFIO.some((m) => janelas.includes(m)) && !conteudoEsperado) {
    pausar(PAUSA_DESAFIO_S, "desafio anti-robô/CAPTCHA detectado", true);
    throw new PesquisaNaoRealizada("o portal respondeu com desafio anti-robô; pausa de 24 h. Nunca contornar.");
  }
  registrarSucesso();
  return texto;
}

export const _internos = { get pausaMemoria() { return pausaMemoria; }, zerarPausaMemoria() { pausaMemoria = 0; } };
export const arquivoDeEstado = () => path.basename(arqEstado());
