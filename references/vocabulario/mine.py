#!/usr/bin/env python3
"""Mineração de coocorrência no corpus TJSE (cópia local /tmp/vocab). Zero rede.
Para cada termo candidato, mede: doc-freq geral (fts_vocab) e doc-freq dentro de um
conjunto-alvo (acordaos que contêm os termos-semente), e imprime achados com exemplo
de acordao real para conferência.
"""
import sqlite3, re, sys, json

con = sqlite3.connect("/tmp/vocab/base/boletim.db")
cur = con.cursor()

TOTAL_DOCS = cur.execute("select count(*) from acordaos").fetchone()[0]

def texto_completo():
    """acordao -> texto (ementa + campos concatenados)"""
    rows = cur.execute("""
        select a.acordao, a.ementa,
               coalesce(c.cabecalho,''), coalesce(c.caso,''), coalesce(c.questao,''),
               coalesce(c.razoes,''), coalesce(c.dispositivo,''), coalesce(c.tese,''),
               coalesce(c.legislacao,''), coalesce(c.juris_citada,'')
        from acordaos a left join campos c on c.acordao = a.acordao
    """).fetchall()
    out = {}
    for r in rows:
        acordao = r[0]
        out[acordao] = " ".join(x or "" for x in r[1:]).upper()
    return out

TXT = texto_completo()

def doc_freq_geral(termo):
    row = cur.execute("select doc from fts_vocab where term = ?", (termo.lower(),)).fetchone()
    return row[0] if row else 0

def alvo_por_semente(sementes):
    """acordaos cujo texto contem qualquer semente (regex simples, maiuscula)."""
    pats = [re.compile(re.escape(s.upper())) for s in sementes]
    return {a for a, t in TXT.items() if any(p.search(t) for p in pats)}

def contagem_termo_no_alvo(termo, alvo):
    pat = re.compile(re.escape(termo.upper()))
    hits = [a for a in alvo if pat.search(TXT[a])]
    return hits

def sugerir(conceito, sementes, candidatos):
    alvo = alvo_por_semente(sementes)
    print(f"\n=== {conceito} — alvo(sementes)={len(alvo)} acórdãos ===")
    for cand in candidatos:
        hits = contagem_termo_no_alvo(cand, alvo)
        dfg = doc_freq_geral(cand)
        n_alvo = len(hits)
        pct_alvo = n_alvo / len(alvo) if alvo else 0
        pct_geral = dfg / TOTAL_DOCS if TOTAL_DOCS else 0
        razao = (pct_alvo / pct_geral) if pct_geral > 0 else float("inf")
        exemplo = hits[0] if hits else None
        print(f"  {cand!r:45s} doc_geral={dfg:5d} ({pct_geral:5.1%})  no_alvo={n_alvo:4d} ({pct_alvo:5.1%})  razao={razao:6.1f}x  ex={exemplo}")

