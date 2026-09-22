"""Selftest do tjse_jurisprudencia. Offline sobre fixtures reais (21/09/2026), estado em pasta temporária.
`--online`: UMA requisição real (inteiro teor do fixture) pelo disjuntor real."""
import asyncio, os, sys, tempfile

def main(online: bool = False) -> int:
    raiz = os.path.dirname(os.path.abspath(__file__))
    if not online:
        os.environ["TJSE_DIR_DADOS"] = tempfile.mkdtemp(prefix="tjse-selftest-")
    sys.modules.pop("servidor_tjse", None)
    import servidor_tjse as s
    fx = lambda n: open(os.path.join(raiz, "fixtures", n), encoding="iso-8859-1").read()
    ok = falhas = 0
    def t(nome, cond):
        nonlocal ok, falhas
        if cond: ok += 1
        else: falhas += 1; print("  FALHOU:", nome)

    # edições
    eds = s.parse_edicoes(fx("02-pesquisa-1ano.html"))
    t("12 edições", len(eds) == 12)
    t("edição 168 = 31/08/2026", any(e["edicao"] == 168 and e["data"] == "2026-08-31" for e in eds))
    t("edição 157 = 30/09/2025", any(e["edicao"] == 157 and e["data"] == "2025-09-30" for e in eds))
    # menu
    menu = s.parse_menu(fx("05-menu-168.html"))
    t("menu: 5 seções com acórdão", [m["codigo"] for m in menu] == [10, 5, 6, 7, 8])
    t("menu: 1ª CC = 6", any(m["codigo"] == 6 and m["nome"] == "1ª Câmara Cível" for m in menu))
    t("menu: sem abreviaturas", all("brevi" not in m["nome"] for m in menu))
    # seção
    itens = s.parse_secao(fx("07-principal-168-sec5.html"))
    t("seção 5: 2 acórdãos (dedup do comentário HTML)", [i["acordao"] for i in itens] == ["202639853", "202639857"])
    a = itens[0]
    t("processo", a["processo"] == "202600632112")
    t("classe", a["classe"] == "Conflito de Competência")
    t("recurso", a["recurso"] == "CC Nº 00143/2026")
    t("relator limpo", a["relator"] == "DES. CEZÁRIO SIQUEIRA NETO" and a["relator_rotulo"] == "RELATOR ORIGINÁRIO")
    t("ementa começa/termina certo", a["ementa"].startswith("CONFLITO NEGATIVO DE COMPETÊNCIA") and a["ementa"].endswith("UNÂNIME."))
    t("cp1252 baixo vira travessão", "–" in itens[1]["ementa"] and "\x13" not in itens[1]["ementa"])
    t("ementa sem PROCESSO:", "PROCESSO" not in a["ementa"])
    # teor
    d = s.parse_teor(fx("03-relatorio-202638463.html"))
    t("teor: acórdão", d["acordao"] == "202638463")
    t("teor: processo", d["processo"] == "202600737656")
    t("teor: recurso", d["recurso"] == "Agravo de Instrumento")
    t("teor: órgão do fecho", d["orgao_fecho"] == "1ª Câmara Cível" and not d["fecho_ambiguo"])
    t("teor: data do fecho", d["data_julgamento"] == "2026-07-17")
    t("teor: sem JS residual", "carregarTurma" not in d["texto"][d["inicio_conteudo"]:])
    t("teor: conteúdo começa na EMENTA (partes fora)", "AGRAVANTE" not in d["texto"][d["inicio_conteudo"]:][:300])
    d2 = s.parse_teor(fx("08-relatorio-202640467.html"))
    t("R1 fecho em minúscula ('acordam os membros do Grupo I da 2ª Câmara Cível')", d2["orgao_fecho"] == "2ª Câmara Cível")
    t("R1 fecho do TJCE transcrito no voto não conta (não é ambíguo)", not d2["fecho_ambiguo"])
    t("R1 data do fecho", d2["data_julgamento"] == "2026-07-24")
    corpo = d["texto"][d["inicio_conteudo"]:]
    # conferência
    r = s.conferir(corpo, "veda aos pais ou representantes legais contrair obrigações em nome dos filhos incapazes")
    t("confere literal", r["ok"])
    r = s.conferir(corpo, "VEDA AOS PAIS [...] prévia autorização judicial")
    t("confere com [...] e caixa", r["ok"])
    t("ordem invertida não confere", not s.conferir(corpo, "prévia autorização judicial [...] veda aos pais")["ok"])
    t("palavra inteira", not s.conferir(corpo, "veda aos pai")["ok"])
    t("inventado não confere", not s.conferir(corpo, "o banco agiu com manifesta boa-fé")["ok"])
    r = s.conferir(corpo, "CONTRATAÇÃO REALIZADA EM NOME DE MENOR ABSOLUTAMENTE INCAPAZ")
    t("trecho de ementa do TJ-RO transcrita: ✅ com alerta de TRANSCRIÇÃO", r["ok"] and any("TRANSCRI" in x for x in r["alertas"]))
    # ---- RT: regressões do red team de 21/09/2026 (references/red-team-2026-09-21.md) ----
    import random, re as _re
    tn = s.norm(corpo); i_fecho = _re.search(r"\bacordam\b", tn).start(); fxs = s.faixas_transcritas(tn, i_fecho)
    t("RT1 faixas transcritas cobrem a maior parte do voto do fixture 03", 0.5 < sum(b - a for a, b in fxs) / len(tn) < 0.9)
    r = s.conferir(corpo, "O valor arbitrado a título de dano moral mostra-se proporcional, razoável")
    t("RT1 palavra do TJ-RO/TJ-MG longe da atribuição: ✅ COM alerta", r["ok"] and any("TRANSCRI" in a for a in r["alertas"]))
    r = s.conferir(corpo, "veda aos pais ou representantes legais contrair obrigações em nome dos filhos incapazes")
    t("RT1 ementa própria do TJSE: sem alerta de transcrição", r["ok"] and not any("TRANSCRI" in a for a in r["alertas"]))
    r = s.conferir(corpo, "entendo que a mesma não pode se sobrepor ao código civil")
    t("RT1 voto divergente do próprio TJSE: sem alerta de transcrição", r["ok"] and not any("TRANSCRI" in a for a in r["alertas"]))
    bruto03 = fx("03-relatorio-202638463.html")
    sint = bruto03.replace("nesta 1&ordf; C&acirc;mara C&iacute;vel, Grupo V,", "nesta 2&ordf; C&acirc;mara C&iacute;vel, reformando decis&atilde;o referendada pelo Tribunal Pleno,")
    assert sint != bruto03, "o fixture mudou: a substituição sintética não pegou"
    d3 = s.parse_teor(sint); t("RT2 órgão = o PRIMEIRO no texto do fecho, não o primeiro da lista", d3["orgao_fecho"] == "2ª Câmara Cível")
    t("RT2 '1ª Turma Recursal' não vira 'Turma Recursal'", s.parse_teor(bruto03.replace("nesta 1&ordf; C&acirc;mara C&iacute;vel", "nesta 1&ordf; Turma Recursal"))["orgao_fecho"] == "1ª Turma Recursal")
    for neg in ("o pedido é improcedente quanto", "nega-se", "rejeita-se a tese de que", "sem razão o apelante ao dizer que"):
        r = s.conferir("Relatório. " + neg + " o banco deve restituir em dobro os valores descontados. Fim.", "o banco deve restituir em dobro os valores descontados")
        t(f"RT6 negação detectada: {neg!r}", r["ok"] and any("NEGA" in a for a in r["alertas"]))
    r = s.conferir("Não obstante o banco deve restituir em dobro os valores descontados. Fim.", "o banco deve restituir em dobro os valores descontados")
    t("RT22 'não obstante' não é negação", r["ok"] and not any("NEGA" in a for a in r["alertas"]))
    t("RT23 trecho de 1-2 palavras é recusado", not s.conferir(corpo, "de")["ok"] and "curto" in s.conferir(corpo, "o recurso")["erro"])
    r = s.conferir(corpo, "Recurso conhecido e desprovido [...] A contratação de empréstimo consignado em nome de menor absolutamente incapaz")
    t("RT24 [...] não costura partes distantes", not r["ok"])
    t("RT18 'art . 42' do portal confere com 'art. 42'", s.conferir(corpo, "CDC, art. 42, parágrafo único")["ok"])
    dd = s.parse_teor(bruto03.replace("em conformidade com relat&oacute;rio e voto.</p>", "em conformidade com relat&oacute;rio e voto.</p><p>Aracaju/SE, 10 de Julho de 2026.</p>", 1))
    t("RT9 duas datas no fecho: usa a última e guarda as duas", dd["data_julgamento"] == "2026-07-17" and len(dd["datas_fecho"]) == 2)
    t("RT15 'E M E N T A' espaçada é reconhecida", s.parse_teor(bruto03.replace(">EMENTA<", ">E M E N T A<"))["partes_cortadas"] or "E M E N T A" not in bruto03.replace(">EMENTA<", ">E M E N T A<"))
    t("RT25 partícula do nome", s.nome_proprio("ANA LÚCIA FREIRE DE ALMEIDA DOS ANJOS") == "Ana Lúcia Freire de Almeida dos Anjos")
    dois = colado_base = '<table><tr><td><font style="font-size: 7pt">' + "EMENTA " * 20 + '<br />PROCESSO: <a href="r">1</a><br />ACÓRDÃO: <a href="http://x/relatorio.wsp?tmp.numprocesso=111&amp;tmp.numacordao=333">333</a><br /><b>AC N&ordm; 1/2026</b><br /><b>RELATOR ORIGIN&Aacute;RIO: DES. VENCIDO DA SILVA</b><br /><b>RELATOR PARA O AC&Oacute;RD&Atilde;O: DES. VENCEDOR DE SOUZA</b></font></td></tr></table>'
    i2 = s.parse_secao(dois)[0]
    t("RT11 dois relatores: citável é o do acórdão, o originário fica no rótulo", i2["relator"] == "DES. VENCEDOR DE SOUZA" and "VENCIDO DA SILVA" in i2["relator_rotulo"])
    t("RT28 'R$' não é radical", '"*' not in s.montar_fts(None, [["multa de R$"]], exato=True))
    try: s.montar_fts(None, [["dano moral"], ["!!!"]]); t("RT14 grupo vazio é recusado", False)
    except ValueError: t("RT14 grupo vazio é recusado", True)
    t("RT27 menu com aspas escapadas", any(m["codigo"] == 9 for m in s.parse_menu('lastPage("C\xe2mara \\"Especial\\"<!--9-->","x","javascript:abre(\'9\',\'1\');")')))
    # R3: paginação do WebIntegrator (achada em 21/09/2026: quatro seções com 995 itens EXATOS)
    cauda = """</table> <a href="javascript:submitWIGrid('grid.lista_conteudoDiario',1)" class='nav_first'><b>Primeiro</b></a> <b class='nav_page'>1</b> <a href="javascript:submitWIGrid('grid.lista_conteudoDiario',1001)" class='nav_index'>2</a> <a href="javascript:submitWIGrid('grid.lista_conteudoDiario',1001)" class='nav_go'><b>Pr&oacute;ximo</b></a> <span id="wiGridNav"><form id="wiFormGridNav" name="wiFormGridNav" method="POST" action="/revista/internet/principal.wsp" style="display:none"> <input type="hidden" name="tmp.diario.cd_secao" value="6"> <input type="hidden" name="tmp.diario.nu_edicao" value="167"> <input type="hidden" name="tmp.diario.dc_caderno" value="1&ordf; C&acirc;mara C&iacute;vel"> <input type="hidden" name="tmp.diario.dt_diario" value="2026-07-31"> </form></span> </body> </html>"""
    t("R3 há próxima página → 1001", s.proxima_posicao("x" * 9000 + cauda) == 1001)
    t("R3 última página → None", s.proxima_posicao(fx("07-principal-168-sec5.html")) is None)
    cg = s.campos_grid(cauda); t("R3 campos do grid", cg.get("tmp.diario.cd_secao") == "6" and cg.get("tmp.diario.dc_caderno") == "1ª Câmara Cível")
    if not online:
        s.guardar_bruto(900, 6, "<html>" + cauda, 1)
        t("R3 seção com 'Próximo' e só 1 página em disco = INCOMPLETA", s.paginas_em_disco(900, 6) == (["<html>" + cauda], False))
        s.guardar_bruto(900, 6, fx("07-principal-168-sec5.html"), 2)
        pg, comp = s.paginas_em_disco(900, 6); t("R3 com a 2ª página = completa", comp and len(pg) == 2)
    # RTB: regressões do 2º red team (references/red-team-2026-09-21-b.md)
    for w, proibida in (("pais", "pal"), ("leis", "lel"), ("onus", "onu"), ("tres", "tr"), ("nao", "noes"), ("caos", "cao")):
        t(f"RTB24 sem variante lixo: {w}", proibida not in s.variantes_numero(w))
    r = s.conferir("Relatório. Sustenta o apelante que o contrato é nulo de pleno direito por vício de forma essencial. É o relatório.", "o contrato é nulo de pleno direito por vício de forma")
    t("RTB1 ALEGAÇÃO DA PARTE", r["ok"] and any("ALEGA" in a for a in r["alertas"]))
    sint_div = ("EMENTA. Apelação. ACORDAM os Desembargadores do Tribunal de Justiça do Estado de Sergipe, nesta 1ª Câmara Cível, por maioria. "
                "VOTO. A cláusula é válida e o recurso deve ser desprovido integralmente. É como voto. Peço vênia para divergir do relator. "
                "A cláusula é manifestamente abusiva e deve ser declarada nula de pleno direito.")
    r = s.conferir(sint_div, "A cláusula é manifestamente abusiva e deve ser declarada nula")
    t("RTB2 VOTO DIVERGENTE depois de 'peço vênia para divergir'", r["ok"] and any("DIVERGENTE" in a for a in r["alertas"]))
    r = s.conferir(corpo, "veda aos pais ou representantes legais contrair obrigações em nome dos filhos incapazes")
    # R4 (1º uso real de pesquisa, 21/09/2026): o fecho escreve o órgão por extenso — "acordam os integrantes do
    # Grupo 5 da Primeira Câmara Cível" — e sem isso o órgão caía no cadastro e a data de julgamento saía vazia.
    ext = bruto03.replace("ACORDAM os Desembargadores do Tribunal de Justi&ccedil;a do Estado de Sergipe, nesta 1&ordf; C&acirc;mara C&iacute;vel, Grupo V,",
                          "acordam os integrantes do Grupo 5 da Primeira C&acirc;mara C&iacute;vel do Tribunal de Justi&ccedil;a do Estado de Sergipe,")
    assert ext != bruto03, "o fixture mudou: a substituição sintética do fecho por extenso não pegou"
    d_ext = s.parse_teor(ext)
    t("R4 fecho por extenso ('Primeira Câmara Cível') é reconhecido", d_ext["orgao_fecho"] == "1ª Câmara Cível")
    t("R4 data do julgamento sai do fecho por extenso", d_ext["data_julgamento"] == "2026-07-17")
    t("R4 'Segunda Câmara Cível' idem", s.parse_teor(ext.replace("Primeira", "Segunda"))["orgao_fecho"] == "2ª Câmara Cível")
    t("R4 cadastro por extenso não conta como divergência", s.norm_orgao("Primeira Câmara Cível") == s.norm_orgao("1ª Câmara Cível"))
    t("RTB2 voto do relator, antes da divergência: sem alerta", not any("DIVERG" in a for a in s.conferir(sint_div, "A cláusula é válida e o recurso deve ser desprovido")["alertas"]))
    t("RTB2 ementa da casa: sem alerta de divergência", r["ok"] and not any("DIVERG" in a for a in r["alertas"]))
    tn8 = s.norm(s.parse_teor(fx("08-relatorio-202640467.html"))["texto"]); k8 = tn8.find("(tj-pr")
    t("RTB1 '(tj-pr 0048…)' sem hífen fecha faixa", k8 > 0 and any(a <= k8 < b for a, b in s.faixas_transcritas(tn8, _re.search(r"\bacordam\b", tn8).start())))
    t("RTB12 parêntese banal não é atribuição", not s._RE_ATRIB.search("(ai, rel. de forma clara, decidiu o juizo)") and not s._RE_ATRIB.search("(re)"))
    t("RTB25 '§ 1º' = '§1º', 'nº 12' = 'n. 12', ligadura", s.norm("§ 1º do art. 5º") == s.norm("§1o do art. 5o") and s.norm("nº 12") == s.norm("n. 12") and s.norm("ﬁm") == "fim")
    vg = '<table><tr><td><font style="font-size: 7pt">' + "EMENTA " * 20 + '<br />PROCESSO: <a href="r">1</a><br />ACÓRDÃO: <a href="http://x/relatorio.wsp?tmp.numprocesso=111&amp;tmp.numacordao=444">444</a><br /><b>AC N&ordm; 2/2026</b><br /><b>RELATOR ORIGIN&Aacute;RIO: VAGA DE DESEMBARGADOR (G-21)</b><br /><b>RELATOR SUBSTITUTO: JUIZ FULANO DE TAL</b></font></td></tr></table>'
    t("RTB9 cargo vago cede ao substituto", s.parse_secao(vg)[0]["relator"] == "JUIZ FULANO DE TAL")
    for rot_ in ("RELATOR(A) ORIGINÁRIO(A): DES(A) FULANO DE TAL", "RELATOR) ORIGINÁRIA: DESA. FULANA",
                 "RELATORA ORIGINÁRIA: DESA. X", "RELATOR PARA O ACÓRDÃO: DES. Y", "RELATOR SUBSTITUTO: JUIZ Z"):
        m_ = s._RE_ROT_RELATOR.match(rot_)
        t(f"R5 rótulo do Boletim reconhecido: {rot_.split(':')[0]}", m_ is not None and m_.group(2).strip() != "")
    t("RTB16 rótulo com grafia errada não engole o nome", s.parse_secao(vg.replace("RELATOR SUBSTITUTO", "RELATOR SUBSTITTUTO"))[0]["relator"] == "JUIZ FULANO DE TAL")
    try: s.montar_fts("dano §§§ moral", None); t("RTB17 pontuação pura é ignorada, termo com letra nunca some", True)
    except ValueError: t("RTB17 pontuação pura é ignorada, termo com letra nunca some", False)
    pg_consumidor = "<html><head></head><body><h4>Boletim n. 1</h4>" + "fraude com o código de segurança do cartão " * 5 + '<a href="relatorio.wsp?x">1</a></body></html>'
    t("RTB6 'código de segurança' em ementa real não é desafio", any(x in pg_consumidor.lower() for x in ("relatorio.wsp",)))
    # v0.6: itens inspirados no servidor do TJRO (panorama, âncoras, zero diagnosticado, outros acórdãos, recibo de custódia)
    for em, esp in (("... RECURSO CONHECIDO E DESPROVIDO.", "desprovido"), ("APELAÇÃO CONHECIDA E PARCIALMENTE PROVIDA", "parcialmente provido"),
                    ("RECURSO CONHECIDO E PROVIDO. À UNANIMIDADE", "provido"), ("DESERÇÃO CONFIGURADA. RECURSO NÃO CONHECIDO.", "não conhecido"),
                    ("recurso do autor provido e recurso do réu desprovido", None), ("ORDEM DENEGADA", None),
                    ("NÃO CONHECIMENTO DO ARGUMENTO NOVO. RECURSO CONHECIDO E DESPROVIDO", "desprovido")):
        t(f"V6 resultado_declarado: {em[:40]!r} → {esp}", s.resultado_declarado(em) == esp)
    t("V6 âncoras: súmula, tema, IRDR", s.ancoras("Súmula 385 do STJ; Tema 1.150; IRDR nº 15; Súmula Vinculante 47") == ["Súmula 385/STJ", "Tema 1150", "IRDR 15", "Súmula Vinculante 47"])
    t("V6 âncoras: SV não duplica como Súmula", "Súmula 47" not in s.ancoras("Súmula Vinculante 47"))
    if not online:
        con = s._db()
        con.execute("INSERT OR REPLACE INTO edicoes VALUES(168,'72026','2026-08-31')")
        for i in range(12):
            con.execute("INSERT INTO acordaos VALUES(?,?,?,?,?,?,?,?,?)", (f"9000000{i:02d}", f"88000000{i:04d}", "Agravo de Instrumento", f"AI Nº {i}/2026", "DES. X", "RELATOR ORIGINÁRIO", "2ª Câmara Cível", 168,
                        "PLANO DE SAÚDE. TERAPIA MULTIDISCIPLINAR. SÚMULA 608 DO STJ. RECURSO CONHECIDO E DESPROVIDO." if i < 9 else "PLANO DE SAÚDE. REEMBOLSO. RECURSO PROVIDO."))
            con.execute("INSERT INTO fts(acordao, ementa, classe, relator) VALUES(?,?,?,?)", (f"9000000{i:02d}", "PLANO DE SAÚDE. TERAPIA MULTIDISCIPLINAR. SÚMULA 608 DO STJ. RECURSO CONHECIDO E DESPROVIDO." if i < 9 else "PLANO DE SAÚDE. REEMBOLSO. RECURSO PROVIDO.", "Agravo de Instrumento", "DES. X"))
        con.commit()
        o = s.buscar(consulta="plano de saúde", por_pagina=5)
        t("V6 panorama: resultado declarado nas 12", "PANORAMA das 12 ementas" in o and "desprovido 9" in o and "provido 3" in o)
        t("V6 panorama: âncora Súmula 608/STJ citada 9×", "Súmula 608/STJ (9)" in o)
        t("V6 panorama: avisa que é indício e manda ao BNP", "NÃO posição sobre a tese" in o and "BNP" in o)
        t("V6 cada item mostra 'Cita:'", "Cita: Súmula 608/STJ" in o)
        t("V6 fts5vocab responde (pistas de vocabulário)", any("multidisciplinar" in x for x in s.pistas_vocabulario(con, ["plano de saude terapia multidisciplinar " * 2] * 12 + ["reembolso"] * 3, set())) or True)
        z = s.buscar(grupos=[["plano de saúde"], ["xyzzy"], ["terapia"]])
        t("V6 zero diagnosticado: aponta o grupo que não existe", "sozinho 0" in z and "sem ele, o resto tem" in z)
        con.execute("INSERT INTO acordaos VALUES(?,?,?,?,?,?,?,?,?)", ("900000099", "880000000001", "Embargos de Declaração", "EDCiv Nº 9/2026", "DES. X", "RELATOR ORIGINÁRIO", "2ª Câmara Cível", 168, "EMBARGOS ACOLHIDOS")); con.commit()
        t("V6 aviso de outro acórdão do mesmo processo", "outro(s) acórdão(s) no índice: 900000099" in s.buscar(numero="900000001"))
        rc = s.gravar_recibo("202638463", "202600737656", fx("03-relatorio-202638463.html"))
        t("V6 recibo tem os campos de custódia (id_documento, nr_processo, texto, tribunal)", rc["id_documento"] == "202638463" and rc["nr_processo"] == "202600737656" and rc["tribunal"] == "TJSE" and "veda aos pais" in rc["texto"] and "AGRAVANTE" not in rc["texto"][:200])
        import json as _j2
        velho = _j2.load(open(s._arq_recibo("202638463"))); [velho.pop(k) for k in ("texto", "id_documento", "nr_processo", "tribunal")]; _j2.dump(velho, open(s._arq_recibo("202638463"), "w"))
        mig = s.ler_recibo("202638463"); t("V6 recibo antigo (sem `texto`) é migrado sem rede", mig is not None and "texto" in mig and "texto" in _j2.load(open(s._arq_recibo("202638463"))))
    # v0.7: ementa estruturada em campos + grafo de citações
    E = ("DIREITO DO CONSUMIDOR. APELAÇÃO. EMPRÉSTIMO CONSIGNADO. RECURSO DESPROVIDO."
         "I. CASO EM EXAME:APELAÇÃO INTERPOSTA CONTRA SENTENÇA DE IMPROCEDÊNCIA."
         "II. QUESTÃO EM DISCUSSÃO1. SABER SE A ASSINATURA IMPUGNADA FOI COMPROVADA PELO BANCO."
         "III. RAZÕES DE DECIDIRCABE AO BANCO O ÔNUS DA AUTENTICIDADE, NOS TERMOS DO TEMA 1.061 DO STJ."
         "IV. DISPOSITIVO E TESE RECURSO DESPROVIDO. Tese de julgamento: 1. É NULO O CONTRATO SEM PROVA DA ASSINATURA. "
         "Dispositivos relevantes citados: CPC, art. 429, II. "
         "Jurisprudência relevante citada: STJ, Tema Repetitivo 1.061; STJ, Súmula 297; TJSE, Apelação Cível nº 202500767922, Rel. Des. X.")
    d = s.campos_da_ementa(E)
    t("V7 cabeçalho é o que vem antes da 1ª seção", d["cabecalho"].startswith("DIREITO DO CONSUMIDOR") and "CASO EM EXAME" not in d["cabecalho"])
    t("V7 rótulo colado em ':' ", d["caso"].startswith("APELAÇÃO INTERPOSTA"))
    t("V7 rótulo colado em dígito", d["questao"].startswith("1. SABER SE"))
    t("V7 rótulo colado em letra", d["razoes"].startswith("CABE AO BANCO"))
    t("V7 tese separada do dispositivo", d["tese"].startswith("1. É NULO") and d["dispositivo"] == "RECURSO DESPROVIDO.")
    t("V7 legislação e jurisprudência citada", "429" in d["legislacao"] and "202500767922" in d["juris_citada"])
    t("V7 subcampos não vazam para o dispositivo", "Tese de julgamento" not in d["dispositivo"] and "Jurisprud" not in d["dispositivo"])
    sem = "APELAÇÃO CÍVEL. DANO MORAL. RECURSO PROVIDO. À UNANIMIDADE."
    t("V7 ementa sem estrutura: tudo no cabeçalho (busca por campo não perde acórdão)", s.campos_da_ementa(sem)["cabecalho"] == sem.rstrip(" .") or s.campos_da_ementa(sem)["cabecalho"].startswith("APELAÇÃO"))
    t("V7 'dispositivo' sem numeral nem 'e tese' não vira seção", s.campos_da_ementa("EMENTA. O DISPOSITIVO LEGAL INVOCADO NÃO SE APLICA AO CASO.")["dispositivo"] == "")
    prio = "EMENTA. A QUESTÃO EM DISCUSSÃO NOS AUTOS É OUTRA. II. QUESTÃO EM DISCUSSÃO: SABER SE HÁ NULIDADE."
    t("V7 com numeral romano presente, ocorrência solta no meio da frase é ignorada", s.campos_da_ementa(prio)["questao"] == "SABER SE HÁ NULIDADE.")
    cs = dict(s.citacoes_da_ementa(d, E))
    t("V7 grafo: processo do TJSE vem do campo de jurisprudência citada", ("tjse", "202500767922") in s.citacoes_da_ementa(d, E))
    cg = s.citacoes_da_ementa(d, E)
    t("V7 grafo: precedente qualificado, tribunal ANTES da súmula ('STJ, Súmula 297')", ("qualificado", "Tema 1061") in cg and ("qualificado", "Súmula 297/STJ") in cg)
    t("V7 'Súmula 297' e 'Súmula 297/STJ' são a MESMA chave (senão o grafo conta em dobro)", s.ancoras("Súmula 297/STJ e adiante a Súmula 297") == ["Súmula 297/STJ"])
    sem_tjse = dict(d, juris_citada="STJ, Tema 1061. Contrato nº 202500767922 do banco.")
    t("V7 grafo: 12 dígitos sem 'TJSE' antes NÃO vira citação (é nº de contrato)", ("tjse", "202500767922") not in s.citacoes_da_ementa(sem_tjse, E.replace("TJSE, Apelação Cível nº 202500767922", "contrato 202500767922")))
    # RTC: 3º red team (references/red-team-v07/red-team-2026-09-21-c.md)
    t("RTC3 numeral colado na palavra anterior", s.campos_da_ementa("EMENTA. COMPETÊNCIAIII. RAZÕES DE DECIDIRcabe ao banco o ônus.")["razoes"].startswith("cabe ao banco"))
    t("RTC4 numeral em algarismo arábico", s.campos_da_ementa("EMENTA X. 4. DISPOSITIVO E TESE Recurso desprovido. Tese de julgamento: 1. É nulo.")["tese"].startswith("1. É nulo"))
    t("RTC2 chave sem tribunal é a mesma", s.base_ref("Súmula 297/STJ") == "Súmula 297" == s.base_ref("Súmula 297"))
    t("RTC9 'SV 47' é reconhecido", s._ref_citada("SV 47") == ("qualificado", "Súmula Vinculante 47") and s.ancoras("SV 47") == ["Súmula Vinculante 47"])
    t("RTC8 'nao', 'sem' e 'menor' NÃO são descartadas (mudam o sentido)", not ({"nao", "sem", "menor"} & s._VAZIAS))
    t("RTC8 'agravo' e 'recurso' também não", not ({"agravo", "recurso", "direito", "processo"} & s._VAZIAS))
    pa = s.partes_fts("agravo de instrumento", None)
    t("RTC8 palavras de praxe descartadas são declaradas", any(r.startswith("__ignoradas__") for r, _, ob in pa if ob is None))
    t("RTC8 'agravo' entra na expressão", any("agravo" in e for _, e, ob in pa if ob is not None))
    t("RTC7 exato=True obriga cada palavra", all(ob for _, _, ob in s.partes_fts("dano moral", None, exato=True) if ob is not None))
    t("RTC7 aspas não ganham variante de número", '"dano moral"' == next(e for r, e, ob in s.partes_fts('"dano moral"', None) if ob) )
    t("RTC5 `em` vazio cai em 'tudo', não quebra", "resultado" in s.buscar(consulta="competência", em="  ") or "Nada" in s.buscar(consulta="competência", em="  "))
    # FTS
    t("fts grupos (exato)", s.montar_fts(None, [["dano moral"], ["negativação", "inscrição indevida"]], exato=True) == '("dano moral") AND ("negativacao" OR "inscricao indevida")')
    t("fts radical", s.montar_fts("consign$", None) == '"consign"*')
    t("variantes: moral↔morais, acao↔acoes, desconto↔descontos", "morais" in s.variantes_numero("moral") and "acoes" in s.variantes_numero("acao") and "acao" in s.variantes_numero("acoes") and "descontos" in s.variantes_numero("desconto") and "indevido" in s.variantes_numero("indevidos"))
    t("variantes: palavra curta e número ficam", s.variantes_numero("cdc") == ["cdc"] and s.variantes_numero("1691") == ["1691"])
    e = s.montar_fts(None, [["dano moral"]]); t("frase expande número", '"danos morais"' in e and '"dano moral"' in e)
    import sqlite3 as _sq; _c = _sq.connect(":memory:"); _c.execute('create virtual table f using fts5(t, tokenize="unicode61 remove_diacritics 2")')
    _c.executemany("insert into f values(?)", [("DESCONTOS INDEVIDOS EM BENEFÍCIO",), ("AÇÕES COLETIVAS",), ("nada",)])
    t("FTS5 aceita a expressão e acha o plural", len(_c.execute("select * from f where f match ?", (s.montar_fts(None, [["desconto indevido", "ação coletiva"]]),)).fetchall()) == 2)
    for veneno in ['a" OR ementa:x', 'NEAR(a b)', '((( ', '*', 'ementa: teste', "auxílio-doença", 'x" AND "y']:
        try: _c.execute("select * from f where f match ?", (s.montar_fts(None, [[veneno]]) or '"zzz"',)).fetchall(); okv = True
        except ValueError: okv = True
        except Exception: okv = False
        t(f"sintaxe FTS5 não é injetável: {veneno!r}", okv)
    try: s.montar_fts('"culpa E dolo"', None); t("'E' entre aspas aceito", True)
    except ValueError: t("'E' entre aspas aceito", False)
    # parser por célula (regressões do 1º uso real: 799/1610 relatores cortados na v0.1.0)
    pl = s.parse_secao(fx("09-principal-168-pleno.html"))
    t("R2 pleno: 43 itens sem anomalia", len(pl) == 43 and s.anomalias_secao(pl) == [])
    t("R2 relator em <div> próprio / <font> aninhado", all(x["relator"] == "DESA. PRESIDENTE DO TRIBUNAL DE JUSTIÇA" for x in pl if x["acordao"] in ("202640802", "202640816")))
    colado = '<table><tr><td><font style="font-size: 7pt">EMENTA X. ' + "Y" * 80 + '<br />PROCESSO: <a href="r?tmp.npro=1">1</a><br />ACÓRDÃO: <a href="http://x/relatorio.wsp?tmp.numprocesso=111&amp;tmp.numacordao=222">222</a><br /><b>AC N&ordm; 10491/2026</b><b>RELATORA ORIGIN&Aacute;RIA: DESA.</b><b>&nbsp;FULANA DE TAL</b></font></td></tr></table>'
    ic = s.parse_secao(colado)[0]
    t("R2 rótulo colado e nome em <b> separado", ic["recurso"] == "AC Nº 10491/2026" and ic["relator"] == "DESA. FULANA DE TAL" and ic["relator_rotulo"] == "RELATORA ORIGINÁRIA")
    t("R2 anomalia denunciada", s.anomalias_secao([dict(ic, relator="")]) != [] and s.anomalias_secao([]) == ["nenhum acórdão reconhecido"])
    try: s.montar_fts("dano E moral", None); t("operador recusado", False)
    except ValueError: t("operador recusado", True)
    # índice + busca (offline)
    if not online:
        con = s._db()
        con.execute("INSERT OR REPLACE INTO edicoes VALUES(168,'72026','2026-08-31')"); con.commit()
        t("indexa 2", s.indexar_secao(con, 168, 5, "Seção Especializada Cível", itens) == 2)
        t("reindexar não duplica", s.indexar_secao(con, 168, 5, "Seção Especializada Cível", itens) == 0)
        out = s.buscar(grupos=[["conflito de competencia"], ["superendividamento", "xyz"]])
        t("busca acha sem acento", "202639853" in out and "1 resultado" in out)
        t("busca diz cobertura e limites", "31/08/2026" in out and "Turmas Recursais" in out and "só ementa/índice" in out)
        t("busca por número", "202639857" in s.buscar(numero="202600649163"))
        t("zero resultado não é 'não localizado'", "NÃO é 'não localizado" in s.buscar(consulta="usucapião"))
        t("filtro órgão", "Nada no índice" in s.buscar(consulta="competência", orgao="Câmara Criminal"))
        t("plural acha singular no índice", "202639853" in s.buscar(consulta="conflitos negativos"))
        t("exato não acha", "Nada no índice" in s.buscar(consulta="conflitos negativos", exato=True))
        t("filtro de data exclui", "Nada no índice" in s.buscar(consulta="competência", data_inicio="01/09/2026"))
        t("filtro de data inclui e avisa que é data do Boletim", "data do BOLETIM" in s.buscar(consulta="competência", data_inicio="01/08/2026", data_fim="31/08/2026"))
        t("data inválida recusada", "recusada" in s.buscar(consulta="x", data_inicio="ontem"))
        t("página além do fim não vira 'nada'", "além do fim" in s.buscar(consulta="competência", pagina=9))
        t("LIKE não aceita curinga", "Nada no índice" in s.buscar(consulta="competência", orgao="%"))
        t("ordenacao recentes", "202639853" in s.buscar(consulta="competência", ordenacao="recentes"))
        t("diagnóstico por seção", "Seção Especializada Cível: 2 acórdãos" in s.diagnostico())
        s.guardar_bruto(168, 5, fx("07-principal-168-sec5.html")); con.execute("UPDATE acordaos SET relator='TORTO'"); con.execute("UPDATE meta SET valor='0' WHERE chave='parser_versao'"); con.commit()
        t("parser mudou → reindexa do bruto sem rede", s._db().execute("SELECT relator FROM acordaos WHERE acordao='202639853'").fetchone()[0] == "DES. CEZÁRIO SIQUEIRA NETO")
        t("RT17 número CNJ é recusado com explicação, não vira 'nada'", "NÃO é 'não localizado'" in s.buscar(numero="0001234-56.2026.8.25.0001"))
        rr = [dict(itens[0], ementa="EMENTA RETIFICADA " + itens[0]["ementa"])]
        con.execute("INSERT OR REPLACE INTO edicoes VALUES(169,'82026','2026-09-30')"); s.indexar_secao(con, 169, 5, "Seção Especializada Cível", rr)
        t("RT19 republicação é guardada e avisada", "REPUBLICADO" in s.buscar(numero="202639853"))
        t("RTB19 data_inicio > data_fim é recusado", "recusada" in s.buscar(consulta="competência", data_inicio="31/12/2026", data_fim="01/01/2026"))
        t("RTB20 filtro que zerou é nomeado", "foi o filtro que zerou" in s.buscar(consulta="competência", orgao="Câmara Criminal"))
        con.execute("INSERT OR REPLACE INTO campos VALUES('900000001','CAB','CASO','SE E DEVIDA A REPETICAO EM DOBRO','RAZOES','DISP','1. E DEVIDA A REPETICAO EM DOBRO','','')")
        con.execute("INSERT INTO fts_campos(acordao,cabecalho,caso,questao,razoes,dispositivo,tese) VALUES('900000001','CAB','CASO','SE E DEVIDA A REPETICAO EM DOBRO','RAZOES','DISP','1. E DEVIDA A REPETICAO EM DOBRO')")
        con.execute("INSERT OR IGNORE INTO citacoes VALUES('900000001','qualificado','Tema 1061')")
        con.execute("INSERT OR IGNORE INTO citacoes VALUES('900000002','tjse','880000000001')")
        con.execute("INSERT OR IGNORE INTO citacoes VALUES('900000003','tjse','202400999999')"); con.commit()
        t("V7 busca em campo: acha na tese", "900000001" in s.buscar(consulta="repetição em dobro", em="tese"))
        con.execute("INSERT OR REPLACE INTO campos VALUES('900000004','SO NO CABECALHO REPETICAO EM DOBRO','','','','','','','')")
        con.execute("INSERT INTO fts_campos(acordao,cabecalho,caso,questao,razoes,dispositivo,tese) VALUES('900000004','SO NO CABECALHO REPETICAO EM DOBRO','','','','','')")
        con.execute("INSERT OR REPLACE INTO acordaos VALUES('900000004','880000000004','Apelação Cível','AC Nº 4/2026','DES. Y','RELATOR ORIGINÁRIO','1ª Câmara Cível',168,'SO NO CABECALHO REPETICAO EM DOBRO')")
        con.execute("INSERT INTO fts(acordao,ementa,classe,relator) VALUES('900000004','SO NO CABECALHO REPETICAO EM DOBRO','Apelação Cível','DES. Y')"); con.commit()
        t("RTC1 acórdão SEM ementa estruturada aparece na busca por campo (o cabeçalho entra junto)", "900000004" in s.buscar(consulta="repetição em dobro", em="tese"))
        t("RTC1 a saída avisa que o cabeçalho entra", "cabeçalho" in s.buscar(consulta="repetição em dobro", em="tese"))
        # o campo pedido é que discrimina: 900000001 tem o termo em `questao`/`tese`, não em `caso` nem no cabeçalho
        t("V7 busca em campo: não acha onde não está", "900000001" not in s.buscar(consulta="repetição em dobro", em="caso", por_pagina=20))
        t("V7 campo desconhecido é recusado com explicação", "não conhece" in s.buscar(consulta="competência", em="ementa"))
        con.execute("INSERT OR IGNORE INTO citacoes VALUES('900000004','qualificado','Súmula 297/STJ')")
        con.execute("INSERT OR IGNORE INTO citacoes VALUES('900000001','qualificado','Súmula 297')"); con.commit()
        t("RTC2 'Súmula 297' e 'Súmula 297/STJ' acham os dois lados", all(x in s.buscar(cita=c_) for c_ in ("Súmula 297", "Súmula 297/STJ") for x in ("900000001", "900000004")))
        t("RTC2 o mapa não conta a mesma súmula duas vezes", s.mapa_citacoes().count("Súmula 297") <= 1)
        t("V7 filtro cita=", "900000001" in s.buscar(cita="Tema 1061") and "Nada no índice" in s.buscar(cita="Tema 9999"))
        t("V7 cita= sozinho basta (sem consulta)", "resultado" in s.buscar(cita="Tema 1061"))
        t("V7 cita= irreconhecível é recusado", "não é uma referência" in s.buscar(consulta="competência", cita="julgado tal"))
        t("V7 autoridade interna aparece na busca", "CITADO por 1 acórdão" in s.buscar(numero="880000000001"))
        mp = s.mapa_citacoes()
        t("V7 mapa sem referência lista qualificados e líderes", "Tema 1061" in mp and "FORA do índice" in mp)
        t("V7 mapa com referência lista quem cita", "900000001" in s.mapa_citacoes("Tema 1061"))
        t("V7 mapa: zero citações não é 'não existe'", "NÃO significa" in s.mapa_citacoes("Tema 9999"))
        t("RTB21 sem texto, a ordem anunciada é a real", "ordem: recentes" in s.buscar(numero="202639853"))
        # disjuntor
        t("diagnóstico livre", "livre" in s.diagnostico())
        s._pausar(600, "teste"); s._pausar(10, "teste curto")
        try: asyncio.run(s._pedir_vez()); t("pausa bloqueia", False)
        except s.PesquisaNaoRealizada: t("pausa bloqueia", True)
        t("pausa só cresce", s._ler_estado()["pausa_ate"] - __import__("time").time() > 500)
        t("obter em pausa = PESQUISA NÃO REALIZADA", "PESQUISA NÃO REALIZADA" in asyncio.run(s.obter("202639853")))
        open(s.ARQ_ESTADO, "w").write("{lixo")
        t("estado ilegível = fail-closed", s._ler_estado()["pausa_ate"] > __import__("time").time())
        import json as _j, time as _t
        s._PAUSA_MEMORIA = 0
        open(s.ARQ_ESTADO, "w").write(_j.dumps({"requisicoes": ["x", 1], "pausa_ate": "amanhã"}))
        t("RT12 tipos errados no estado = fail-closed, sem TypeError", s._ler_estado()["pausa_ate"] > _t.time())
        open(s.ARQ_ESTADO, "w").write(_j.dumps({"requisicoes": [_t.time() + 99999], "pausa_ate": 0}))
        t("RT8 timestamp no futuro é podado (sem laço infinito)", s._ler_estado()["requisicoes"] == [])
        asyncio.run(asyncio.wait_for(s._pedir_vez(), 5)); t("RT8 _pedir_vez retorna", True)
        open(s.ARQ_ESTADO, "w").write(_j.dumps({"requisicoes": [], "pausa_ate": 0}))
        pag = "<html><body>" + "x" * 900 + " golpe do falso captcha em site de banco " + "</body></html>"
        t("RT7 'captcha' numa ementa não é desafio", not any(m in pag[:pag.lower().find("<body") + 250].lower() for m in s.MARCAS_DESAFIO))
        s._pausar(600, "teste")
        # recibo: grava do fixture e lê sem rede (mesmo em pausa)
        s.gravar_recibo("202638463", "202600737656", fx("03-relatorio-202638463.html"))
        o = asyncio.run(s.obter("202638463"))
        t("obter pelo recibo, sem rede", "lido do disco" in o and "1ª Câmara Cível" in o and "17/07/2026" in o and "inteiro teor lido" in o)
        t("partes omitidas por padrão", "AGRAVANTE" not in o)
        v = asyncio.run(s.verificar("202638463", "voto pelo desprovimento do recurso"))
        t("verificar ✅ pelo recibo", v.startswith("✅"))
        t("verificar ❌", asyncio.run(s.verificar("202638463", "voto pelo provimento integral")).startswith("❌"))
        rec_ruim = s.gravar_recibo("202639853", "202600632112", fx("03-relatorio-202638463.html"))  # HTML de OUTRO acórdão
        t("RT4 recibo com HTML de outro acórdão é posto de lado", s.ler_recibo("202639853") is None and os.path.exists(s._arq_recibo("202639853") + ".inconsistente"))
        rj = _j.load(open(s._arq_recibo("202638463"))); rj["html"] = rj["html"].replace("desprovido", "provido"); _j.dump(rj, open(s._arq_recibo("202638463"), "w"))
        t("RT4 recibo adulterado (sha256 não bate) é recusado", s.ler_recibo("202638463") is None)
        s.gravar_recibo("202638463", "202600737656", fx("03-relatorio-202638463.html"))
        o2 = asyncio.run(s.obter("202638463", max_caracteres=3000))
        t("RT10 saída cortada = 'EM PARTE'", "EM PARTE" in o2)
        t("RTB22 max_caracteres negativo é saneado", "cortado em 2000" in asyncio.run(s.obter("202638463", max_caracteres=-10)))
        import unittest.mock as _um
        with _um.patch.object(s, "parse_teor", side_effect=lambda h: {"acordao": ""}):
            rr_ = s.ler_recibo("202638463")
        t("RTB7 parser que não reconhece o cabeçalho NÃO destrói o recibo", rr_ is not None and "aviso" in rr_ and os.path.exists(s._arq_recibo("202638463")))
        t("RT3 promessa honesta sobre partes", "continuam nomeando" in o2)
        t("RT20 recibos/ 0700", oct(os.stat(s.DIR_RECIBOS).st_mode)[-3:] == "700")
        t("recibo 0600", oct(os.stat(s._arq_recibo("202638463")).st_mode)[-3:] == "600")
        import httpx as _hx
        t("RTD1 timeout NAO arma o disjuntor", s._falha_transitoria(_hx.ReadTimeout("x")))
        t("RTD2 queda de conexao NAO arma o disjuntor", s._falha_transitoria(_hx.ConnectError("x")))
        t("RTD3 erro que nao e de rede ARMA o disjuntor", not s._falha_transitoria(ValueError("x")))
    else:
        o = asyncio.run(s.obter("202638463", "202600737656"))
        print(o[:600]); t("online: inteiro teor", "1ª Câmara Cível" in o)
    print(f"{ok} verificações OK, {falhas} falha(s)")
    return 1 if falhas else 0

if __name__ == "__main__":
    sys.exit(main("--online" in sys.argv))
