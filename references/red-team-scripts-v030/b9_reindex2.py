"""B9 — republicações e reindexação; gz corrompido; base v0.1.0; seção incompleta virando órfã."""
import _base as b
import gzip
import os
import re
import shutil
import sqlite3

s = b.s
SEC = os.path.join(b.RAIZ, "base", "secoes")
arq = sorted(f for f in os.listdir(SEC) if re.fullmatch(r"\d+-\d+\.html\.gz", f))[0]
ed, cod = (int(x) for x in arq.replace(".html.gz", "").split("-"))
BRUTO = gzip.open(os.path.join(SEC, arq), "rb").read().decode("utf-8")


def zerar():
    shutil.rmtree(s.DIR_BASE, ignore_errors=True)
    os.makedirs(s.DIR_SECOES, exist_ok=True)


print("=== D) republicação: a reindexação troca qual EDIÇÃO fica no índice? ===")
zerar()
itens = s.parse_secao(BRUTO)[:5]
con = s._db()
for e in (ed, ed + 1):
    con.execute("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)", (e, str(e), "2026-08-31"))
s.indexar_secao(con, ed, cod, "Câmara X", itens)
s.indexar_secao(con, ed + 1, cod + 1, "Câmara Y",
                [dict(i, ementa="RETIFICACAO: ONDE SE LE PROVIDO LEIA-SE DESPROVIDO. " + i["ementa"]) for i in itens])
s.guardar_bruto(ed, cod, BRUTO)
s.guardar_bruto(ed + 1, cod + 1, BRUTO)
print("  antes :", con.execute("SELECT edicao, COUNT(*) FROM acordaos GROUP BY edicao").fetchall(),
      "· republicacoes:", con.execute("SELECT COUNT(*) FROM republicacoes").fetchone()[0])
con.commit()
con.close()
s.PARSER_VERSAO += 1
con = s._db()
print("  depois:", con.execute("SELECT edicao, COUNT(*) FROM acordaos GROUP BY edicao").fetchall(),
      "· republicacoes:", con.execute("SELECT COUNT(*) FROM republicacoes").fetchone()[0])
print("  -> a reindexação percorre `secoes` na ordem do SELECT; quem for reindexado primeiro fica com o acórdão")
con.close()

print("\n=== E) gz corrompido / página 1 ilegível ===")
zerar()
con = s._db()
con.execute("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)", (ed, str(ed), "2026-08-31"))
s.guardar_bruto(ed, cod, BRUTO)
s.indexar_secao(con, ed, cod, "Câmara X", s.parse_secao(BRUTO))
n0 = con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0]
con.close()
open(s._arq_secao(ed, cod), "wb").write(b"nao sou gzip")
s.PARSER_VERSAO += 1
con = s._db()
print(f"  antes {n0} acórdãos · depois {con.execute('SELECT COUNT(*) FROM acordaos').fetchone()[0]}"
      f" · seções {con.execute('SELECT COUNT(*) FROM secoes').fetchone()[0]}")
print("  cobertura():", s.cobertura(con))
print("  buscar():", s.buscar(consulta="dano")[:200].replace("\n", " | "))
con.close()

print("\n=== E2) seção INCOMPLETA (falta a p2): indexa e depois apaga de `secoes` -> acórdãos ÓRFÃOS ===")
zerar()
con = s._db()
con.execute("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)", (ed, str(ed), "2026-08-31"))
# grava uma p1 que ANUNCIA próxima página e nenhuma p2
h_com_prox = BRUTO + ("<form id=\"wiFormGridNav\"></form>"
                      "<a href=\"#\" onclick=\"submitWIGrid('grid.lista_conteudoDiario', 1000)\" class='nav_go'>Próximo</a>")
s.guardar_bruto(ed, cod, h_com_prox)
s.indexar_secao(con, ed, cod, "Câmara X", s.parse_secao(h_com_prox))
print("  proxima_posicao detectada:", s.proxima_posicao(h_com_prox))
con.commit(); con.close()
s.PARSER_VERSAO += 1
con = s._db()
a = con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0]
sec = con.execute("SELECT COUNT(*) FROM secoes").fetchone()[0]
print(f"  após reindex: acordaos={a} · secoes={sec}")
print("  cobertura():", s.cobertura(con))
print("  diagnostico() 'Por seção':")
for l in s.diagnostico().splitlines():
    if l.startswith("Índice") or l.startswith("  ") or l.startswith("Por seção"):
        print("   ", l)
con.close()

print("\n=== F) base v0.1.0 (sem `meta` nem `republicacoes`): migra? ===")
zerar()
c = sqlite3.connect(s.ARQ_DB)
c.executescript("""CREATE TABLE edicoes(edicao INTEGER PRIMARY KEY, rotulo TEXT, data TEXT);
CREATE TABLE secoes(edicao INTEGER, codigo INTEGER, nome TEXT, itens INTEGER, baixada_em TEXT, PRIMARY KEY(edicao,codigo));
CREATE TABLE acordaos(acordao TEXT PRIMARY KEY, processo TEXT, classe TEXT, recurso TEXT, relator TEXT,
  relator_rotulo TEXT, orgao TEXT, edicao INTEGER, ementa TEXT);
CREATE VIRTUAL TABLE fts USING fts5(acordao UNINDEXED, ementa, classe, relator, tokenize="unicode61 remove_diacritics 2");
INSERT INTO edicoes VALUES(168,'168','2026-08-31');
INSERT INTO secoes VALUES(168,6,'1ª Câmara Cível',3,'2026-09-01T00:00:00');
INSERT INTO acordaos VALUES('202639853','202600000001','Apelação','AC Nº 1/2026','DES. X','RELATOR','1ª Câmara Cível',168,'EMENTA VELHA DE DANO MORAL');
INSERT INTO fts VALUES('202639853','EMENTA VELHA DE DANO MORAL','Apelação','DES. X');""")
c.commit(); c.close()
con = s._db()
print("  acórdãos após migração:", con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0],
      "· seções:", con.execute("SELECT COUNT(*) FROM secoes").fetchone()[0])
print("  cobertura():", s.cobertura(con))
print("  buscar('dano'):", s.buscar(consulta="dano")[:230].replace("\n", " | "))
con.close()
