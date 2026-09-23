"""Compara, tabela a tabela, o banco montado pelo NODE (do HTML bruto) com o banco do PYTHON. Uso: python3 indice_cmp.py <boletim.db python> <boletim.db node>"""
import hashlib, sqlite3, sys
py, nd = sqlite3.connect(sys.argv[1]), sqlite3.connect(sys.argv[2])
def h(con, sql):
    x = hashlib.sha256(); n = 0
    for r in con.execute(sql): x.update(repr(r).encode()); n += 1
    return n, x.hexdigest()[:16]
casos = {"acordaos": "SELECT * FROM acordaos ORDER BY acordao", "campos": "SELECT * FROM campos ORDER BY acordao",
         "citacoes": "SELECT * FROM citacoes ORDER BY origem, tipo, ref",
         "secoes": "SELECT edicao, codigo, nome, itens FROM secoes ORDER BY edicao, codigo",
         "republicacoes": "SELECT * FROM republicacoes ORDER BY acordao, edicao",
         "fts": "SELECT acordao, ementa, classe, relator FROM fts ORDER BY acordao",
         "fts_campos": "SELECT acordao, cabecalho, caso, questao, razoes, dispositivo, tese FROM fts_campos ORDER BY acordao",
         "vocabulario": "SELECT term, doc, cnt FROM fts_vocab ORDER BY term",
         # o rótulo vem de fontes diferentes (listagem do portal x cabeçalho da página) e nunca aparece em saída: só edição e data contam
         "edicoes(edicao,data)": "SELECT edicao, data FROM edicoes WHERE edicao IN (SELECT edicao FROM secoes) ORDER BY edicao"}
ok = True
for nome, sql in casos.items():
    a, b = h(py, sql), h(nd, sql); ok &= a == b
    print(f"{'ok  ' if a == b else 'DIFF'} {nome:22s} python {a[0]:>6} · node {b[0]:>6}")
print("INDICE IDENTICO" if ok else "INDICE DIVERGE"); sys.exit(0 if ok else 1)
