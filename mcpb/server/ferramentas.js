// Ferramentas com rede e saída final — porte de `servidor_tjse.py` (sincronizar, obter, verificar, diagnostico).
import fs from "node:fs";
import { ARQUIVO_PACOTE, baixarEExtrair, estado as estadoPacote } from "./pacote.js";
import {
  BOLETIM, URL_TEOR, URL_FORM_TURNSTILE, VERSAO, arqDb, dirDados, dirSecoes, dirRecibos, complementos, JANELA_S, DIA_MAX, ESCADA,
  SUCESSOS_PARA_RELAXAR, MAX_REQ_POR_SINCRONIZACAO, PesquisaNaoRealizada, PedidoRecusado, AmbienteIncompativel, userAgent,
} from "./config.js";
import { comTrava, http, lerEstado, dormir } from "./disjuntor.js";
import { db, um, todos, escalar, cobertura, indexarSecao, importarSecoesDoBruto, guardarBruto, paginasEmDisco, gravaMeta } from "./indice.js";
import { br, norm, normOrgao, semAcento } from "./texto.js";
import {
  parseEdicoes, parseMenu, parseSecao, parseTeor, proximaPosicao, camposGrid, anomaliasSecao, linkTeor, PARSER_VERSAO,
} from "./parse.js";
import { conferir, nomeProprio } from "./confere.js";
import { gravarRecibo, lerRecibo } from "./recibos.js";
import { outrosAcordaosDoProcesso } from "./busca.js";
import { linkRelato } from "./avisos.js";

// ---------------------------------------------------------------------------- sincronização
/** Baixa para o índice local as edições do Boletim dos últimos `meses`. O orçamento de TEMPO (prazoMs) existe porque o
 * cliente MCP aborta chamadas longas: ao esgotar, devolve o que fez e pede para chamar de novo — nada é rebaixado. */
