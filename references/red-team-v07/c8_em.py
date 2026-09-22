# C8: a promessa "busca por campo NÃO perde acórdão, só deixa de distingui-lo"
import os, sys
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
con = S._db()
q = S.montar_fts(None, [["prescricao"]])
tot = con.execute("SELECT count(*) FROM fts WHERE fts MATCH ?", (q,)).fetchone()[0]
for em in ("questao", "tese", "questao,tese", "cabecalho"):
    cols = "{" + " ".join(em.split(",")) + "}"
    n = con.execute(f"SELECT count(*) FROM fts_campos WHERE fts_campos MATCH ?", (cols + " : (" + q + ")",)).fetchone()[0]
    print(f"em={em:14s} → {n:5d}   (tudo: {tot})")
# acórdãos SEM estrutura que casam e somem
sem = con.execute("SELECT count(*) FROM campos WHERE caso='' AND questao='' AND razoes='' AND dispositivo='' "
                  "AND acordao IN (SELECT acordao FROM fts WHERE fts MATCH ?)", (q,)).fetchone()[0]
print("dos que casam em 'tudo', SEM estrutura (só cabecalho):", sem)
print()
for em in ("TUDO", "questao, tese", "questao,questao", "tudo,questao", "questao;;tese", " ", "juris_citada", "legislacao"):
    out = S.buscar(grupos=[["prescricao"]], em=em, por_pagina=5)
    print(f"em={em!r:20s} → {out.splitlines()[1][:150] if len(out.splitlines())>1 else out[:150]}")
