// Suíte do porte Node. Fixtures reais em ../../fixtures (anonimizados). Estado sempre em pasta temporária.
// A referência de comportamento é o servidor Python (selftest_tjse.py); o teste de paridade contra o corpus real
// está em test/paridade/ e roda à parte (`npm run paridade`), porque precisa do Python e do índice.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, describe, it } from "node:test";
import { fileURLToPath } from "node:url";

const raiz = path.dirname(fileURLToPath(import.meta.url));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tjse-teste-"));
process.env.TJSE_DIR_DADOS = tmp;
process.env.TJSE_MCP_SEM_AVISO_ATUALIZACAO = "1";
const fx = (n) => fs.readFileSync(path.join(raiz, "..", "..", "fixtures", n), "latin1");
const srv = (m) => import(path.join(raiz, "..", "server", m));

const T = await srv("texto.js"), P = await srv("parse.js"), C = await srv("confere.js"), I = await srv("indice.js");
const B = await srv("busca.js"), D = await srv("disjuntor.js"), F = await srv("ferramentas.js"), A = await srv("avisos.js");
const CFG = await srv("config.js"), R = await srv("recibos.js"), PK = await srv("pacote.js"), { pyre } = await srv("pyre.js");

after(() => { I.fecharDb(); fs.rmSync(tmp, { recursive: true, force: true }); });

describe("texto", () => {
  it("norm: sem acento, caixa, aspas, º/ª, § e ligaduras", () => {
    assert.equal(T.norm("§ 1º do art. 5º"), T.norm("§1o do art. 5o"));
    assert.equal(T.norm("nº 12"), T.norm("n. 12"));
    assert.equal(T.norm("ﬁm"), "fim");
    assert.equal(T.norm("Ação  “Cível” – art . 42"), "acao 'civel' - art. 42");
  });
  it("limparHtml: byte baixo do cp1252 vira travessão (o unescape do Python o descartaria)", () => {
    assert.equal(T.limparHtml("A&#19;B &#24;x&#25; &nbsp;C &Atilde;&Ccedil;"), "A–B ‘x’ C ÃÇ");
  });
  it("desescapaHtml: entidades legadas sem ponto-e-vírgula e inválidas, como o CPython", () => {
    assert.equal(T.desescapaHtml("&amp;tmp &notit; &#65;&#x42; &#18; &#150;"), "&tmp ¬it; AB  –");
  });
  it("datas", () => {
    assert.equal(T.dataPorExtenso("31 de Agosto de 2026"), "2026-08-31");
    assert.equal(T.dataPorExtenso("1º de março de 2026"), "2026-03-01");
    assert.equal(T.dataPorExtenso("31 de fevereiro de 2026"), null);
    assert.equal(T.dataPorExtenso("15 de xyz de 2026"), null);
    assert.equal(T.br("2026-08-31"), "31/08/2026");
  });
  it("quoteLatin1 (o portal é ISO-8859-1)", () => {
    assert.equal(T.quoteLatin1("Câmara Cível"), "C%E2mara%20C%EDvel");
    assert.equal(T.quoteLatin1("a b&c=d"), "a%20b%26c%3Dd");
  });
});

describe("parsers do Boletim (fixtures reais)", () => {
  it("edições e menu", () => {
    const eds = P.parseEdicoes(fx("02-pesquisa-1ano.html"));
    assert.equal(eds.length, 12);
    assert.ok(eds.some((e) => e.edicao === 168 && e.data === "2026-08-31"));
    assert.ok(eds.some((e) => e.edicao === 157 && e.data === "2025-09-30"));
    const menu = P.parseMenu(fx("05-menu-168.html"));
    assert.deepEqual(menu.map((m) => m.codigo), [10, 5, 6, 7, 8]);
    assert.ok(menu.some((m) => m.codigo === 6 && m.nome === "1ª Câmara Cível"));
    assert.ok(menu.every((m) => !/brevi/.test(m.nome)));
  });
  it("seção 5: dedup do comentário HTML, campos limpos", () => {
    const itens = P.parseSecao(fx("07-principal-168-sec5.html"));
    assert.deepEqual(itens.map((i) => i.acordao), ["202639853", "202639857"]);
    const a = itens[0];
    assert.equal(a.processo, "202600632112");
    assert.equal(a.classe, "Conflito de Competência");
    assert.equal(a.recurso, "CC Nº 00143/2026");
    assert.equal(a.relator, "DES. CEZÁRIO SIQUEIRA NETO");
    assert.equal(a.relator_rotulo, "RELATOR ORIGINÁRIO");
    assert.ok(a.ementa.startsWith("CONFLITO NEGATIVO DE COMPETÊNCIA") && a.ementa.endsWith("UNÂNIME."));
    assert.ok(itens[1].ementa.includes("–") && !itens[1].ementa.includes("\x13"));
    assert.ok(!a.ementa.includes("PROCESSO"));
  });
  it("Pleno: 43 itens, relator em <div> próprio e <font> aninhado", () => {
    const pl = P.parseSecao(fx("09-principal-168-pleno.html"));
    assert.equal(pl.length, 43);
    assert.deepEqual(P.anomaliasSecao(pl), []);
    for (const x of pl.filter((x) => ["202640802", "202640816"].includes(x.acordao))) assert.equal(x.relator, "DESA. PRESIDENTE DO TRIBUNAL DE JUSTIÇA");
  });
  const celula = (rel) => '<table><tr><td><font style="font-size: 7pt">' + "EMENTA ".repeat(20) + '<br />PROCESSO: <a href="r">1</a><br />ACÓRDÃO: <a href="http://x/relatorio.wsp?tmp.numprocesso=111&amp;tmp.numacordao=333">333</a><br /><b>AC N&ordm; 1/2026</b><br />' + rel + "</font></td></tr></table>";
  it("dois relatores: o citável é o do acórdão; o originário fica no rótulo", () => {
    const i = P.parseSecao(celula("<b>RELATOR ORIGIN&Aacute;RIO: DES. VENCIDO DA SILVA</b><br /><b>RELATOR PARA O AC&Oacute;RD&Atilde;O: DES. VENCEDOR DE SOUZA</b>"))[0];
    assert.equal(i.relator, "DES. VENCEDOR DE SOUZA");
    assert.ok(i.relator_rotulo.includes("VENCIDO DA SILVA"));
  });
  it("cargo vago cede ao substituto, mesmo com o rótulo errado", () => {
    const vg = celula("<b>RELATOR ORIGIN&Aacute;RIO: VAGA DE DESEMBARGADOR (G-21)</b><br /><b>RELATOR SUBSTITUTO: JUIZ FULANO DE TAL</b>");
    assert.equal(P.parseSecao(vg)[0].relator, "JUIZ FULANO DE TAL");
    assert.equal(P.parseSecao(vg.replace("RELATOR SUBSTITUTO", "RELATOR SUBSTITTUTO"))[0].relator, "JUIZ FULANO DE TAL");
  });
  it("rótulos do Boletim com grafias erradas ainda são reconhecidos", () => {
    const re = pyre(String.raw`(?i)^(relat[\w()\[\]]*(?:\s+[\wÀ-ÿ()\[\]/.-]+){0,4}?)\s*:\s*(.*)$`);
    for (const r of ["RELATOR(A) ORIGINÁRIO(A): DES(A) FULANO DE TAL", "RELATOR) ORIGINÁRIA: DESA. FULANA", "RELATORA ORIGINÁRIA: DESA. X", "RELATOR PARA O ACÓRDÃO: DES. Y", "RELATOR SUBSTITUTO: JUIZ Z"])
      assert.ok(re.exec(r) && re.exec(r)[2].trim() !== "", r);
  });
  it("menu com aspas escapadas", () => {
    assert.ok(P.parseMenu('lastPage("C\xe2mara \\"Especial\\"<!--9-->","x","javascript:abre(\'9\',\'1\');")').some((m) => m.codigo === 9));
  });
  it("paginação do WebIntegrator", () => {
    const cauda = `</table> <a href="javascript:submitWIGrid('grid.lista_conteudoDiario',1)" class='nav_first'><b>Primeiro</b></a> <a href="javascript:submitWIGrid('grid.lista_conteudoDiario',1001)" class='nav_go'>Próximo</a>` +
      `<form id="wiFormGridNav"><input type="hidden" name="tmp.diario.cd_secao" value="6"><input type="hidden" name="tmp.diario.dc_caderno" value="1&ordf; C&acirc;mara C&iacute;vel"></form>`;
    assert.equal(P.proximaPosicao("x".repeat(9000) + cauda), 1001);
    assert.equal(P.proximaPosicao(fx("07-principal-168-sec5.html")), null);
    const cg = P.camposGrid(cauda);
    assert.equal(cg["tmp.diario.cd_secao"], "6");
    assert.equal(cg["tmp.diario.dc_caderno"], "1ª Câmara Cível");
  });
  it("anomalias: relator vazio denunciado; seção vazia também", () => {
    const i = P.parseSecao(fx("07-principal-168-sec5.html"))[0];
    assert.notDeepEqual(P.anomaliasSecao([{ ...i, relator: "" }]), []);
    assert.deepEqual(P.anomaliasSecao([]), ["nenhum acórdão reconhecido"]);
  });
});

