import os, sys, re, collections
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
for ac in ("202640792","202640805","202640333"):
    e = con.execute("select ementa from acordaos where acordao=?", (ac,)).fetchone()[0]
    c = S.campos_da_ementa(e)
    print("="*90); print(ac, "len", len(e))
    for k in S.CAMPOS_EMENTA:
        print(f"  [{k}] ({len(c[k])}) {c[k][:220]!r}")
    print("  marcas cruas:", [(m.group('num'), m.group('rot')) for m in S._RE_SECAO.finditer(e)])
