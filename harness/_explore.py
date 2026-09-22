import sqlite3, re, sys, json
c = sqlite3.connect('/tmp/goldtjse/base/boletim.db')
cur = c.cursor()
cur.execute("select acordao, processo, classe, recurso, relator, orgao, edicao, ementa from acordaos")
rows = cur.fetchall()
cols = ["acordao","processo","classe","recurso","relator","orgao","edicao","ementa"]

def search(pat, flags=re.IGNORECASE):
    p = re.compile(pat, flags)
    return [dict(zip(cols,r)) for r in rows if p.search(r[7])]

if __name__ == "__main__":
    pat = sys.argv[1]
    res = search(pat)
    print(f"TOTAL: {len(res)}")
    for r in res[:400]:
        print(r["acordao"], "|", r["ementa"][:160].replace("\n"," "))