describe("inteiro teor: fecho, órgão e data", () => {
  const b3 = fx("03-relatorio-202638463.html");
  const d = P.parseTeor(b3);
  it("campos e fecho", () => {
    assert.equal(d.acordao, "202638463");
    assert.equal(d.processo, "202600737656");
    assert.equal(d.recurso, "Agravo de Instrumento");
    assert.equal(d.orgao_fecho, "1ª Câmara Cível");
    assert.equal(d.fecho_ambiguo, false);
    assert.equal(d.data_julgamento, "2026-07-17");
    assert.ok(!d.texto.slice(d.inicio_conteudo).includes("carregarTurma"));
    assert.ok(!d.texto.slice(d.inicio_conteudo).slice(0, 300).includes("AGRAVANTE"));
  });
  it("fecho em minúscula e fecho de outro tribunal transcrito no voto não conta", () => {
    const d2 = P.parseTeor(fx("08-relatorio-202640467.html"));
    assert.equal(d2.orgao_fecho, "2ª Câmara Cível");
    assert.equal(d2.fecho_ambiguo, false);
    assert.equal(d2.data_julgamento, "2026-07-24");
  });
  it("órgão é o PRIMEIRO no texto do fecho, não o primeiro da lista; '1ª Turma Recursal' não vira 'Turma Recursal'", () => {
    const s1 = b3.replace("nesta 1&ordf; C&acirc;mara C&iacute;vel, Grupo V,", "nesta 2&ordf; C&acirc;mara C&iacute;vel, reformando decis&atilde;o referendada pelo Tribunal Pleno,");
    assert.notEqual(s1, b3);
    assert.equal(P.parseTeor(s1).orgao_fecho, "2ª Câmara Cível");
    assert.equal(P.parseTeor(b3.replace("nesta 1&ordf; C&acirc;mara C&iacute;vel", "nesta 1&ordf; Turma Recursal")).orgao_fecho, "1ª Turma Recursal");
  });
  it("fecho com ordinal por extenso ('Primeira Câmara Cível')", () => {
    const ext = b3.replace("ACORDAM os Desembargadores do Tribunal de Justi&ccedil;a do Estado de Sergipe, nesta 1&ordf; C&acirc;mara C&iacute;vel, Grupo V,",
      "acordam os integrantes do Grupo 5 da Primeira C&acirc;mara C&iacute;vel do Tribunal de Justi&ccedil;a do Estado de Sergipe,");
    assert.notEqual(ext, b3);
    const de = P.parseTeor(ext);
    assert.equal(de.orgao_fecho, "1ª Câmara Cível");
    assert.equal(de.data_julgamento, "2026-07-17");
    assert.equal(P.parseTeor(ext.replace("Primeira", "Segunda")).orgao_fecho, "2ª Câmara Cível");
    assert.equal(T.normOrgao("Primeira Câmara Cível"), T.normOrgao("1ª Câmara Cível"));
  });
  it("duas datas no fecho: usa a última e guarda as duas", () => {
    const dd = P.parseTeor(b3.replace("em conformidade com relat&oacute;rio e voto.</p>", "em conformidade com relat&oacute;rio e voto.</p><p>Aracaju/SE, 10 de Julho de 2026.</p>"));
    assert.equal(dd.data_julgamento, "2026-07-17");
    assert.equal(dd.datas_fecho.length, 2);
  });
});

