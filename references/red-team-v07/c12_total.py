# C12: o "N resultado(s)" do OU x quantos casam TODOS os termos; e janela de 160 chars do grafo
import os, sys, re
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
for c in ["desconto indevido em beneficio de idoso analfabeto",
          "dano moral por inscricao indevida em cadastro de inadimplentes",
          "guarda compartilhada de filho menor e alimentos"]:
    p = S.partes_fts(c, None)
    ou = S.montar_fts(c, None)
    e_ = " AND ".join(x for _, x, _ in p)
    n_ou = con.execute("SELECT count(*) FROM fts WHERE fts MATCH ?", (ou,)).fetchone()[0]
    n_e = con.execute("SELECT count(*) FROM fts WHERE fts MATCH ?", (e_,)).fetchone()[0]
    print(f"{c!r}\n   'N resultado(s)' mostrado = {n_ou}   |   casam TODOS os termos = {n_e}   ({100*n_e/n_ou:.1f}%)")
print()
print("### grafo: distância entre 'TJSE' e o número capturado")
longe = 0; tot = 0; amostra = []
for r in con.execute("SELECT acordao, ementa FROM acordaos"):
    cps = S.campos_da_ementa(r["ementa"]); jc = cps["juris_citada"]
    if not jc: continue
    for m in re.finditer(r"(?i)tjse[^;]{0,160}?" + S._RE_PROC_TJSE.pattern, jc):
        tot += 1
        d = m.end(1) - m.start() - 12
        if d > 60:
            longe += 1
            if len(amostra) < 6: amostra.append(re.sub(r"\s+", " ", m.group(0))[:150])
print(f"capturas: {tot} · com >60 chars entre 'TJSE' e o número: {longe}")
for a in amostra: print("   ", a)
