"""t4 — índice e busca: injeção/erro FTS5, grupo que some, paginação além do fim,
LIKE com curinga, numero com máscara CNJ, edição sem data."""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import *

itens = s.parse_secao(fx("07-principal-168-sec5.html"))
con = s._db()
con.execute("INSERT OR REPLACE INTO edicoes VALUES(168,'72026','2026-08-31')"); con.commit()
s.indexar_secao(con, 168, 5, "Seção Especializada Cível", itens)
print("indexados:", [i["acordao"] for i in itens])

print("\n=== A) montar_fts: injeção de sintaxe FTS5 / erro operacional ===")
hostis = ['"', '""', 'a" OR ementa:"b', 'NEAR(a b)', '*', '(', 'a AND b', 'ementa:x', 'a:b',
          '§§', '...', '-', '$', 'a$', '""*', 'competencia*', 'auxílio-doença', 'R$ 1.000,00']
for h in hostis:
    try:
        q = s.montar_fts(h, None)
    except ValueError as ex:
        print(f"   consulta {h!r:22} -> RECUSADA ({str(ex)[:40]}…)"); continue
    try:
        n = con.execute("SELECT COUNT(*) FROM fts WHERE fts MATCH ?", (q,)).fetchone()[0] if q else "—"
        print(f"   consulta {h!r:22} -> q={q!r:30} match={n}")
    except sqlite3.OperationalError as ex:
        print(f"   consulta {h!r:22} -> q={q!r:30} sqlite3.OperationalError: {ex}")

print("\n=== B) 'E'/'OU' em caixa alta dentro de frase legítima ===")
for c in ['"dano moral E material"', 'ação de cobrança E consignação', '"AÇÃO DE DESPEJO E COBRANÇA"',
          'dano moral e material']:
    try:
        print(f"   {c!r:36} -> {s.montar_fts(c, None)!r}")
    except ValueError:
        print(f"   {c!r:36} -> RECUSADA")

print("\n=== C) grupo que vira vazio some em silêncio (o E deixa de valer) ===")
g = [["conflito de competencia"], ["§§§"]]
print("   grupos =", g, "-> q =", repr(s.montar_fts(None, g)))
out = s.buscar(grupos=g)
print("   resultado:", out.split("\n")[1])
print("   (o 2º grupo — que NENHUM acórdão atende — desapareceu; a saída mostra a expressão já sem ele)")
print("   grupos=[[]] ->", repr(s.montar_fts(None, [[]])), "| busca:", s.buscar(grupos=[[]]).split("\n")[0][:80])

print("\n=== D) paginação além do fim ===")
for pg in (1, 2, 5, 0, -3):
    o = s.buscar(consulta="competencia", pagina=pg)
    print(f"   pagina={pg:>3} -> {o.split(chr(10))[1][:95]}")

print("\n=== E) filtros LIKE aceitam curinga do SQL ===")
for o_ in ("Câmara Criminal", "%", "_%", "Seção%Cível"):
    r = s.buscar(consulta="competencia", orgao=o_)
    print(f"   orgao={o_!r:16} -> {'ACHOU' if 'resultado(s)' in r else 'nada'} :: {r.split(chr(10))[1][:70]}")

print("\n=== F) numero com máscara CNJ / processo de 12 dígitos ===")
for n in ("202600632112", "2026.0063.2112", "0006321-12.2026.8.25.0001", "202639853"):
    r = s.buscar(numero=n)
    print(f"   numero={n!r:28} -> {'ACHOU' if 'resultado(s)' in r else r.split(chr(10))[1][:60]}")

print("\n=== G) edição sem data reconhecida (data=None) ===")
con.execute("INSERT OR REPLACE INTO edicoes VALUES(169,'82026',NULL)")
s.indexar_secao(con, 169, 6, "1ª Câmara Cível",
                [{"acordao": "202699999", "processo": "202600000001", "classe": "Apelação",
                  "recurso": "AC Nº 1/2026", "relator": "DES. X", "relator_rotulo": "RELATOR",
                  "ementa": "TESTE DE COBERTURA COM DATA NULA."}])
print("   cobertura:", s.cobertura(con))
r = s.buscar(consulta="cobertura")
print("   linha do resultado:", [l for l in r.split("\n") if "Boletim ed." in l])