if __name__ == "__main__":
    # t1 — idoso/analfabeto/consignado
    sugerir("t1_idoso_analfabeto", ["ANALFABET", "IDOSO"],
            ["HIPERVULNERÁVEL", "HIPERVULNERABILIDADE", "TARIFAS BANCÁRIAS", "ASSINATURA A ROGO",
             "ANALFABETISMO", "AVALISTA", "CÉDULA DE CRÉDITO BANCÁRIO", "ILETRAD",
             "BENEFICIÁRIO DO INSS", "DESCONTO INDEVIDO", "APOSENTADO"])

    sugerir("t2_autismo", ["AUTIST", "AUTISMO", "TEA"],
            ["MENOR IMPÚBERE", "INFANTE", "MÉTODO ABA", "TERAPIA MULTIDISCIPLINAR",
             "COBERTURA", "AUTOGESTÃO", "CERCEAMENTO DE DEFESA", "TAXATIVIDADE MITIGADA",
             "DESCREDENCIAMENTO"])

    sugerir("t3_rmc", ["RESERVA DE MARGEM CONSIGNÁVEL", "RMC", " RCC"],
            ["CARTÃO BENEFÍCIO CONSIGNADO", "BIOMETRIA FACIAL", "VENIRE CONTRA FACTUM PROPRIO",
             "PRECLUSÃO TEMPORAL", "BPC/LOAS", "MENOR ABSOLUTAMENTE INCAPAZ", "PRESCRIÇÃO QUINQUENAL",
             "EXERCÍCIO REGULAR DE DIREITO", "TERMO DE CONSENTIMENTO"])

    sugerir("t4_negativacao", ["NEGATIVAÇÃO", "INSCRIÇÃO INDEVIDA"],
            ["SCR", "SISTEMA DE INFORMAÇÕES DE CRÉDITO", "SÚMULA 385", "IN RE IPSA",
             "QUANTUM INDENIZATÓRIO", "CADASTRO DE INADIMPLENTES", "ÓRGÃO DE PROTEÇÃO AO CRÉDITO",
             "PROTESTO"])

    sugerir("t5_estado", ["RESPONSABILIDADE CIVIL DO ESTADO"],
            ["ILEGITIMIDADE PASSIVA", "LIXÃO", "CONCESSIONÁRIA DE SERVIÇO PÚBLICO",
             "COISA JULGADA", "DETENTO", "SUICÍDIO", "ABORDAGEM POLICIAL", "ERRO MÉDICO",
             "VIOLÊNCIA OBSTÉTRICA", "OMISSÃO DO PODER PÚBLICO", "TEORIA DO RISCO ADMINISTRATIVO"])

    sugerir("t6_usucapiao", ["USUCAPI"],
            ["ANIMUS DOMINI", "POSSE MANSA E PACÍFICA", "ACCESSIO POSSESSIONIS",
             "TERRENO DE MARINHA", "AFORAMENTO", "ABANDONO DA CAUSA", "DEFENSOR DATIVO",
             "ÁREA PÚBLICA", "USUCAPIENDO"])

    # conceitos gerais adicionais (para além do gold)
    for conceito, sementes, cands in [
        ("dano_moral", ["DANO MORAL"], ["DANO EXTRAPATRIMONIAL", "QUANTUM INDENIZATÓRIO", "IN RE IPSA", "ABALO MORAL"]),
        ("prescricao", ["PRESCRIÇÃO"], ["PRESCRIÇÃO QUINQUENAL", "PRESCRIÇÃO TRIENAL", "DECADÊNCIA", "PRAZO PRESCRICIONAL", "TERMO INICIAL"]),
        ("honorarios", ["HONORÁRIOS"], ["HONORÁRIOS ADVOCATÍCIOS", "HONORÁRIOS SUCUMBENCIAIS", "MAJORAÇÃO", "DEFENSOR DATIVO", "ARTIGO 85"]),
        ("tutela_urgencia", ["TUTELA DE URGÊNCIA"], ["TUTELA ANTECIPADA", "TUTELA PROVISÓRIA", "PERICULUM IN MORA", "FUMUS BONI IURIS", "LIMINAR"]),
        ("juros_correcao", ["JUROS DE MORA"], ["CORREÇÃO MONETÁRIA", "ÍNDICE DE ATUALIZAÇÃO", "TERMO INICIAL DOS JUROS", "SELIC"]),
        ("cerceamento_defesa", ["CERCEAMENTO DE DEFESA"], ["INDEFERIMENTO DE PROVA", "NULIDADE PROCESSUAL", "INSTRUÇÃO PROBATÓRIA", "PROVA PERICIAL"]),
        ("dever_de_informar_bancario", ["INSTITUIÇÃO FINANCEIRA"], ["ÔNUS DA PROVA", "RESPONSABILIDADE OBJETIVA", "FALHA NA PRESTAÇÃO DO SERVIÇO", "CDC"]),
        ("obrigacao_fazer", ["OBRIGAÇÃO DE FAZER"], ["ASTREINTES", "MULTA COMINATÓRIA", "TUTELA ESPECÍFICA"]),
        ("gratuidade_justica", ["GRATUIDADE DA JUSTIÇA"], ["ASSISTÊNCIA JUDICIÁRIA GRATUITA", "HIPOSSUFICIÊNCIA", "PRESUNÇÃO DE POBREZA"]),
        ("repetitivo_tema", ["TEMA REPETITIVO", "TEMA "], ["RECURSO REPETITIVO", "IRDR", "AFETAÇÃO", "SOBRESTAMENTO"]),
    ]:
        sugerir(conceito, sementes, cands)
