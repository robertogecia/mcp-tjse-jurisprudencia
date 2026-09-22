#!/usr/bin/env python3
"""Monta o gabarito (gold set) do harness de qualidade de busca do índice TJSE.

CEGO À IMPLEMENTAÇÃO: este script NÃO importa servidor_tjse e NÃO usa buscar().
Ele varre a tabela `acordaos` de uma CÓPIA do banco com regex em Python sobre a
ementa normalizada (minúscula, sem acento) e decide relevância por conteúdo.

Uso:  python3 montar_gold.py /tmp/gold.db  > gold.json
"""
import sqlite3, re, sys, json, unicodedata, hashlib

DB = sys.argv[1] if len(sys.argv) > 1 else "/tmp/gold.db"
TETO_ESSENCIAIS = 25

def sem_acento(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()

def cabecalho(e: str, k: int = 200) -> str:
    """Trecho de palavras-chave da ementa (antes de 'I. CASO EM EXAME')."""
    return re.split(r"i\.\s*caso em exame|i\s*[-–]\s*caso|i\.caso|i\s*[-–]\s*fatos|i\s*–\s*fatos", e)[0][:k]

def rx(p):
    r = re.compile(p)
    return lambda t: bool(r.search(t))

# ---------------------------------------------------------------- consultas
# cab  = regex que precisa casar no cabeçalho de palavras-chave (foco do caso)
# corpo= regex que precisa casar na ementa inteira (confirma o recorte)
# amplo= regex de varredura generosa → o que casa aqui mas não é essencial vira "desejável"
# raro = vocabulário fora do óbvio; tudo que casar entra como essencial de ofício
CONSULTAS = [
 dict(id="q1_bancario_idoso_analfabeto",
   pergunta="Contrato bancário (empréstimo consignado, cartão, tarifa) impugnado por consumidor idoso ou analfabeto: de quem é o ônus da prova e o contrato vale sem assinatura a rogo?",
   termos_advogado=["empréstimo consignado", "analfabeto", "idoso", "assinatura a rogo", "art. 595 CC", "ônus da prova"],
   cab=r"(analfabet|hipervulner|idos[oa]|nao alfabetizad)", cab_k=200,
   corpo=r"(inexistencia de debito|inexistencia de relacao|inexistencia de negocio|nulidade|anulatoria|nao contratad|fraud|negativa de contratac)",
   corpo2=r"(emprestimo|consignad|bancari|instituicao financeira|cartao|tarifa)",
   amplo=r"(analfabet|hipervulner|idos[oa]|septuagenari|octogenari)",
   amplo2=r"(emprestimo|consignad|contrato bancari|instituicao financeira|cartao|tarifa|mutuo|avenca|pactuac)",
   raro=r"(a rogo|analfabetismo funcional|semianalfabet|nao alfabetizad|avenca|pactuac|numerario|hipervulnerabilidade)"),
 dict(id="q2_plano_saude_autismo",
   pergunta="Plano de saúde pode negar, limitar por coparticipação ou descredenciar clínica no tratamento multidisciplinar (método ABA) de criança com transtorno do espectro autista?",
   termos_advogado=["plano de saúde", "autismo", "TEA", "método ABA", "tratamento multidisciplinar", "coparticipação", "rol da ANS"],
   cab=r"(autis|\btea\b)", cab_k=330, cab2=r"(plano de saude|saude suplementar|operadora)",
   corpo=r"(multidisciplinar|\baba\b|coparticipac|cobertura|descredenciamento|rescisao unilateral|reembolso)",
   amplo=r"(autis|espectro autista|\btea\b)",
   amplo2=r"(plano de saude|operadora|saude suplementar|unimed|hapvida|amil|rol da ans)",
   raro=r"(infante|impuber|analise do comportamento aplicada|denver|terapia abr|paciente infante|menor impubere)"),
 dict(id="q3_cartao_consignado_rmc",
   pergunta="Cartão de crédito consignado com reserva de margem consignável (RMC) descontado de benefício previdenciário sem contratação válida: nulidade, repetição do indébito e dano moral?",
   termos_advogado=["RMC", "reserva de margem consignável", "cartão de crédito consignado", "desconto em benefício previdenciário", "repetição do indébito"],
   cab=r"(reserva de margem|\brmc\b|\brcc\b|cartao de credito consignad|cartao consignado|cartao benefici)", cab_k=200,
   corpo=r"(desconto|indebito|nulidade|inexistencia|dano moral|contratac)",
   amplo=r"(reserva de margem|\brmc\b|\brcc\b|cartao consignad|cartao de credito consignad|cartao benefici|saque facil|cartao com reserva)",
   raro=r"(saque facil|rcc\b|cartao benefici|margem consignavel reservada|avenca|pactuac|numerario)"),
 dict(id="q4_negativacao_indevida",
   pergunta="Inscrição indevida do nome do consumidor em cadastro de inadimplentes gera dano moral in re ipsa, e o que acontece se houver negativação preexistente (Súmula 385)?",
   termos_advogado=["negativação indevida", "inscrição indevida", "cadastro de inadimplentes", "SERASA", "dano moral in re ipsa", "Súmula 385"],
   cab=r"(negativac|inscricao indevida|cadastro de inadimplent|orgaos de protecao ao credito)", cab_k=200,
   corpo=r"dano moral",
   amplo=r"(negativac|inscricao indevida|cadastro de inadimplent|serasa|\bspc\b|orgao de protecao ao credito|restricao creditici|sumula 385)",
   raro=r"(sumula 385|restricao creditici|anotacao restritiva|cadastro restritivo|apontamento indevido|protesto indevido)"),
 dict(id="q5_estado_falha_saude",
   pergunta="Responsabilidade civil do Estado/Município por falha na prestação do serviço público de saúde (demora em cirurgia, erro médico, omissão de atendimento): cabe dano moral?",
   termos_advogado=["responsabilidade civil do Estado", "falha na prestação do serviço de saúde", "erro médico", "SUS", "dano moral", "omissão"],
   cab=r"(responsabilidade civil do estado|responsabilidade do estado|responsabilidade civil (objetiva )?(do municipio|do ente|estatal)|falha na prestacao do servico (publico )?de saude|erro medico)", cab_k=330,
   corpo=r"(saude|hospital|medic|upa|samu|cirurgi|parto|unidade de pronto)",
   amplo=r"(responsabilidade civil do estado|responsabilidade objetiva|erro medico|falha na prestacao do servico|omissao estatal|art. 37, § 6)",
   amplo2=r"(saude|hospital|sus\b|medic|cirurgi|parto|upa|samu)",
   raro=r"(violencia obstetrica|iatrogen|nosocomio|infante|omissao estatal|teoria da faute du service|perda de uma chance)"),
 dict(id="q6_usucapiao",
   pergunta="Usucapião (extraordinária, ordinária, especial urbana ou rural): quais requisitos de posse e animus domini o autor precisa provar para adquirir a propriedade?",
   termos_advogado=["usucapião", "animus domini", "posse mansa e pacífica", "prescrição aquisitiva", "usucapião extraordinária"],
   cab=r"usucapi", cab_k=330,
   corpo=r"(animus domini|posse mansa|prescricao aquisitiva)",
   amplo=r"(usucapi|prescricao aquisitiva|animus domini|posse ad usucapionem)",
   raro=r"(prescricao aquisitiva|posse ad usucapionem|acessio possessionis|usucapiao tabular|interversao)"),
]

def main():
    con = sqlite3.connect(DB)
    linhas = con.execute("select acordao, classe, orgao, ementa from acordaos").fetchall()
    base = [(a, cl, og, em, sem_acento(em)) for a, cl, og, em in linhas]
    saida = {"fonte": DB, "total_acordaos": len(base),
             "metodo": ("varredura direta do banco com regex sobre a ementa normalizada; "
                        "nenhuma chamada a servidor_tjse.buscar(). Essencial = caso cujo FOCO "
                        "(cabeçalho de palavras-chave da ementa) é o tema da pergunta; quando o "
                        "conjunto estrito passa de %d, entram de ofício os de vocabulário incomum "
                        "(campo `raro`) e o restante é completado por amostra determinística "
                        "(md5 do nº do acórdão), para não enviesar. O excedente vira `desejavel`." % TETO_ESSENCIAIS),
             "consultas": []}
    for q in CONSULTAS:
        cab_ok = rx(q["cab"]); cab2 = rx(q["cab2"]) if q.get("cab2") else None
        corpo = rx(q["corpo"]); corpo2 = rx(q["corpo2"]) if q.get("corpo2") else None
        amplo = rx(q["amplo"]); amplo2 = rx(q["amplo2"]) if q.get("amplo2") else None
        raro = rx(q["raro"])
        estrito, largo = [], []
        for a, cl, og, em, t in base:
            h = cabecalho(t, q.get("cab_k", 200))
            if cab_ok(h) and (cab2 is None or cab2(h)) and corpo(t) and (corpo2 is None or corpo2(t)):
                estrito.append((a, cl, og, em, t))
            elif amplo(t) and (amplo2 is None or amplo2(t)):
                largo.append((a, cl, og, em, t))
        forcados = [x for x in estrito if raro(x[4])]
        resto = [x for x in estrito if x not in forcados]
        resto.sort(key=lambda x: hashlib.md5(x[0].encode()).hexdigest())
        ess = (forcados[:TETO_ESSENCIAIS] + resto)[:TETO_ESSENCIAIS]
        ess_ids = {x[0] for x in ess}
        desej = [x for x in estrito if x[0] not in ess_ids] + largo
        itens = []
        for a, cl, og, em, t in ess:
            m = raro(t)
            itens.append(dict(acordao=a, classe=cl, orgao=og, nivel="essencial",
                              vocabulario="incomum" if m else "comum",
                              porque=cabecalho(em, 200).strip(),
                              ementa_200=em[:200]))
        for a, cl, og, em, t in desej:
            itens.append(dict(acordao=a, classe=cl, orgao=og, nivel="desejavel",
                              vocabulario="incomum" if raro(t) else "comum",
                              porque=cabecalho(em, 160).strip(), ementa_200=em[:200]))
        saida["consultas"].append(dict(id=q["id"], pergunta=q["pergunta"],
                                       termos_advogado=q["termos_advogado"],
                                       n_essenciais=len(ess), n_desejaveis=len(desej),
                                       acordaos=itens))
    json.dump(saida, sys.stdout, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