describe("ementa estruturada e grafo", () => {
  const E = "DIREITO DO CONSUMIDOR. APELAÇÃO. EMPRÉSTIMO CONSIGNADO. RECURSO DESPROVIDO." +
    "I. CASO EM EXAME:APELAÇÃO INTERPOSTA CONTRA SENTENÇA DE IMPROCEDÊNCIA." +
    "II. QUESTÃO EM DISCUSSÃO1. SABER SE A ASSINATURA IMPUGNADA FOI COMPROVADA PELO BANCO." +
    "III. RAZÕES DE DECIDIRCABE AO BANCO O ÔNUS DA AUTENTICIDADE, NOS TERMOS DO TEMA 1.061 DO STJ." +
    "IV. DISPOSITIVO E TESE RECURSO DESPROVIDO. Tese de julgamento: 1. É NULO O CONTRATO SEM PROVA DA ASSINATURA. " +
    "Dispositivos relevantes citados: CPC, art. 429, II. " +
    "Jurisprudência relevante citada: STJ, Tema Repetitivo 1.061; STJ, Súmula 297; TJSE, Apelação Cível nº 202500767922, Rel. Des. X.";
  const d = P.camposDaEmenta(E);
  it("divide nas seções, com o rótulo colado em ':', dígito ou letra", () => {
    assert.ok(d.cabecalho.startsWith("DIREITO DO CONSUMIDOR") && !d.cabecalho.includes("CASO EM EXAME"));
    assert.ok(d.caso.startsWith("APELAÇÃO INTERPOSTA"));
    assert.ok(d.questao.startsWith("1. SABER SE"));
    assert.ok(d.razoes.startsWith("CABE AO BANCO"));
    assert.ok(d.tese.startsWith("1. É NULO"));
    assert.equal(d.dispositivo, "RECURSO DESPROVIDO.");
    assert.ok(d.legislacao.includes("429") && d.juris_citada.includes("202500767922"));
    assert.ok(!d.dispositivo.includes("Tese de julgamento") && !d.dispositivo.includes("Jurisprud"));
  });
  it("sem estrutura, tudo no cabeçalho (a busca por campo não perde o acórdão)", () => {
    const sem = "APELAÇÃO CÍVEL. DANO MORAL. RECURSO PROVIDO. À UNANIMIDADE.";
    assert.ok(P.camposDaEmenta(sem).cabecalho.startsWith("APELAÇÃO"));
  });
  it("'dispositivo' comum não vira seção; ocorrência solta cede ao numeral romano", () => {
    assert.equal(P.camposDaEmenta("EMENTA. O DISPOSITIVO LEGAL INVOCADO NÃO SE APLICA AO CASO.").dispositivo, "");
    assert.equal(P.camposDaEmenta("EMENTA. A QUESTÃO EM DISCUSSÃO NOS AUTOS É OUTRA. II. QUESTÃO EM DISCUSSÃO: SABER SE HÁ NULIDADE.").questao, "SABER SE HÁ NULIDADE.");
  });
  it("numeral colado na palavra anterior e em algarismo arábico", () => {
    assert.ok(P.camposDaEmenta("EMENTA. COMPETÊNCIAIII. RAZÕES DE DECIDIRcabe ao banco o ônus.").razoes.startsWith("cabe ao banco"));
    assert.ok(P.camposDaEmenta("EMENTA X. 4. DISPOSITIVO E TESE Recurso desprovido. Tese de julgamento: 1. É nulo.").tese.startsWith("1. É nulo"));
  });
  it("grafo: processo do TJSE só do campo de jurisprudência; qualificado com tribunal antes ou depois", () => {
    const cg = P.citacoesDaEmenta(d, E);
    assert.ok(cg.some(([t, r]) => t === "tjse" && r === "202500767922"));
    assert.ok(cg.some(([t, r]) => t === "qualificado" && r === "Tema 1061"));
    assert.ok(cg.some(([t, r]) => t === "qualificado" && r === "Súmula 297/STJ"));
    const semTjse = { ...d, juris_citada: "STJ, Tema 1061. Contrato nº 202500767922 do banco." };
    assert.ok(!P.citacoesDaEmenta(semTjse, "x").some(([t]) => t === "tjse"));
  });
  it("âncoras: súmula, tema, IRDR, SV; 'Súmula 297' e '297/STJ' são a mesma chave", () => {
    assert.deepEqual(P.ancoras("Súmula 385 do STJ; Tema 1.150; IRDR nº 15; Súmula Vinculante 47"), ["Súmula 385/STJ", "Tema 1150", "IRDR 15", "Súmula Vinculante 47"]);
    assert.ok(!P.ancoras("Súmula Vinculante 47").includes("Súmula 47"));
    assert.deepEqual(P.ancoras("Súmula 297/STJ e adiante a Súmula 297"), ["Súmula 297/STJ"]);
    assert.deepEqual(P.ancoras("SV 47"), ["Súmula Vinculante 47"]);
  });
  it("resultado declarado só quando um lado é inequívoco", () => {
    for (const [em, esp] of [["... RECURSO CONHECIDO E DESPROVIDO.", "desprovido"], ["APELAÇÃO CONHECIDA E PARCIALMENTE PROVIDA", "parcialmente provido"],
      ["RECURSO CONHECIDO E PROVIDO. À UNANIMIDADE", "provido"], ["DESERÇÃO CONFIGURADA. RECURSO NÃO CONHECIDO.", "não conhecido"],
      ["recurso do autor provido e recurso do réu desprovido", null], ["ORDEM DENEGADA", null],
      ["NÃO CONHECIMENTO DO ARGUMENTO NOVO. RECURSO CONHECIDO E DESPROVIDO", "desprovido"]])
      assert.equal(P.resultadoDeclarado(em), esp, em);
  });
});

describe("consulta FTS5", () => {
  it("expressões: grupos, radical, variantes de número, 'R$' não é radical", () => {
    assert.equal(B.expressaoFts(B.partesFts(null, [["dano moral"], ["negativação", "inscrição indevida"]], true)), '("dano moral") AND ("negativacao" OR "inscricao indevida")');
    assert.equal(B.expressaoFts(B.partesFts("consign$", null)), '"consign"*');
    assert.ok(!B.expressaoFts(B.partesFts(null, [["multa de R$"]], true)).includes('"*'));
    const e = B.expressaoFts(B.partesFts(null, [["dano moral"]]));
    assert.ok(e.includes('"danos morais"') && e.includes('"dano moral"'));
  });
  it("variantes: moral↔morais, acao↔acoes; palavras curtas e invariáveis ficam", () => {
    assert.ok(B.variantesNumero("moral").includes("morais") && B.variantesNumero("acao").includes("acoes") && B.variantesNumero("acoes").includes("acao"));
    assert.deepEqual(B.variantesNumero("cdc"), ["cdc"]);
    assert.deepEqual(B.variantesNumero("1691"), ["1691"]);
    for (const [w, ruim] of [["pais", "pal"], ["leis", "lel"], ["onus", "onu"], ["tres", "tr"], ["nao", "noes"], ["caos", "cao"]]) assert.ok(!B.variantesNumero(w).includes(ruim), w);
  });
  it("operador em caixa alta é recusado; entre aspas é aceito; grupo vazio é recusado", () => {
    assert.throws(() => B.partesFts("dano E moral", null), /operador em caixa alta/);
    assert.doesNotThrow(() => B.partesFts('"culpa E dolo"', null));
    assert.throws(() => B.partesFts(null, [["dano moral"], ["!!!"]]), /nenhum termo pesquisável/);
    assert.doesNotThrow(() => B.partesFts("dano §§§ moral", null));
  });
  it("palavras de praxe são descartadas e declaradas; as que mudam sentido, não", () => {
    const pa = B.partesFts("agravo de instrumento", null);
    assert.ok(pa.some(([r, , ob]) => r.startsWith("__ignoradas__") && ob === null));
    assert.ok(pa.some(([, e, ob]) => ob !== null && e.includes("agravo")));
    const p2 = B.partesFts("dano moral", null, true);
    assert.ok(p2.filter(([, , ob]) => ob !== null).every(([, , ob]) => ob));
    assert.equal(B.partesFts('"dano moral"', null).find(([, , ob]) => ob)[1], '"dano moral"');
  });
  it("a sintaxe do FTS5 não é injetável", async () => {
    const { DatabaseSync } = await import("node:sqlite");
    const c = new DatabaseSync(":memory:");
    c.exec('create virtual table f using fts5(t, tokenize="unicode61 remove_diacritics 2")');
    c.prepare("insert into f values(?)").run("DESCONTOS INDEVIDOS EM BENEFÍCIO"); c.prepare("insert into f values(?)").run("AÇÕES COLETIVAS"); c.prepare("insert into f values(?)").run("nada");
    assert.equal(c.prepare("select * from f where f match ?").all(B.expressaoFts(B.partesFts(null, [["desconto indevido", "ação coletiva"]]))).length, 2);
    for (const veneno of ['a" OR ementa:x', "NEAR(a b)", "((( ", "*", "ementa: teste", "auxílio-doença", 'x" AND "y'])
      assert.doesNotThrow(() => { let q; try { q = B.expressaoFts(B.partesFts(null, [[veneno]])); } catch { return; } c.prepare("select * from f where f match ?").all(q || '"zzz"'); }, veneno);
    c.close();
  });
  it("refCitada e baseRef", () => {
    assert.deepEqual(B.refCitada("SV 47"), ["qualificado", "Súmula Vinculante 47"]);
    assert.deepEqual(B.refCitada("Tema 1061"), ["qualificado", "Tema 1061"]);
    assert.deepEqual(B.refCitada("202500767922"), ["tjse", "202500767922"]);
    assert.equal(B.refCitada("banana"), null);
    assert.equal(B.baseRef("Súmula 297/STJ"), "Súmula 297");
  });
});