export async function sincronizar(meses = 3, maxRequisicoes = MAX_REQ_POR_SINCRONIZACAO, { prazoMs = null } = {}) {
  meses = Math.max(1, Math.min(Math.trunc(meses), 24));
  const orc = Math.max(2, Math.min(Math.trunc(maxRequisicoes), MAX_REQ_POR_SINCRONIZACAO));
  const con = db();
  let gasto = 0, tempoEsgotado = false;
  const linhas = [];
  const hoje = new Date();
  const total = hoje.getFullYear() * 12 + hoje.getMonth() - meses;   // getMonth() já é 0-11
  const ini = new Date(Math.floor(total / 12), total % 12, 1);
  const dmy = (d) => `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
  const estourouTempo = () => { if (prazoMs !== null && Date.now() > prazoMs) tempoEsgotado = true; return tempoEsgotado; };
  let eds = [], falta = 0;
  const adiadas = [];
  try {
    const h = await http("POST", `${BOLETIM}/pesquisar.wsp`, { referer: `${BOLETIM}/pesquisar.wsp`, data: {
      tmp_origem: "", "tmp.diario.dt_inicio": dmy(ini), "tmp.diario.dt_fim": dmy(hoje), "tmp.diario.cd_caderno": "",
      "tmp.diario.cd_secao": "", "tmp.diario.pal_chave": "", "wi.token": "", "tmp.diario.id_advogado": "" } });
    gasto++;
    eds = parseEdicoes(h);
    if (!eds.length) return "PESQUISA NÃO REALIZADA — a listagem de edições veio sem nenhuma edição reconhecível (layout mudou?).";
    for (const e of eds) con.prepare("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)").run(e.edicao, e.rotulo, e.data);
    externo: for (const e of [...eds].sort((a, b) => b.edicao - a.edicao)) {   // mais recente primeiro
      const feitas = new Set(todos(con, "SELECT codigo FROM secoes WHERE edicao=?", e.edicao).map((r) => r.codigo));
      const menuConhecido = um(con, "SELECT valor FROM meta WHERE chave=?", `menu:${e.edicao}`);
      let secs;
      if (menuConhecido) secs = JSON.parse(menuConhecido.valor);
      else {
        if (gasto >= orc || estourouTempo()) break;
        const hm = await http("GET", `${BOLETIM}/menu.wsp`, { referer: `${BOLETIM}/inicial.wsp`, params: {
          "tmp.diario.nu_edicao": e.edicao, "tmp.diario.id_advogado": "", "tmp.diario.cd_caderno": "", "tmp.diario.cd_secao": "", "tmp.diario.pal_chave": "" } });
        gasto++;
        secs = parseMenu(hm);
        if (!secs.length) {
          linhas.push(`  ⚠ menu da edição ${e.edicao} veio sem nenhuma seção reconhecível — edição NÃO sincronizada (será tentada de novo; se persistir, o layout mudou).`);
          continue;
        }
        gravaMeta(con, `menu:${e.edicao}`, JSON.stringify(secs));
      }
      for (const s of secs) {
        if (feitas.has(s.codigo)) continue;
        const vz = um(con, "SELECT valor FROM meta WHERE chave=?", `vazia:${e.edicao}:${s.codigo}`);
        if (vz && (Date.now() / 1000 - Number(vz.valor)) < 7 * 86400) continue;   // veio sem acórdão há menos de 7 dias: não insiste
        if (gasto >= orc || estourouTempo()) break externo;
        let [pags, completa] = paginasEmDisco(e.edicao, s.codigo);   // retoma do que já está em disco
        let estourou = false;
        while (!completa) {
          if (gasto >= orc || estourouTempo()) { estourou = true; break; }
          let dados;
          if (!pags.length) dados = { "tmp.diario.cd_secao": s.codigo, "tmp.diario.nu_edicao": e.edicao, "tmp.diario.id_advogado": "", "tmp.diario.pal_chave": "" };
          else {
            dados = camposGrid(pags[pags.length - 1]);
            dados["grid.lista_conteudodiario.next"] = String(proximaPosicao(pags[pags.length - 1]));
            if (!("tmp.diario.cd_secao" in dados))
              throw new PesquisaNaoRealizada(`há página seguinte na seção ${s.nome} da edição ${e.edicao}, mas o formulário de paginação não foi reconhecido (layout mudou).`);
          }
          const hs = await http("POST", `${BOLETIM}/principal.wsp`, { referer: `${BOLETIM}/menu.wsp`, data: dados });
          gasto++;
          if (!hs.slice(-400).toLowerCase().includes("</html>"))
            throw new PesquisaNaoRealizada(`resposta TRUNCADA na seção ${s.nome} da edição ${e.edicao} (${hs.length} caracteres, sem </html>); nada dela foi indexado.`);
          const novosIds = new Set(parseSecao(hs).map((i) => i.acordao));
          if (pags.length && novosIds.size) {
            const antes = new Set(pags.flatMap((h0) => parseSecao(h0).map((i) => i.acordao)));
            if ([...novosIds].every((x) => antes.has(x)))
              throw new PesquisaNaoRealizada(`a página ${pags.length + 1} da seção ${s.nome} (ed. ${e.edicao}) repetiu a anterior — o portal ignorou a paginação; seção NÃO marcada como baixada.`);
          }
          if (!novosIds.size) {
            // seção sem acórdão NUNCA é marcada como baixada: pode ser página de erro ou mês sem julgado naquele órgão. Nova tentativa só depois de 7 dias.
            gravaMeta(con, `vazia:${e.edicao}:${s.codigo}`, String(Date.now() / 1000));
            linhas.push(`  ⚠ edição ${e.edicao} · ${s.nome}: NENHUM acórdão reconhecido ` +
              (hs.includes("relatorio.wsp") ? "apesar de haver links — layout mudou" : "(página de erro, ou órgão sem julgado publicado no mês)") +
              "; seção NÃO marcada como baixada — nova tentativa em 7 dias; a edição fica como incompleta.");
            estourou = true;
            break;
          }
          guardarBruto(e.edicao, s.codigo, hs, pags.length + 1);
          pags.push(hs);
          completa = proximaPosicao(hs) === null;
        }
        if (estourou || !completa) {
          if (pags.length && !completa) linhas.push(`  … edição ${e.edicao} · ${s.nome}: ${pags.length} página(s) guardada(s), FALTAM páginas — seção ainda fora do índice; chame de novo.`);
          if (gasto >= orc || tempoEsgotado) break externo;
          continue;
        }
        const itens = parseSecao(pags.join("\n"));   // juntas: a classe aberta na página 1 continua na 2
        const novos = indexarSecao(con, e.edicao, s.codigo, s.nome, itens);
        const an = itens.length ? anomaliasSecao(itens) : [];
        linhas.push(`  edição ${e.edicao} (${br(e.data)}) · ${s.nome}: ${itens.length} acórdãos em ${pags.length} página(s) (${novos} novos)` + (an.length ? ` ⚠ ANOMALIAS: ${an.join("; ")}` : ""));
      }
    }
    for (const e of eds) {
      const m = um(con, "SELECT valor FROM meta WHERE chave=?", `menu:${e.edicao}`);
      const nSecs = m ? JSON.parse(m.valor).length : 5;   // edição ainda não visitada: 5 seções é o medido
      const nVz = escalar(con, "SELECT COUNT(*) n FROM meta WHERE chave LIKE ? AND CAST(valor AS REAL) > ?", `vazia:${e.edicao}:%`, Date.now() / 1000 - 7 * 86400);
      falta += Math.max(0, nSecs - nVz - escalar(con, "SELECT COUNT(*) n FROM secoes WHERE edicao=?", e.edicao));
      if (nVz) adiadas.push(`ed. ${e.edicao}: ${nVz}`);
    }
  } catch (ex0) {
    const interno = !(ex0 instanceof PesquisaNaoRealizada);
    const ex = interno ? `ERRO INTERNO do servidor (${ex0.name}: ${ex0.message}) — é defeito da ferramenta, não do portal; avise o advogado` : ex0.message;
    const relato = interno ? `\nSe persistir, relate: ${linkRelato("sincronizacao")}` : "";
    return `SINCRONIZAÇÃO INTERROMPIDA — ${ex}\nFeito antes da interrupção (${gasto} requisições):\n${linhas.join("\n") || "  nada"}\nÍndice: ${cobertura(con)}${relato}`;
  }
  const maisAntiga = eds.map((x) => x.data || "9999-12-31").sort()[0];
  const curto = eds.length < meses - 1
    ? `\n⚠ Pedi ${meses} mês(es) e a lista do portal trouxe ${eds.length} edição(ões) (a mais antiga de ${br(maisAntiga)}): o portal pode limitar a listagem — o período anterior NÃO foi coberto.` : "";
  const cont = curto + (falta
    ? `\nFaltam ≥ ${falta} seção(ões) no período pedido: chame de novo (${tempoEsgotado ? "o tempo desta chamada acabou" : `o teto por chamada é ${orc} requisições`}; o que já foi baixado não é rebaixado).`
    : (adiadas.length
      ? `\nNenhuma seção pendente de download, MAS há seção que veio SEM ACÓRDÃO e não entrou no índice (${adiadas.join("; ")}): pode ser órgão sem julgado no mês ou página de erro. Enquanto não entrarem, a edição segue contada como INCOMPLETA e zero resultado nela vale menos. Nova tentativa automática 7 dias depois da última.`
      : "\nTodas as edições LISTADAS pelo portal no período estão completas."));
  return `Sincronização do Boletim Jurídico do TJSE — ${gasto} requisição(ões)\n${linhas.join("\n") || "  nada novo"}${cont}\nÍndice: ${cobertura(con)}`;
}

// ---------------------------------------------------------------------------- inteiro teor e conferência
async function teor(acordao, processo) {
  const lk = linkTeor(acordao);   // aceita a URL do inteiro teor colada
  if (lk) { processo = lk.processo; acordao = lk.acordao; }
  acordao = String(acordao || "").replace(/\D/g, "");
  if (acordao.length === 12 && !processo) throw new PedidoRecusado("isso parece nº de PROCESSO (12 dígitos); o inteiro teor pede o nº do ACÓRDÃO (ano + sequencial, de 5 a 9 dígitos). Ache-o com `buscar_jurisprudencia_tjse(numero=…)`.");
  if (!acordao) throw new PedidoRecusado("informe o nº do acórdão (ano + sequencial, de 5 a 9 dígitos, como sai na busca).");
  let rec = lerRecibo(acordao);
  const doDisco = rec !== null;
  if (rec === null) {
    processo = String(processo || "").replace(/\D/g, "");
    if (!processo) {
      const row = um(db(), "SELECT processo FROM acordaos WHERE acordao=?", acordao);
      if (!row) throw new PedidoRecusado("acórdão fora do índice local: informe também `numero_processo` (o link do TJSE exige os dois), ou cole a URL do inteiro teor. " +
        (complementos().length ? "" : "Os dois números aparecem em qualquer citação completa do TJSE e na página do acórdão no portal oficial."));
      processo = row.processo;
    }
    const h = await http("GET", URL_TEOR, { params: { "tmp.numprocesso": processo, "tmp.numacordao": acordao } });
    const d = parseTeor(h);
    if (d.acordao !== acordao || d.texto.length < 400)
      throw new PesquisaNaoRealizada("o portal respondeu, mas sem o acórdão pedido (par processo/acórdão errado, ou página vazia). Nada foi gravado.");
    rec = gravarRecibo(acordao, processo, h);
  }
  return [rec, parseTeor(rec.html), doDisco];
}

const orgaoFonte = (d) => (d.orgao_fecho && !d.fecho_ambiguo ? "fecho" : "cadastro (seção do Boletim)");

function orgaoEAvisos(d, acordao) {
  const row = um(db(), "SELECT orgao FROM acordaos WHERE acordao=?", acordao);
  const cad = row ? row.orgao : null, avisos = [];
  if (d.fecho_ambiguo) {
    avisos.push("FECHO AMBÍGUO: o texto tem fechos de órgãos diferentes (embargos que transcrevem o acórdão embargado?). Órgão exibido é o da seção do Boletim, com ressalva — confira lendo.");
    return [cad || "órgão não determinado", avisos];
  }
  if (d.orgao_fecho) {
    if (cad && normOrgao(cad) !== normOrgao(d.orgao_fecho)) avisos.push(`DIVERGÊNCIA: Boletim publica em '${cad}', o fecho diz '${d.orgao_fecho}'. Vale o fecho.`);
    return [d.orgao_fecho, avisos];
  }
  avisos.push("Fecho ('ACORDAM… Tribunal de Justiça do Estado de Sergipe') não localizado: órgão é o da seção do Boletim.");
  return [cad || "órgão não determinado", avisos];
}

const citacao = (d, orgao, link, nivel) => {
  const dj = d.data_julgamento ? `, julgado em ${br(d.data_julgamento)}` : "";
  return `([TJSE, ${d.recurso || "Acórdão"}, processo nº ${d.processo}, acórdão nº ${d.acordao}, Rel. ${nomeProprio(d.relator || "?")}, ${orgao}${dj}](${link})) — verificação: ${nivel}`;
};

export async function obter(numeroAcordao, numeroProcesso = null, comPartes = false, maxCaracteres = 60000) {
  let rec, d, doDisco;
  try { [rec, d, doDisco] = await teor(numeroAcordao, numeroProcesso); } catch (ex) {
    if (ex instanceof PesquisaNaoRealizada) return `PESQUISA NÃO REALIZADA — ${ex.message} Isto NÃO é 'não localizado'.`;
    if (ex instanceof PedidoRecusado) return `Pedido recusado: ${ex.message}`;
    throw ex;
  }
  const [orgao, avisos] = orgaoEAvisos(d, rec.acordao);
  maxCaracteres = Math.max(2000, Math.trunc(maxCaracteres || 0));
  try {
    const outros = outrosAcordaosDoProcesso(db(), rec.processo, rec.acordao);
    if (outros) avisos.push(outros.replace(/^⚠ /, ""));
  } catch { /* aviso é acessório */ }
  if (rec.aviso) avisos.push(rec.aviso);
  let corpo = comPartes ? d.texto : d.texto.slice(d.inicio_conteudo);
  let nivel = "inteiro teor lido";
  if (corpo.length > maxCaracteres) {
    corpo = corpo.slice(0, maxCaracteres) + `\n[… cortado em ${maxCaracteres} de ${d.texto.length} caracteres; o recibo tem tudo]`;
    nivel = "inteiro teor lido EM PARTE (saída cortada — peça o resto com max_caracteres maior antes de afirmar o que o voto diz)";
  }
  if ((d.datas_fecho || []).length > 1) avisos.push(`Há ${d.datas_fecho.length} datas no fecho (${d.datas_fecho.map(br).join(", ")}); usei a última. Confira.`);
  if (!comPartes && !d.partes_cortadas) avisos.push("Cabeçalho 'EMENTA' não localizado: a qualificação das partes NÃO pôde ser cortada desta saída.");
  return `TJSE — acórdão ${rec.acordao} · processo ${rec.processo} · ${d.recurso}\n` +
    `Relator(a): ${d.relator} · Órgão: ${orgao} · Julgamento: ${br(d.data_julgamento)}\n` +
    `orgao_fonte: ${orgaoFonte(d)}\n` +
    `Fonte: ${rec.url}\nRecibo: ${doDisco ? "lido do disco" : "gravado agora"} · obtido em ${rec.obtido_em} · sha256 ${rec.sha256.slice(0, 16)}…\n` +
    avisos.map((a) => `⚠ ${a}\n`).join("") +
    "⚠ O voto costuma TRANSCREVER ementas de outros tribunais: trecho destacado não é, por isso, palavra do TJSE.\n" +
    (comPartes ? "" : "(só o bloco de QUALIFICAÇÃO das partes foi cortado; relatório e voto continuam nomeando pessoas, às vezes menor de idade e seu representante — não colar em lugar nenhum fora da peça)\n") +
    `Citação: ${citacao(d, orgao, rec.url, nivel)}\n${"─".repeat(60)}\n${corpo}`;
}

export async function verificar(numeroAcordao, trecho, numeroProcesso = null) {
  let rec, d, doDisco;
  try { [rec, d, doDisco] = await teor(numeroAcordao, numeroProcesso); } catch (ex) {
    if (ex instanceof PesquisaNaoRealizada) return `PESQUISA NÃO REALIZADA — ${ex.message} A citação fica NÃO CONFERIDA (não é ❌).`;
    if (ex instanceof PedidoRecusado) return `Pedido recusado: ${ex.message}`;
    throw ex;
  }
  const r = conferir(d.texto.slice(d.inicio_conteudo), trecho);
  const [orgao, avisos] = orgaoEAvisos(d, rec.acordao);
  const base = `acórdão ${rec.acordao} (recibo ${doDisco ? "do disco" : "gravado agora"}, sha256 ${rec.sha256.slice(0, 16)}…)`;
  if (!r.ok) return `❌ NÃO CONFERE — ${base}\nFragmento que não aparece literalmente: «${r.fragmento || r.erro}»\nNão vai entre aspas. (Diferença de número '1.000'≠'1000' ou palavra cortada também dá ❌ — o lado seguro.)`;
  return `✅ CONFERE LITERALMENTE — ${base}\n` + [...r.alertas, ...avisos].map((a) => `⚠ ${a}\n`).join("") +
    `Contexto (normalizado): …${r.contexto}…\nCitação: ${citacao(d, orgao, rec.url, "inteiro teor lido")}`;
}

// ---------------------------------------------------------------------------- diagnóstico
export function diagnostico() {
  try { return _diagnostico(); } catch (ex) {
    if (ex instanceof AmbienteIncompativel) return `tjse_jurisprudencia v${VERSAO}: ${ex.message}`;
    if (/locked/i.test(String(ex.message)))
      return `tjse_jurisprudencia v${VERSAO}: índice OCUPADO por outro processo (${ex.message}) — provavelmente uma sincronização ou reindexação em curso. Aguarde e repita; NÃO apague a base.`;
    return `tjse_jurisprudencia v${VERSAO}: o índice local está ILEGÍVEL (${ex.name}: ${ex.message}). Buscas não são confiáveis. Remédio: mover \`${arqDb()}\` para fora e importar/sincronizar de novo (o HTML bruto em \`${dirSecoes()}\` reconstrói o índice com \`importar_pacote_tjse\`).`;
  }
}

