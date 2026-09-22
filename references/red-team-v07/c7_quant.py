# C7: quantifica (a) seção real descartada pelo filtro com_num, (b) dispositivo em numeral arábico
import os, sys, re, collections
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
st = collections.Counter(); ex = collections.defaultdict(list)
for r in con.execute("select acordao, ementa from acordaos"):
    e = r["ementa"]
    marcas = []
    for m in S._RE_SECAO.finditer(e):
        rot = next(k for k, p in S._SECOES_EMENTA if re.fullmatch(p, m.group("rot"), re.I))
        marcas.append((rot, bool(m.group("num")), m.start("rot")))
    if not marcas: continue
    com_num = any(x[1] for x in marcas)
    if com_num:
        # seção descartada por não ter numeral, apesar de ser título de verdade (rótulo não repetido antes)
        vistos = {x[0] for x in marcas if x[1]}
        perdidas = {x[0] for x in marcas if not x[1]} - vistos
        if perdidas:
            st["secao_perdida_por_com_num"] += 1
            for p in perdidas: st["perdida_"+p] += 1
            ex["com_num"].append((r["acordao"], sorted(perdidas)))
    # dispositivo com numeral arábico descartado
    if re.search(r"(?i)(?:^|[\s.;:])\d{1,2}\s*[.\-–—)]\s*DISPOSITIVO\b", e) and not S.campos_da_ementa(e)["dispositivo"]:
        st["dispositivo_arabico_descartado"] += 1; ex["arab"].append(r["acordao"])
for k,v in sorted(st.items()): print(k, v)
print("exemplos com_num:", ex["com_num"][:8])
print("exemplos arabico:", ex["arab"][:8])