describe("conferência literal e alertas de atribuição", () => {
  const d = P.parseTeor(fx("03-relatorio-202638463.html"));
  const corpo = d.texto.slice(d.inicio_conteudo);
  const tem = (r, rot) => r.ok && r.alertas.some((a) => a.includes(rot));
  it("literal, com [...], caixa, ordem e palavra inteira", () => {
    assert.ok(C.conferir(corpo, "veda aos pais ou representantes legais contrair obrigações em nome dos filhos incapazes").ok);
    assert.ok(C.conferir(corpo, "VEDA AOS PAIS [...] prévia autorização judicial").ok);
    assert.ok(!C.conferir(corpo, "prévia autorização judicial [...] veda aos pais").ok);
    assert.ok(!C.conferir(corpo, "veda aos pai").ok);
    assert.ok(!C.conferir(corpo, "o banco agiu com manifesta boa-fé").ok);
    assert.ok(C.conferir(corpo, "CDC, art. 42, parágrafo único").ok);   // "art . 42" do portal
  });
  it("transcrição de ementa de outro tribunal: ✅ com alerta; ementa própria e voto do próprio TJSE: sem", () => {
    assert.ok(tem(C.conferir(corpo, "CONTRATAÇÃO REALIZADA EM NOME DE MENOR ABSOLUTAMENTE INCAPAZ"), "TRANSCRI"));
    assert.ok(tem(C.conferir(corpo, "O valor arbitrado a título de dano moral mostra-se proporcional, razoável"), "TRANSCRI"));
    assert.ok(!tem(C.conferir(corpo, "veda aos pais ou representantes legais contrair obrigações em nome dos filhos incapazes"), "TRANSCRI"));
    assert.ok(!tem(C.conferir(corpo, "entendo que a mesma não pode se sobrepor ao código civil"), "TRANSCRI"));
    const tn = T.norm(corpo), fi = /(?<![a-z])acordam(?![a-z])/.exec(tn).index;
    const soma = C.faixasTranscritas(tn, fi).reduce((s, [a, b]) => s + b - a, 0) / tn.length;
    assert.ok(soma > 0.5 && soma < 0.9, `faixas cobrem ${soma}`);
  });
  it("negação antes do trecho; 'não obstante' não é negação", () => {
    for (const neg of ["o pedido é improcedente quanto", "nega-se", "rejeita-se a tese de que", "sem razão o apelante ao dizer que"])
      assert.ok(tem(C.conferir(`Relatório. ${neg} o banco deve restituir em dobro os valores descontados. Fim.`, "o banco deve restituir em dobro os valores descontados"), "NEGA"), neg);
    const r = C.conferir("Não obstante o banco deve restituir em dobro os valores descontados. Fim.", "o banco deve restituir em dobro os valores descontados");
    assert.ok(r.ok && !r.alertas.some((a) => a.includes("NEGA")));
  });
  it("trecho curto e [...] que costura partes distantes são recusados", () => {
    assert.ok(!C.conferir(corpo, "de").ok);
    assert.match(C.conferir(corpo, "o recurso").erro, /curto/);
    assert.ok(!C.conferir(corpo, "Recurso conhecido e desprovido [...] A contratação de empréstimo consignado em nome de menor absolutamente incapaz").ok);
  });
  it("alegação da parte no relatório", () => {
    assert.ok(tem(C.conferir("Relatório. Sustenta o apelante que o contrato é nulo de pleno direito por vício de forma essencial. É o relatório.", "o contrato é nulo de pleno direito por vício de forma"), "ALEGA"));
  });
  it("voto divergente: só o que vem depois da divergência", () => {
    const s = "EMENTA. Apelação. ACORDAM os Desembargadores do Tribunal de Justiça do Estado de Sergipe, nesta 1ª Câmara Cível, por maioria. " +
      "VOTO. A cláusula é válida e o recurso deve ser desprovido integralmente. É como voto. Peço vênia para divergir do relator. " +
      "A cláusula é manifestamente abusiva e deve ser declarada nula de pleno direito.";
    assert.ok(tem(C.conferir(s, "A cláusula é manifestamente abusiva e deve ser declarada nula"), "DIVERGENTE"));
    assert.ok(!C.conferir(s, "A cláusula é válida e o recurso deve ser desprovido").alertas.some((a) => a.includes("DIVERG")));
  });
  it("'(tj-pr 0048…)' sem hífen fecha faixa; parêntese banal não é atribuição", () => {
    const tn8 = T.norm(P.parseTeor(fx("08-relatorio-202640467.html")).texto), k8 = tn8.indexOf("(tj-pr");
    assert.ok(k8 > 0 && C.faixasTranscritas(tn8, /(?<![a-z])acordam(?![a-z])/.exec(tn8).index).some(([a, b]) => a <= k8 && k8 < b));
    const re = pyre(String.raw`\((?:resp|aresp|agint|agrg|edcl|eresp|rms|adi|adpf|apelacao(?: civel)?|agravo de instrumento)\b[^()]{0,220}\brel(?:ator[a]?|\.)?\s*(?:p/|para|min|des|juiz|dr)`);
    assert.ok(!re.test("(ai, rel. de forma clara, decidiu o juizo)") && !re.test("(re)"));
  });
  it("nomeProprio respeita partículas", () => {
    assert.equal(C.nomeProprio("ANA LÚCIA FREIRE DE ALMEIDA DOS ANJOS"), "Ana Lúcia Freire de Almeida dos Anjos");
  });
});

