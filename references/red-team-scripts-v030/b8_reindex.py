"""B8 — reindexação: custo por chamada, bug de parser apagando o índice inteiro em silêncio,
republicações trocando de edição, fts x acordaos, corrida entre processos."""
import _base as b
import gzip
import re
import os
import shutil
import sqlite3
import time

s = b.s
SEC = os.path.join(b.RAIZ, "base", "secoes")
DEST = s.DIR_SECOES
os.makedirs(DEST, exist_ok=True)
arqs = sorted(f for f in os.listdir(SEC) if re.fullmatch(r"\d+-\d+\.html\.gz", f))[:4]
for f in arqs:
    shutil.copy2(os.path.join(SEC, f), DEST)
print("seções copiadas:", arqs)

con = s._db()
for f in arqs:
    ed, cod = f.replace(".html.gz", "").split("-")[:2]
    h = gzip.open(os.path.join(DEST, f), "rb").read().decode("utf-8")
    itens = s.parse_secao(h)
    con.execute("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)", (int(ed), str(ed), "2026-08-31"))
    s.indexar_secao(con, int(ed), int(cod), f"Seção {cod}", itens)
print("índice montado:", con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0], "acórdãos")
con.close()

print("\n=== A) custo: _db() reindexa a CADA chamada quando PARSER_VERSAO muda ===")
t0 = time.time()
s._db().close()
print(f"  _db() com parser_versao igual: {time.time()-t0:.3f}s")
s.PARSER_VERSAO += 1
t0 = time.time()
c = s._db()
print(f"  _db() com PARSER_VERSAO nova (1 reindex): {time.time()-t0:.2f}s · "
      f"{c.execute('SELECT COUNT(*) FROM acordaos').fetchone()[0]} acórdãos")
c.close()
t0 = time.time()
s._db().close()
print(f"  _db() logo depois (já reindexado): {time.time()-t0:.3f}s")

print("\n=== B) fts x acordaos após reindexar 2x ===")
s.PARSER_VERSAO += 1
s._db().close()
s.PARSER_VERSAO += 1
c = s._db()
print("  acordaos:", c.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0],
      "· fts:", c.execute("SELECT COUNT(*) FROM fts").fetchone()[0],
      "· fts órfãos:", c.execute("SELECT COUNT(*) FROM fts WHERE acordao NOT IN (SELECT acordao FROM acordaos)").fetchone()[0])
c.close()

print("\n=== C) um BUG de parser apaga o índice inteiro em silêncio? ===")
orig = s.parse_secao
s.parse_secao = lambda h: (_ for _ in ()).throw(AttributeError("bug novo no parser"))
s.PARSER_VERSAO += 1
try:
    c = s._db()
except Exception as ex:
    print(f"  _db() LEVANTOU {type(ex).__name__}: {ex}")
    print("  -> em v0.4.0 a exceção do parser SOBE de _db(); buscar() só captura sqlite3.Error")
    print("  buscar():", s.buscar.__wrapped__ if hasattr(s.buscar,'__wrapped__') else '')
    try:
        print("  buscar(consulta='dano') ->", s.buscar(consulta="dano")[:120])
    except Exception as ex2:
        print(f"  buscar() PROPAGA {type(ex2).__name__}: {ex2}")
    try:
        print("  diagnostico() ->", s.diagnostico()[:120])
    except Exception as ex2:
        print(f"  diagnostico() PROPAGA {type(ex2).__name__}: {ex2}")
    s.parse_secao = orig
    c = s._db()
print("  acórdãos após reindex com parser quebrado:", c.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0])
print("  seções restantes:", c.execute("SELECT COUNT(*) FROM secoes").fetchone()[0])
print("  cobertura() diz:", s.cobertura(c))
print("  arquivos .html.gz ainda em disco:", len([f for f in os.listdir(DEST) if f.endswith('.gz')]))
c.close()
s.parse_secao = orig
print("  parser consertado -> _db() reindexa de novo?")
c = s._db()
print("    acórdãos:", c.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0],
      "· meta parser_versao:", c.execute("SELECT valor FROM meta WHERE chave='parser_versao'").fetchone()[0])
c.close()

print("\n=== D) republicações: a reindexação troca qual edição fica no índice? ===")
shutil.rmtree(s.DIR_BASE, ignore_errors=True)
os.makedirs(DEST, exist_ok=True)
for f in arqs[:1]:
    shutil.copy2(os.path.join(SEC, f), DEST)
