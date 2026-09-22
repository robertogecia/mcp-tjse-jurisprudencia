import os, sys, re
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
for ac in ("202640381","202629073","202640139"):
    e = con.execute("select ementa from acordaos where acordao=?", (ac,)).fetchone()[0]
    c = S.campos_da_ementa(e)
    print("="*90); print(ac)
    print(" marcas:", [(m.group('num'), m.group('rot')) for m in S._RE_SECAO.finditer(e)])
    for k in S.CAMPOS_EMENTA: print(f"  [{k}] ({len(c[k])}) {c[k][:160]!r}")
    for lab in ("DISPOSITIVO","RAZÕES DE DECIDIR","TESE DE JULGAMENTO"):
        i = e.upper().find(lab)
        if i>=0: print(f"  ...{lab} no bruto @{i}: {e[max(0,i-40):i+60]!r}")
