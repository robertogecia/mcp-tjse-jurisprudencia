# C5: seções perdidas por exigir numeral romano / por o rótulo vir com numeral ARÁBICO
import os, sys, re, collections
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
rows = con.execute("select acordao, ementa from acordaos").fetchall()
st = collections.Counter(); ex = collections.defaultdict(list)
RX_DISP = re.compile(r"(?i)\b(?:[IVX]{1,4}\s*[.\-–—)]\s*|\d{1,2}\s*[.\-–—)]\s*)?DISPOSITIVO(?:\s+E\s+TESE)?\b")
for r in rows:
    e = r["ementa"]; c = S.campos_da_ementa(e)
    est = any(c[k] for k in ("caso","questao","razoes","dispositivo"))
    if not est: continue
    st["estruturada"] += 1
    if not c["dispositivo"]:
        st["sem_dispositivo"] += 1
        # havia marcador de dispositivo no texto?
        if re.search(r"(?i)(?:^|[\s.;:])(?:\d{1,2}\s*[.\-–—)]\s*)DISPOSITIVO", e):
            st["dispositivo_com_numeral_ARABICO_perdido"] += 1; ex["arab"].append(r["acordao"])
        if re.search(r"(?i)RAZ[OÕ]ES DE DECIDIR", e) and re.search(r"(?i)DISPOSITIVO", e):
            st["tem_palavra_dispositivo"] += 1
    # razoes engoliu o dispositivo?
    if c["razoes"] and re.search(r"(?i)(?:^|[\s.;:])(?:[ivx]{1,4}|\d{1,2})\s*[.\-–—)]\s*DISPOSITIVO", c["razoes"]):
        st["razoes_engole_dispositivo"] += 1; ex["engole"].append(r["acordao"])
    # outro campo carrega rótulo de OUTRA seção
    for k, outros in (("caso", r"raz[oõ]es de decidir|dispositivo e tese"), ("questao", r"raz[oõ]es de decidir|dispositivo e tese"),
                      ("razoes", r"caso em exame|quest[aã]o em discuss")):
        if c[k] and re.search("(?i)"+outros, c[k]):
            st["leak_"+k] += 1; ex["leak_"+k].append(r["acordao"])
for k,v in sorted(st.items()): print(k, v)
print({k: v[:6] for k,v in ex.items()})