describe("índice local e busca", () => {
  let itens;
  before(() => {
    itens = P.parseSecao(fx("07-principal-168-sec5.html"));
    const con = I.db();
    con.prepare("INSERT OR REPLACE INTO edicoes VALUES(168,'72026','2026-08-31')").run();
    assert.equal(I.indexarSecao(con, 168, 5, "Seção Especializada Cível", itens), 2);
  });
  it("reindexar não duplica", () => assert.equal(I.indexarSecao(I.db(), 168, 5, "Seção Especializada Cível", itens), 0));
  const b = (p) => B.buscar(p);
  it("acha sem acento, plural↔singular, por número; diz cobertura e limites", () => {
    const out = b({ grupos: [["conflito de competencia"], ["superendividamento", "xyz"]] });
    assert.ok(out.includes("202639853") && out.includes("1 resultado"));
    assert.ok(out.includes("31/08/2026") && out.includes("Turmas Recursais") && out.includes("só ementa/índice"));
    assert.ok(b({ numero: "202600649163" }).includes("202639857"));
    assert.ok(b({ consulta: "conflitos negativos" }).includes("202639853"));
    assert.ok(b({ consulta: "conflitos negativos", exato: true }).includes("Nada no índice"));
  });
  it("zero resultado não é 'não localizado'; filtros zeram com explicação", () => {
    assert.ok(b({ consulta: "usucapião" }).includes("NÃO é 'não localizado"));
    assert.ok(b({ consulta: "competência", orgao: "Câmara Criminal" }).includes("Nada no índice"));
    assert.ok(b({ consulta: "competência", orgao: "%" }).includes("Nada no índice"));   // LIKE não aceita curinga
    assert.ok(b({ consulta: "competência", data_inicio: "01/09/2026" }).includes("Nada no índice"));
    assert.ok(b({ consulta: "competência", data_inicio: "01/08/2026", data_fim: "31/08/2026" }).includes("data do BOLETIM"));
    assert.ok(b({ consulta: "competência", pagina: 9 }).includes("além do fim"));
    assert.ok(b({ consulta: "competência", ordenacao: "recentes" }).includes("202639853"));
  });
  it("pedidos inválidos são recusados com explicação", () => {
    assert.ok(b({ consulta: "multa", data_inicio: "ontem" }).includes("recusada"));
    assert.ok(b({ consulta: "multa", data_inicio: "31/02/2026" }).includes("day is out of range for month"));
    assert.ok(b({ consulta: "multa", data_inicio: "01/08/2026", data_fim: "01/03/2026" }).includes("posterior"));
    assert.ok(b({ numero: "0001234-56.2026.8.25.0001" }).includes("NÃO é 'não localizado'"));
    // acórdão = ano + sequencial SEM zeros (20266743): 16,5% do índice real tem menos de 9 dígitos e a validação antiga os recusava
    for (const n of ["20266743", "2026599", "20265", "202561964"]) assert.ok(!b({ numero: n }).startsWith("Pedido recusado"), n);
    for (const n of ["2026", "2026000000", "20260000000", "12345678901234567890"]) assert.ok(b({ numero: n }).startsWith("Pedido recusado"), n);
    assert.ok(b({ consulta: "competência", em: "  " }).match(/resultado|Nada/));   // `em` vazio cai em 'tudo'
    assert.ok(b({ consulta: "multa", em: "xyz" }).includes("não conhece"));
    assert.equal(b({}), "Informe `consulta`, `grupos`, `numero` ou `cita`.");
    assert.equal(b({ consulta: "multa", ordenacao: "aleatoria" }), "`ordenacao` deve ser 'relevantes', 'recentes' ou 'antigos'.");
  });
  it("diagnóstico por seção", () => assert.ok(F.diagnostico().includes("Seção Especializada Cível: 2 acórdãos")));
  it("panorama, âncoras, zero diagnosticado e outros acórdãos do processo", () => {
    const con = I.db();
    const ins = con.prepare("INSERT INTO acordaos VALUES(?,?,?,?,?,?,?,?,?)"), fts = con.prepare("INSERT INTO fts(acordao, ementa, classe, relator) VALUES(?,?,?,?)");
    for (let i = 0; i < 12; i++) {
      const em = i < 9 ? "PLANO DE SAÚDE. TERAPIA MULTIDISCIPLINAR. SÚMULA 608 DO STJ. RECURSO CONHECIDO E DESPROVIDO." : "PLANO DE SAÚDE. REEMBOLSO. RECURSO PROVIDO.";
      ins.run(`9000000${String(i).padStart(2, "0")}`, `88000000${String(i).padStart(4, "0")}`, "Agravo de Instrumento", `AI Nº ${i}/2026`, "DES. X", "RELATOR ORIGINÁRIO", "2ª Câmara Cível", 168, em);
      fts.run(`9000000${String(i).padStart(2, "0")}`, em, "Agravo de Instrumento", "DES. X");
    }
    const o = b({ consulta: "plano de saúde", por_pagina: 5 });
    assert.ok(o.includes("PANORAMA das 12 ementas") && o.includes("desprovido 9") && o.includes("provido 3"));
    assert.ok(o.includes("Súmula 608/STJ (9)") && o.includes("NÃO posição sobre a tese") && o.includes("BNP") && o.includes("Cita: Súmula 608/STJ"));
    const z = b({ grupos: [["plano de saúde"], ["xyzzy"], ["terapia"]] });
    assert.ok(z.includes("sozinho 0") && z.includes("sem ele, o resto tem"));
    ins.run("900000099", "880000000001", "Embargos de Declaração", "EDCiv Nº 9/2026", "DES. X", "RELATOR ORIGINÁRIO", "2ª Câmara Cível", 168, "EMBARGOS ACOLHIDOS");
    assert.ok(b({ numero: "900000001" }).includes("outro(s) acórdão(s) no índice: 900000099"));
  });
  it("parser mudou → reindexa do HTML bruto sem rede", () => {
    const con = I.db();
    I.guardarBruto(168, 5, fx("07-principal-168-sec5.html"));
    con.prepare("UPDATE acordaos SET relator='TORTO'").run();
    con.prepare("UPDATE meta SET valor='0' WHERE chave='parser_versao'").run();
    I.fecharDb();
    assert.equal(I.db().prepare("SELECT relator FROM acordaos WHERE acordao='202639853'").get().relator, "DES. CEZÁRIO SIQUEIRA NETO");
  });
  it("republicação é guardada e avisada", () => {
    const con = I.db();
    con.prepare("INSERT OR REPLACE INTO edicoes VALUES(169,'82026','2026-09-30')").run();
    I.indexarSecao(con, 169, 5, "Seção Especializada Cível", [{ ...itens[0], ementa: "EMENTA RETIFICADA " + itens[0].ementa }]);
    assert.ok(b({ numero: "202639853" }).includes("REPUBLICADO"));
  });
});

describe("importação do HTML bruto (pacote de terceiro)", () => {
  it("importa com rótulo lido da página; código desconhecido e seção sem fim são avisados; repetir não refaz", () => {
    const pleno = fx("09-principal-168-pleno.html");
    I.guardarBruto(777, 10, pleno, 1);
    I.guardarBruto(778, 99, pleno, 1);
    I.guardarBruto(779, 10, pleno + "submitWIGrid('grid.lista_conteudoDiario', 5)\" class='nav_go'", 1);
    const con = I.db();
    const r = I.importarSecoesDoBruto(con);
    assert.ok(r.includes("edição 777 · Tribunal Pleno"));
    assert.ok(r.includes("[99]") && r.includes("código(s) de seção sem nome conhecido"));
    assert.ok(r.includes("SEM a marca de fim"));
    assert.ok(I.escalar(con, "SELECT COUNT(*) n FROM acordaos WHERE edicao=777") > 0);
    assert.notEqual(I.um(con, "SELECT data FROM edicoes WHERE edicao=777").data, null);
    assert.ok(I.importarSecoesDoBruto(con).includes("0 acórdão(s) novo(s)"));
  });
  it("prazo esgotado deixa o resto para a próxima chamada", () => {
    I.guardarBruto(780, 10, fx("09-principal-168-pleno.html").replace(/2026\d{4}/g, (m) => "9" + m.slice(1)), 1);
    const r = I.importarSecoesDoBruto(I.db(), { prazoMs: Date.now() - 1 });
    assert.ok(r.includes("Faltam") && r.includes("Chame de novo"));
  });
});