f = arqs[0]
ed, cod = f.replace(".html.gz", "").split("-")[:2]
h = gzip.open(os.path.join(DEST, f), "rb").read().decode("utf-8")
itens = s.parse_secao(h)[:5]
con = s._db()
for e in (int(ed), int(ed) + 1):
    con.execute("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)", (e, str(e), "2026-08-31"))
# mesma seção em duas edições: a 2ª vira "republicação"
s.indexar_secao(con, int(ed), int(cod), "Seção X", itens)
s.indexar_secao(con, int(ed) + 1, int(cod), "Seção X", [dict(i, ementa="RETIFICAÇÃO: onde se lê PROVIDO leia-se DESPROVIDO") for i in itens])
shutil.copy2(os.path.join(DEST, f), s._arq_secao(int(ed) + 1, int(cod)))
print("  antes do reindex:",
      con.execute("SELECT edicao, COUNT(*) FROM acordaos GROUP BY edicao").fetchall(),
      "· republicacoes:", con.execute("SELECT COUNT(*) FROM republicacoes").fetchone()[0])
print("   ementa no índice:", con.execute("SELECT ementa FROM acordaos LIMIT 1").fetchone()[0][:60])
con.commit(); con.close()
s.PARSER_VERSAO += 1
con = s._db()
print("  depois do reindex:",
      con.execute("SELECT edicao, COUNT(*) FROM acordaos GROUP BY edicao").fetchall(),
      "· republicacoes:", con.execute("SELECT COUNT(*) FROM republicacoes").fetchone()[0])
print("   ementa no índice:", (con.execute("SELECT ementa FROM acordaos LIMIT 1").fetchone() or ["<vazio>"])[0][:60])
print("   -> _apagar_secao apaga por (edicao, NOME); duas seções com o mesmo nome se apagam mutuamente")
con.close()

print("\n=== E) gz corrompido ===")
shutil.rmtree(s.DIR_BASE, ignore_errors=True)
os.makedirs(DEST, exist_ok=True)
shutil.copy2(os.path.join(SEC, arqs[0]), DEST)
ed, cod = arqs[0].replace(".html.gz", "").split("-")[:2]
con = s._db()
con.execute("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)", (int(ed), str(ed), "2026-08-31"))
s.indexar_secao(con, int(ed), int(cod), "Seção X", s.parse_secao(gzip.open(s._arq_secao(int(ed), int(cod)), "rb").read().decode("utf-8")))
con.close()
open(s._arq_secao(int(ed), int(cod)), "wb").write(b"nao sou gzip")
s.PARSER_VERSAO += 1
con = s._db()
print("  acórdãos:", con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0],
      "· seções:", con.execute("SELECT COUNT(*) FROM secoes").fetchone()[0])
print("  cobertura:", s.cobertura(con))
con.close()

print("\n=== F) base v0.1.0 sem tabela `meta`/`republicacoes` (migração) ===")
shutil.rmtree(s.DIR_BASE, ignore_errors=True)
os.makedirs(s.DIR_BASE, exist_ok=True)
c = sqlite3.connect(s.ARQ_DB)
c.executescript("""CREATE TABLE edicoes(edicao INTEGER PRIMARY KEY, rotulo TEXT, data TEXT);
CREATE TABLE secoes(edicao INTEGER, codigo INTEGER, nome TEXT, itens INTEGER, baixada_em TEXT, PRIMARY KEY(edicao,codigo));
CREATE TABLE acordaos(acordao TEXT PRIMARY KEY, processo TEXT, classe TEXT, recurso TEXT, relator TEXT,
  relator_rotulo TEXT, orgao TEXT, edicao INTEGER, ementa TEXT);
CREATE VIRTUAL TABLE fts USING fts5(acordao UNINDEXED, ementa, classe, relator, tokenize="unicode61 remove_diacritics 2");
INSERT INTO edicoes VALUES(168,'168','2026-08-31');
INSERT INTO secoes VALUES(168,6,'1ª Câmara Cível',3,'2026-09-01T00:00:00');
INSERT INTO acordaos VALUES('202639853','202600000001','Apelação','AC Nº 1/2026','DES. X','RELATOR','1ª Câmara Cível',168,'EMENTA VELHA');
INSERT INTO fts VALUES('202639853','EMENTA VELHA','Apelação','DES. X');""")
c.commit(); c.close()
try:
    con = s._db()
    print("  migração OK · acórdãos:", con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0])
    print("  cobertura:", s.cobertura(con))
    print("  -> o acórdão da base v0.1.0 sobreviveu?",
          con.execute("SELECT COUNT(*) FROM acordaos WHERE acordao='202639853'").fetchone()[0])
    con.close()
except Exception as ex:
    print("  ERRO:", type(ex).__name__, ex)
