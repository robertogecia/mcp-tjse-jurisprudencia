"""B7 — variantes_numero, _frase_fts, explosão combinatória, bm25/paginação sobre o índice REAL (copiado)."""
import _base as b
import os
import re
import shutil
import sqlite3
import time

s = b.s

print("=== A) variantes_numero: variante que MUDA O SENTIDO ou é lixo ===")
for w in ("pais", "pai", "mes", "meses", "juros", "bens", "onus", "lapis", "caos", "mao", "maos", "sao",
          "nao", "pao", "sem", "de", "lei", "leis", "moral", "morais", "acao", "acoes", "dano", "danos",
          "consumidor", "vez", "vezes", "paz", "voz", "luz", "nos", "cruz", "revel", "anel", "gol",
          "fim", "bom", "som", "mar", "cor", "dor", "por", "ser", "ter", "ver", "fez", "tres"):
    print(f"  {w!r:12s} -> {s.variantes_numero(w)}")

print("\n=== B) stopwords/negação expandidas: 'nao' vira 'noes'? ===")
for t in ("nao houve dano", "sem razao", "de oficio"):
    print(f"  {t!r:22s} -> {s._frase_fts(t)[:160]}")

print("\n=== C) explosão combinatória: tamanho e teto de 36 ===")
for t in ("dano moral", "dano moral consumidor banco", "dano moral consumidor banco contrato nulo",
          "dano moral consumidor banco contrato nulo menor incapaz autorizacao judicial",
          "acao revisional de contrato bancario com capitalizacao mensal de juros e comissao de permanencia"):
    f = s._frase_fts(t)
    print(f"  {len(t.split())} palavras -> {len(f)} chars na expressão; combos={f.count(' OR ')+1}")
    if len(f) < 200:
        print(f"      {f}")

print("\n=== D) exato + radical + frase ===")
for t, ex in (("consign$", False), ("consign$", True), ("R$ 5.000,00", False), ("art. 42", False),
              ("a$", False), ("§", False), ("1.000", False)):
    print(f"  {t!r:14s} exato={ex} -> {s._frase_fts(t, ex)!r}")

print("\n=== E) consulta no ÍNDICE REAL (cópia read-only): tempo, duplicidade entre páginas ===")
orig = os.path.join(b.RAIZ, "base", "boletim.db")
if not os.path.exists(orig):
    print("  (sem base real)")
    raise SystemExit
dest = os.path.join(os.environ["TJSE_DIR_DADOS"], "base")
os.makedirs(dest, exist_ok=True)
shutil.copy2(orig, os.path.join(dest, "boletim.db"))
con = sqlite3.connect(os.path.join(dest, "boletim.db"))
con.row_factory = sqlite3.Row
print("  acordaos:", con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0],
      "· fts:", con.execute("SELECT COUNT(*) FROM fts").fetchone()[0],
      "· secoes:", con.execute("SELECT COUNT(*) FROM secoes").fetchone()[0],
      "· republicacoes:", con.execute("SELECT COUNT(*) FROM republicacoes").fetchone()[0])

for t in ("dano moral", "dano moral consumidor banco contrato nulo",
          "acao revisional de contrato bancario com capitalizacao mensal de juros e comissao de permanencia"):
    q = s._frase_fts(t)
    t0 = time.time()
    try:
        n = con.execute("SELECT COUNT(*) FROM fts WHERE fts MATCH ?", (q,)).fetchone()[0]
        print(f"  {len(t.split())}p · {len(q)} chars · {n} hits · {time.time()-t0:.2f}s")
    except sqlite3.Error as ex:
        print(f"  {len(t.split())}p · {len(q)} chars · ERRO {type(ex).__name__}: {ex}")

print("\n  -- duplicidade entre páginas na ordenação 'relevantes' (empate de bm25) --")
q = s._frase_fts("dano moral")
vistos, dupl = set(), []
for pag in range(1, 9):
    rows = con.execute("SELECT a.acordao FROM (SELECT acordao ac, bm25(fts,0,5.0,2.0,1.0) rk FROM fts WHERE fts MATCH ?) r "
                       "JOIN acordaos a ON a.acordao=r.ac JOIN edicoes e USING(edicao) "
                       "WHERE a.acordao IN (SELECT acordao FROM fts WHERE fts MATCH ?) "
                       "ORDER BY r.rk, a.edicao DESC LIMIT 10 OFFSET ?", (q, q, (pag - 1) * 10)).fetchall()
    for r in rows:
        if r["acordao"] in vistos:
            dupl.append((pag, r["acordao"]))
        vistos.add(r["acordao"])
print(f"  8 páginas · {len(vistos)} acórdãos distintos · repetidos entre páginas: {len(dupl)} {dupl[:5]}")

print("\n  -- o MATCH aparece DUAS vezes na consulta 'relevantes' (subconsulta + where)? --")
print("     linha 865-868: SELECT … FROM (… fts MATCH ?) r JOIN … WHERE " + "a.acordao IN (SELECT acordao FROM fts WHERE fts MATCH ?)")
print("     -> o índice FTS é varrido 2x por página; args = [q] + args, e `args` já contém q")

print("\n=== F) ordenação 'relevantes' quando só há `numero` (sem q) ===")
print("  _buscar cai no else (ordem por edição) mas a saída diz 'ordem: relevantes' — ver B-relatório")