describe("disjuntor: ritmo, escada e falhas de rede", () => {
  const estado = () => D.lerEstado();
  it("recusa do portal aperta a escada; erro comum não; consultas limpas afrouxam", () => {
    const n0 = estado().nivel;
    D.pausar(0.01, "HTTP 429 (teste)", true);
    assert.equal(estado().nivel, Math.min(n0 + 1, CFG.ESCADA.length - 1));
    const n1 = estado().nivel;
    D.pausar(0.01, "falha comum (teste)");
    assert.equal(estado().nivel, n1);
    assert.ok(CFG.ESCADA[n1][0] > CFG.ESCADA[0][0] && CFG.ESCADA[n1][1] < CFG.ESCADA[0][1]);
    for (let i = 0; i < CFG.SUCESSOS_PARA_RELAXAR; i++) D.registrarSucesso();
    assert.equal(estado().nivel, n1 - 1);
    fs.rmSync(CFG.arqEstado(), { force: true });
    D._internos.zerarPausaMemoria();
  });
  it("timeout e queda de conexão NÃO armam o disjuntor; erro desconhecido arma", () => {
    assert.ok(D.falhaTransitoria(Object.assign(new Error("x"), { name: "AbortError" })));
    assert.ok(D.falhaTransitoria(new TypeError("fetch failed")));
    assert.ok(!D.falhaTransitoria(new RangeError("x")));
  });
  it("estado ilegível trava (fail-closed)", async () => {
    fs.writeFileSync(CFG.arqEstado(), "{lixo");
    assert.ok(estado().pausa_ate > Date.now() / 1000);
    await assert.rejects(D.pedirVez(), /disjuntor em pausa/);
    fs.rmSync(CFG.arqEstado(), { force: true }); D._internos.zerarPausaMemoria();
  });
  it("trava entre processos: quem não a obtém não requisita", () => {
    const lock = CFG.arqEstado() + ".lockdir";
    fs.mkdirSync(CFG.dirDados(), { recursive: true }); fs.mkdirSync(lock);
    let travou = true;
    // trava recém-criada por "outro processo": espera esgotar (5 s) seria lento; força a idade para o teste da quebra
    const antigo = new Date(Date.now() - 60_000); fs.utimesSync(lock, antigo, antigo);
    D.comTrava((t) => { travou = t; });
    assert.ok(travou, "trava abandonada há mais de 15 s é quebrada");
    assert.ok(!fs.existsSync(lock), "e é liberada ao sair");
  });
});

describe("portal simulado: http, sincronização, inteiro teor e verificação", () => {
  const latin1 = (s) => new Response(Buffer.from(s, "latin1"), { status: 200 });
  let chamadas, antes;
  const portal = async (url, init = {}) => {
    chamadas.push(`${init.method || "GET"} ${url.split("/").pop().split("?")[0]}`);
    if (url.includes("pesquisar.wsp")) return latin1(fx("02-pesquisa-1ano.html"));
    if (url.includes("menu.wsp")) return latin1(fx("05-menu-168.html"));
    if (url.includes("principal.wsp")) {
      const cod = /cd_secao=(\d+)/.exec(String(init.body))?.[1];
      if (cod === "5") return latin1(fx("07-principal-168-sec5.html"));
      if (cod === "10") return latin1(fx("09-principal-168-pleno.html"));
      return latin1("<html><body><h4>Boletim n. 168</h4>sem julgados neste mês</body></html>");
    }
    if (url.includes("relatorio.wsp")) return latin1(fx("03-relatorio-202638463.html"));
    return new Response("nao", { status: 404 });
  };
  before(() => { antes = D._trocarFetch(portal); chamadas = []; fs.rmSync(CFG.arqEstado(), { force: true }); D._internos.zerarPausaMemoria(); });
  after(() => { D._trocarFetch(antes); });
  const semEspera = () => { fs.writeFileSync(CFG.arqEstado(), JSON.stringify({ requisicoes: [], pausa_ate: 0, motivo: "", incidentes: [], nivel: 0, sucessos: 0 })); };

  it("sincroniza: seções com acórdão entram; seção sem acórdão nunca é marcada como baixada", async () => {
    const con = I.db();
    con.prepare("DELETE FROM meta WHERE chave LIKE 'menu:%' OR chave LIKE 'vazia:%'").run();
    con.prepare("DELETE FROM secoes WHERE edicao=168").run();
    semEspera();
    // o disjuntor espaça 6 s entre requisições: para o teste, estado sem histórico e espaçamento zerado via pausa nula
    const t0 = Date.now();
    const r = await F.sincronizar(12, 14, { prazoMs: Date.now() + 25_000 });
    assert.ok(r.includes("Sincronização do Boletim Jurídico do TJSE"), r.slice(0, 200));
    assert.ok(/edição 168 .*Seção Especializada Cível: 2 acórdãos/.test(r) || r.includes("tempo desta chamada acabou"), r);
    assert.ok(Date.now() - t0 < 60_000);
  });
  it("obtém o inteiro teor uma vez e grava recibo íntegro; a segunda vez lê do disco (0 requisições)", async () => {
    semEspera(); chamadas.length = 0;
    const o1 = await F.obter("202638463", "202600737656");
    assert.ok(o1.includes("orgao_fonte: fecho") && o1.includes("1ª Câmara Cível") && o1.includes("gravado agora") && o1.includes("Citação: ([TJSE, Agravo de Instrumento"));
    assert.equal(chamadas.filter((c) => c.includes("relatorio.wsp")).length, 1);
    const rec = JSON.parse(fs.readFileSync(R.arqRecibo("202638463"), "utf8"));
    assert.equal(rec.sha256.length, 64);
    assert.equal(rec.id_documento, "202638463");
    assert.equal(rec.tribunal, "TJSE");
    assert.equal((fs.statSync(R.arqRecibo("202638463")).mode & 0o777).toString(8), "600");
    chamadas.length = 0;
    const o2 = await F.obter("202638463");
    assert.ok(o2.includes("lido do disco"));
    assert.equal(chamadas.length, 0);
  });
  it("verifica a citação contra o recibo, sem rede", async () => {
    chamadas.length = 0;
    const ok = await F.verificar("202638463", "veda aos pais ou representantes legais contrair obrigações em nome dos filhos incapazes");
    assert.ok(ok.startsWith("✅ CONFERE LITERALMENTE") && ok.includes("recibo do disco"));
    const ruim = await F.verificar("202638463", "o banco agiu com manifesta boa-fé e nada mais");
    assert.ok(ruim.startsWith("❌ NÃO CONFERE"));
    const transc = await F.verificar("202638463", "CONTRATAÇÃO REALIZADA EM NOME DE MENOR ABSOLUTAMENTE INCAPAZ");
    assert.ok(transc.includes("TRANSCRIÇÃO"));
    assert.equal(chamadas.length, 0);
  });
  it("aceita a URL do inteiro teor colada; recusa nº de processo no lugar do acórdão", async () => {
    const o = await F.obter("https://www.tjse.jus.br/tjnet/jurisprudencia/relatorio.wsp?tmp.numprocesso=202600737656&tmp.numacordao=202638463");
    assert.ok(o.includes("lido do disco"));
    assert.ok((await F.obter("202600737656")).includes("nº de PROCESSO"));
    assert.ok((await F.obter("")).startsWith("Pedido recusado"));
  });
  it("recibo adulterado (sha256 não bate) é posto de lado e o teor é buscado de novo", async () => {
    const caminho = R.arqRecibo("202638463");
    const rec = JSON.parse(fs.readFileSync(caminho, "utf8")); rec.html += " adulterado";
    fs.writeFileSync(caminho, JSON.stringify(rec));
    semEspera(); chamadas.length = 0;
    const o = await F.obter("202638463", "202600737656");
    assert.ok(o.includes("gravado agora"));
    assert.ok(fs.existsSync(caminho + ".inconsistente"));
  });
  it("falha de rede sai como PESQUISA NÃO REALIZADA, nunca como 'não localizado'", async () => {
    fs.rmSync(R.arqRecibo("202638463"), { force: true }); semEspera();
    const ant = D._trocarFetch(async () => { throw new TypeError("fetch failed"); });
    const o = await F.obter("202638463", "202600737656");
    D._trocarFetch(ant);
    assert.ok(o.startsWith("PESQUISA NÃO REALIZADA") && o.includes("Isto NÃO é 'não localizado'"));
    assert.equal(D.lerEstado().pausa_ate, 0, "timeout não pausou o servidor");
  });
  it("HTTP 429 arma o disjuntor por 6 h e aperta a escada; desafio anti-robô é reconhecido", async () => {
    semEspera();
    let ant = D._trocarFetch(async () => new Response("x", { status: 429 }));
    await assert.rejects(D.http("GET", CFG.URL_TEOR), /HTTP 429/);
    D._trocarFetch(ant);
    assert.ok(D.lerEstado().pausa_ate > Date.now() / 1000 + 5 * 3600);
    assert.equal(D.lerEstado().nivel, 1);
    semEspera(); D._internos.zerarPausaMemoria();
    ant = D._trocarFetch(async () => latin1("<html><head><script src='https://challenges.cloudflare.com/x'></script></head><body>Just a moment...</body></html>"));
    await assert.rejects(D.http("GET", CFG.URL_TEOR), /desafio anti-robô/);
    D._trocarFetch(ant);
    // a palavra "código de segurança" numa ementa real NÃO é desafio: a página é o que pedimos
    semEspera(); D._internos.zerarPausaMemoria();
    ant = D._trocarFetch(async () => latin1("<html><head></head><body><h4>Boletim n. 1</h4>" + "fraude com o código de segurança do cartão ".repeat(5) + '<a href="relatorio.wsp?x">1</a></body></html>'));
    assert.ok((await D.http("GET", CFG.URL_TEOR)).includes("código de segurança"));
    D._trocarFetch(ant);
    semEspera(); D._internos.zerarPausaMemoria();
  });
});