function _diagnostico() {
  const e = comTrava(() => lerEstado());
  const agora = Date.now() / 1000;
  const reqs = e.requisicoes.filter((t) => agora - t < 86400);
  const pausa = (e.pausa_ate || 0) - agora;
  const con = db();
  const nRec = fs.existsSync(dirRecibos()) ? fs.readdirSync(dirRecibos()).length : 0;
  const porSecao = todos(con, `SELECT s.nome, SUM(s.itens) n, COUNT(*) eds, MIN(e.data) a, MAX(e.data) b FROM secoes s JOIN edicoes e USING(edicao) GROUP BY s.nome ORDER BY s.nome`)
    .map((r) => `  ${r.nome}: ${r.n} acórdãos em ${r.eds} edição(ões), publicadas de ${br(r.a)} a ${br(r.b)}`).join("\n") || "  —";
  const buracos = todos(con, `SELECT e.edicao, e.data FROM edicoes e WHERE e.edicao BETWEEN (SELECT MIN(edicao) FROM secoes) AND (SELECT MAX(edicao) FROM secoes) AND (SELECT COUNT(*) FROM secoes s WHERE s.edicao=e.edicao) < 5`)
    .map((r) => `ed. ${r.edicao} (${br(r.data)})`);
  const mb = fs.existsSync(arqDb()) ? fs.statSync(arqDb()).size / 1e6 : 0;
  const nCit = escalar(con, "SELECT COUNT(*) n FROM citacoes");
  const nProcCit = escalar(con, "SELECT COUNT(DISTINCT ref) n FROM citacoes WHERE tipo='tjse'");
  const inc = (e.incidentes || []).slice(-8).map((i) => `  ${i.quando} — ${i.motivo}`).join("\n") || "  nenhum";
  const [esp, tetoJanela] = [ESCADA[e.nivel][0], ESCADA[e.nivel][1]];
  const compl = complementos();
  return `tjse_jurisprudencia v${VERSAO} (sem rede nesta chamada)\n` +
    `Disjuntor: ${pausa > 0 ? `EM PAUSA por ~${Math.trunc(pausa / 60 + 1)} min — ${e.motivo}` : "livre"}\n` +
    `Requisições: ${reqs.filter((t) => agora - t < JANELA_S).length}/${tetoJanela} em 10 min · ${reqs.length}/${DIA_MAX} em 24 h · espaçamento ${Math.round(esp)} s` +
    (e.nivel ? ` · RITMO APERTADO: degrau ${e.nivel} de ${ESCADA.length - 1} por recusa anterior do portal; ${SUCESSOS_PARA_RELAXAR - e.sucessos} consulta(s) limpa(s) para afrouxar` : "") +
    `\nÍndice (${mb.toFixed(1)} MB, parser v${PARSER_VERSAO}): ${cobertura(con)}\nPor seção:\n${porSecao}\n` +
    (buracos.length ? `⚠ Edições INCOMPLETAS dentro do intervalo coberto: ${buracos.join(", ")} — sincronize antes de confiar em zero resultado.\n` : "") +
    `Grafo de citações: ${nCit} arestas (${nProcCit} processos do TJSE citados)\n` +
    `Recibos de inteiro teor: ${nRec}\nIncidentes:\n${inc}\n` +
    `Modo: ${compl.length ? "híbrido — complementos declarados: " + compl.join(", ") : "autônomo (TJSE_COMPLEMENTOS vazio)"} · ` +
    `User-Agent: ${process.env.TJSE_USER_AGENT ? "definido por TJSE_USER_AGENT" : "padrão (identificado)"}\n` +
    `Dados em: ${dirDados()}\n` +
    `Fora do alcance: formulário oficial com Cloudflare Turnstile (${URL_FORM_TURNSTILE}) — não é usado nem contornado.`;
}

