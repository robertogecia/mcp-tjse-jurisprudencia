# C3: varredura de campos_da_ementa sobre as 8.974 ementas reais
import os, sys, re, collections
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
rows = con.execute("select acordao, ementa from acordaos").fetchall()
st = collections.Counter(); ex = collections.defaultdict(list)
for r in rows:
    e = r["ementa"]; c = S.campos_da_ementa(e)
    est = any(c[k] for k in ("caso","questao","razoes","dispositivo"))
    st["total"] += 1; st["estruturada"] += est
    if not c["cabecalho"].strip():
        st["cabecalho_vazio"] += 1; ex["cabecalho_vazio"].append(r["acordao"])
    # rótulo de seção sobrando DENTRO de um campo = campo engoliu o seguinte
    for k in ("caso","questao","razoes","dispositivo","tese"):
        if c[k] and re.search(r"(?i)(caso em exame|quest[aã]o em discuss|raz[oõ]es de decidir|tese de julgamento|jurisprud[eê]ncia relevante citada|dispositivos? relevantes? citad)", c[k]):
            st["vaza_rotulo_"+k] += 1; ex["vaza_rotulo_"+k].append(r["acordao"])
    # conteudo duplicado entre campos
    if c["tese"] and c["dispositivo"] and (c["tese"] in c["dispositivo"] or c["dispositivo"] in c["tese"]):
        st["tese_dup_dispositivo"] += 1; ex["tese_dup_dispositivo"].append(r["acordao"])
    # perda: soma dos campos vs ementa
    soma = sum(len(c[k]) for k in S.CAMPOS_EMENTA)
    if soma < len(e) * 0.80:
        st["perde_20pct"] += 1; ex["perde_20pct"].append((r["acordao"], soma, len(e)))
    if est and not c["cabecalho"]:
        st["est_sem_cabecalho"] += 1
for k, v in sorted(st.items()): print(f"{k}: {v}")
print()
for k, v in ex.items():
    print(k, "→", v[:5])