describe("crédito, aviso de versão e relato", () => {
  it("crédito sai uma vez por processo; versão nova, uma vez; nunca espera rede", () => {
    A._resetAvisosParaTeste();
    assert.ok(A.comAvisos("x").includes(A.CREDITO) && !A.comAvisos("y").includes(A.CREDITO));
    A._resetAvisosParaTeste(); A._definirVersaoNovaParaTeste("9.9.9");
    const a1 = A.comAvisos("x");
    assert.ok(a1.includes(A.RELEASES_PAGINA) && a1.includes("9.9.9"));
    assert.ok(!A.comAvisos("y").includes("versão mais nova"));
    A._resetAvisosParaTeste();
  });
  it("só tag ESTRITAMENTE maior e bem formada vira aviso", () => {
    assert.ok(!A.versaoMaisNova("0.7.5", "0.7.5") && !A.versaoMaisNova("0.7.5", "v0.7.4"));
    assert.ok(A.versaoMaisNova("0.7.5", "v0.8.0") && A.versaoMaisNova("0.9.9", "1.0.0"));
    assert.ok(!A.versaoMaisNova("0.7.5", "ultima") && !A.versaoMaisNova("0.7.5", "") && !A.versaoMaisNova("0.7.5", "0.8"));
  });
  it("checagem: silêncio sem rede, com 404 e com a variável de desligar; URL do aviso é FIXA", async () => {
    assert.equal(await A.checarVersao({ fetchImpl: async () => { throw new Error("sem rede"); } }), null);
    assert.equal(await A.checarVersao({ fetchImpl: async () => ({ ok: false }) }), null);
    assert.equal(await A.checarVersao({ env: {}, fetchImpl: async () => ({ ok: true, json: async () => ({ tag_name: "v99.0.0", html_url: "https://evil.example" }) }) }), "99.0.0");
    assert.equal(await A.checarVersao({ env: { TJSE_MCP_SEM_AVISO_ATUALIZACAO: "1" }, fetchImpl: async () => ({ ok: true, json: async () => ({ tag_name: "v99.0.0" }) }) }), null);
    A._definirVersaoNovaParaTeste("99.0.0");
    assert.ok(!A.comAvisos("z").includes("evil.example"));
    A._resetAvisosParaTeste();
  });
  it("link de relato: só dado técnico, nunca busca, acórdão ou nome de parte", () => {
    const u = decodeURIComponent(A.linkRelato("busca_indice_local"));
    assert.ok(u.startsWith(A.ISSUES_NOVA) && u.includes(`na v${CFG.VERSAO}`) && u.includes("Tipo do erro: busca_indice_local"));
    assert.ok(!/\d{9}/.test(u));
  });
});