// ---------------------------------------------------------------------------- pacote de HTML bruto
const fmtMB = (b) => (b / 1048576).toFixed(0);

/** `baixar`: true = baixa o pacote do release e importa; false = só importa o que já está em `base/secoes`; undefined = baixa se estiver vazio. */
export async function importarPacote(baixar, { prazoMs = Date.now() + 45_000 } = {}) {
  const linhas = [];
  const temArquivos = () => fs.existsSync(dirSecoes()) && fs.readdirSync(dirSecoes()).some((n) => n.endsWith(".html.gz"));
  const quer = baixar === undefined ? !temArquivos() : Boolean(baixar);
  if (quer || estadoPacote.rodando) {
    const p = baixarEExtrair();
    const resultado = await Promise.race([p.then(() => "fim"), dormir(Math.max(0.05, (prazoMs - Date.now()) / 1000)).then(() => "tempo")]);
    if (resultado === "tempo" && estadoPacote.rodando)
      return `⏳ Baixando o pacote do TJSE (${ARQUIVO_PACOTE}): ${fmtMB(estadoPacote.baixado)}${estadoPacote.total ? ` de ${fmtMB(estadoPacote.total)}` : ""} MB. ` +
        "O download continua em segundo plano — chame `importar_pacote_tjse` de novo em instantes para concluir. Nada foi enviado do seu computador: é só um download.";
    if (estadoPacote.erro) return `PESQUISA NÃO REALIZADA — ${estadoPacote.erro}\nAlternativa: \`sincronizar_boletim_tjse\` baixa direto do portal do tribunal (mais lento).`;
    if (estadoPacote.concluido) linhas.push(`Pacote baixado e conferido (hash confere): ${estadoPacote.concluido.arquivos} arquivos, ${fmtMB(estadoPacote.concluido.bytes)} MB.`);
  } else if (!temArquivos()) {
    return `Nada em \`${dirSecoes()}\` para importar. Chame com baixar=true para baixar o pacote pronto do GitHub, ou use \`sincronizar_boletim_tjse\` (baixa direto do portal do tribunal, mais lento).`;
  }
  // a importação inteira leva ~10 s e é retomável: mesmo que o download tenha gasto o orçamento, ela ganha uma janela própria
  // (assim o usuário não precisa de uma terceira chamada só para um índice que já está a segundos de ficar pronto)
  return [...linhas, importarSecoesDoBruto(db(), { prazoMs: Math.max(prazoMs, Date.now() + 12_000) })].join("\n");
}
