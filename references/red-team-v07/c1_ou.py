# C1: quanto o OU sujou o topo? Mede nos 10 primeiros quantos casam <=1 termo.
import os, sys
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
print("acordaos:", con.execute("select count(*) from acordaos").fetchone()[0], "versao", S.VERSAO)
CONSULTAS = [
 "desconto indevido em beneficio previdenciario de idoso analfabeto",
 "dano moral por inscricao indevida em cadastro de inadimplentes",
 "guarda compartilhada de filho menor e alimentos",
 "juros abusivos em contrato de emprestimo consignado",
 "responsabilidade do banco por fraude em conta de cliente idoso",
]
for c in CONSULTAS:
    try:
        partes = S.partes_fts(c, None)
    except ValueError as e:
        print("\n===", c, "RECUSADA:", e); continue
    termos = [rot for rot, _, ob in partes if not ob]
    q = S.montar_fts(c, None)
    tot = con.execute("SELECT count(*) FROM fts WHERE fts MATCH ?", (q,)).fetchone()[0]
    rows = con.execute("SELECT acordao, bm25(fts,0,5.0,2.0,1.0) rk FROM fts WHERE fts MATCH ? ORDER BY rk LIMIT 10", (q,)).fetchall()
    print(f"\n=== {c}\n  termos: {termos}  total: {tot}")
    so1 = 0
    for r in rows:
        em = S.norm(con.execute("select ementa from acordaos where acordao=?", (r["acordao"],)).fetchone()[0])
        casam = [t for t in termos if any(v in em for v in S.variantes_numero(S.norm(t)))]
        if len(casam) <= 1: so1 += 1
        print(f"   {r['acordao']} casa {len(casam)}/{len(termos)}: {casam}")
    print(f"  >>> {so1}/10 casam <=1 termo")