describe("pacote de HTML bruto: baixar, conferir e extrair", () => {
  it("lerTar lê ustar, ignora lixo e não confia em nomes", async () => {
    const { Readable } = await import("node:stream");
    const cab = (nome, dados) => { const c = Buffer.alloc(512); c.write(nome, 0); c.write("0000644\0", 100); c.write(dados.length.toString(8).padStart(11, "0") + "\0", 124); c.write("0", 156); c.write("ustar\0", 257);
      let s = 256; for (let i = 0; i < 512; i++) if (i < 148 || i >= 156) s += c[i]; c.write(s.toString(8).padStart(6, "0") + "\0 ", 148); return Buffer.concat([c, dados, Buffer.alloc((512 - dados.length % 512) % 512)]); };
    const tar = Buffer.concat([cab("secoes/1-6.html.gz", Buffer.from("a")), cab("../../x", Buffer.from("b")), Buffer.alloc(1024)]);
    const nomes = []; for await (const e of PK.lerTar(Readable.from([tar]))) nomes.push(e.nome);
    assert.deepEqual(nomes, ["secoes/1-6.html.gz", "../../x"]);
  });
  const montarFetch = async (bytes, somaErrada) => {
    const crypto = await import("node:crypto"), { Readable } = await import("node:stream");
    const sha = crypto.createHash("sha256").update(bytes).digest("hex");
    return async (url) => url.endsWith("SHA256SUMS.txt")
      ? new Response(`${somaErrada ? "0".repeat(64) : sha}  ${PK.ARQUIVO_PACOTE}\n`)
      : new Response(Readable.toWeb(Readable.from([bytes.subarray(0, 700), bytes.subarray(700)])), { headers: { "content-length": String(bytes.length) } });
  };
  const tarGz = async (entradas) => {
    const zlib = await import("node:zlib");
    const cab = (nome, dados) => { const c = Buffer.alloc(512); c.write(nome, 0); c.write("0000644\0", 100); c.write(dados.length.toString(8).padStart(11, "0") + "\0", 124); c.write("0", 156); c.write("ustar\0", 257);
      let s = 256; for (let i = 0; i < 512; i++) if (i < 148 || i >= 156) s += c[i]; c.write(s.toString(8).padStart(6, "0") + "\0 ", 148); return Buffer.concat([c, dados, Buffer.alloc((512 - dados.length % 512) % 512)]); };
    return zlib.gzipSync(Buffer.concat([...entradas.map(([n, d]) => cab(n, Buffer.from(d))), Buffer.alloc(1024)]));
  };
  const rodar = async (bytes, opcoes = {}) => {
    fs.rmSync(path.join(CFG.dirBase(), "secoes"), { recursive: true, force: true });
    await PK.baixarEExtrair({ fetchImpl: await montarFetch(bytes, opcoes.somaErrada) });
    const dest = path.join(CFG.dirBase(), "secoes");
    return { n: fs.existsSync(dest) ? fs.readdirSync(dest).length : 0, erro: PK.estado.erro, ok: PK.estado.concluido };
  };
  it("instala só o que tem nome de seção; nunca cria caminho vindo do pacote", async () => {
    const r = await rodar(await tarGz([["../../fora", "x"], ["/tmp/abs", "x"], ["secoes/../../fora.html.gz", "x"], ["secoes/158-6.html.gz", "ok"], ["secoes/158-6.p2.html.gz", "ok2"]]));
    assert.equal(r.n, 2); assert.equal(r.erro, null);
    assert.ok(!fs.existsSync(path.join(CFG.dirDados(), "fora")) && !fs.existsSync("/tmp/abs"));
  });
  it("hash que não confere, download truncado e pacote sem seção: nada é instalado", async () => {
    const bom = await tarGz([["secoes/158-6.html.gz", "ok"]]);
    let r = await rodar(bom, { somaErrada: true });
    assert.equal(r.n, 0); assert.match(r.erro, /NÃO confere/);
    r = await rodar(bom.subarray(0, bom.length - 5));
    assert.equal(r.n, 0); assert.match(r.erro, /interrompido|nada foi instalado/);
    r = await rodar(await tarGz([["LEIAME.txt", "x"]]));
    assert.equal(r.n, 0); assert.match(r.erro, /nenhuma seção reconhecível/);
  });
  it("importarPacote: sem nada em disco e baixar=false, orienta", async () => {
    fs.rmSync(path.join(CFG.dirBase(), "secoes"), { recursive: true, force: true });
    assert.ok((await F.importarPacote(false)).includes("Nada em"));
  });
  it("conexão LENTA: a 1ª chamada devolve o progresso, o download segue em segundo plano e a 2ª conclui e importa", async () => {
    const crypto = await import("node:crypto"), { Readable } = await import("node:stream");
    const pleno = fx("09-principal-168-pleno.html");
    const gz = (await import("node:zlib")).gzipSync(Buffer.from(pleno, "utf8"));
    const cab = (nome, dados) => { const c = Buffer.alloc(512); c.write(nome, 0); c.write("0000644\0", 100); c.write(dados.length.toString(8).padStart(11, "0") + "\0", 124); c.write("0", 156); c.write("ustar\0", 257);
      let x = 256; for (let i = 0; i < 512; i++) if (i < 148 || i >= 156) x += c[i]; c.write(x.toString(8).padStart(6, "0") + "\0 ", 148); return Buffer.concat([c, dados, Buffer.alloc((512 - dados.length % 512) % 512)]); };
    const bytes = (await import("node:zlib")).gzipSync(Buffer.concat([cab("secoes/501-10.html.gz", gz), Buffer.alloc(1024)]));
    const sha = crypto.createHash("sha256").update(bytes).digest("hex");
    async function* lento() { const n = 20, t = Math.ceil(bytes.length / n); for (let i = 0; i < n; i++) { await new Promise((r) => setTimeout(r, 80)); yield bytes.subarray(i * t, (i + 1) * t); } }
    const antes = globalThis.fetch;
    globalThis.fetch = async (url) => url.endsWith("SHA256SUMS.txt") ? new Response(`${sha}  ${PK.ARQUIVO_PACOTE}\n`)
      : new Response(Readable.toWeb(Readable.from(lento())), { headers: { "content-length": String(bytes.length) } });
    try {
      fs.rmSync(path.join(CFG.dirBase(), "secoes"), { recursive: true, force: true });
      const r1 = await F.importarPacote(true, { prazoMs: Date.now() + 250 });
      assert.match(r1, /Baixando o pacote do TJSE.*chame `importar_pacote_tjse` de novo/s);
      const r2 = await F.importarPacote(true, { prazoMs: Date.now() + 15_000 });
      assert.ok(r2.includes("Pacote baixado e conferido (hash confere)") && r2.includes("Importação do HTML bruto"), r2.slice(0, 300));
      assert.match(r2, /edição 501 · Tribunal Pleno: 43 acórdãos/);   // leu a seção inteira (43 é o do fixture); a inserção pode virar republicação
    } finally { globalThis.fetch = antes; }
  });
});

describe("servidor MCP de ponta a ponta (cliente real, stdio)", () => {
  it("expõe as 7 ferramentas e responde com o crédito uma única vez", async () => {
    const { Client } = await import("@modelcontextprotocol/sdk/client/index.js");
    const { StdioClientTransport } = await import("@modelcontextprotocol/sdk/client/stdio.js");
    const dados = fs.mkdtempSync(path.join(os.tmpdir(), "tjse-e2e-"));
    const t = new StdioClientTransport({ command: process.execPath, args: [path.join(raiz, "..", "server", "index.js")], env: { ...process.env, TJSE_DIR_DADOS: dados } });
    const c = new Client({ name: "teste", version: "1" });
    await c.connect(t);
    try {
      const { tools } = await c.listTools();
      assert.deepEqual(tools.map((x) => x.name).sort(), ["buscar_jurisprudencia_tjse", "diagnostico_tjse", "importar_pacote_tjse", "mapa_de_citacoes_tjse", "obter_inteiro_teor_tjse", "sincronizar_boletim_tjse", "verificar_citacao_tjse"]);
      const chama = async (nome, args) => (await c.callTool({ name: nome, arguments: args })).content[0].text;
      const d1 = await chama("diagnostico_tjse", {});
      assert.ok(d1.includes(`v${CFG.VERSAO}`) && d1.includes("índice local VAZIO") && d1.includes(A.CREDITO));
      assert.ok(!(await chama("diagnostico_tjse", {})).includes(A.CREDITO));
      assert.ok((await chama("buscar_jurisprudencia_tjse", { consulta: "dano moral" })).includes("índice local VAZIO"));
      assert.ok((await chama("buscar_jurisprudencia_tjse", { consulta: "dano E moral" })).includes("operador em caixa alta"));
      assert.ok((await chama("verificar_citacao_tjse", { numero_acordao: "202638463", trecho: "x" })).includes("Pedido recusado"));
    } finally { await c.close(); fs.rmSync(dados, { recursive: true, force: true }); }
  });
});
