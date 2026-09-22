# C9: grafo — chaves duplicadas (com e sem tribunal) e falsos processos
import os, sys, re, collections
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
refs = collections.Counter()
for r in con.execute("SELECT ref, COUNT(DISTINCT origem) k FROM citacoes WHERE tipo='qualificado' GROUP BY ref"):
    refs[r["ref"]] = r["k"]
dup = [(b, refs[b], [(x, refs[x]) for x in refs if x.startswith(b + "/")]) for b in refs if "/" not in b
       and any(x.startswith(b + "/") for x in refs)]
print("### chaves partidas (mesma súmula contada em duas linhas):")
for b, k, outros in sorted(dup, key=lambda t: -t[1])[:15]:
    print(f"  {b!r}={k}  vs  {outros}")
print("total de chaves partidas:", len(dup))
print()
print("### teste: tribunal ANTES do número")
for t in ["O STJ, NO TEMA 1061, FIXOU", "SÚMULA 297 DO STJ", "STJ, SÚMULA 297", "SÚMULA 7 DO TJSE",
          "STJ. SÚMULA 297", "IRDR 15 DO TJSE", "TJSE, SÚMULA 3"]:
    print(f"  {t!r:34s} → {S.ancoras(t)}")
print()
print("### processos 'TJSE' capturados no campo de jurisprudência — amostra do que veio")
n=0
for r in con.execute("SELECT c.ref, c.origem FROM citacoes c WHERE c.tipo='tjse' LIMIT 4000"):
    cps = S.campos_da_ementa(con.execute("select ementa from acordaos where acordao=?", (r["origem"],)).fetchone()[0])
    jc = cps["juris_citada"]
    m = re.search(r"(?i)tjse[^;]{0,160}?" + r["ref"], jc)
    if m and n < 12:
        print("   ", r["ref"], "|", re.sub(r"\s+"," ", m.group(0))[-110:]); n += 1
tot = con.execute("SELECT COUNT(*) FROM citacoes WHERE tipo='tjse'").fetchone()[0]
print("arestas tjse:", tot)
