import os, sys
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
CASOS = ["de a o para", "de prescricao", 'prescricao "dano moral"', '"dano moral" indenizacao consumidor',
         "agravo de instrumento", "recurso especial repetitivo", "direito processual civil",
         "nao incidencia de juros de mora", "dano moral", "sem justa causa"]
for c in CASOS:
    try:
        p = S.partes_fts(c, None)
        print(f"{c!r:38s} → obrig={[r for r,_,o in p if o]} opc={[r for r,_,o in p if not o]}")
    except ValueError as e:
        print(f"{c!r:38s} → RECUSADA: {str(e)[:110]}")
print()
print("exato=True com soltas:", S.montar_fts("desconto indevido beneficio", None, exato=True))
print("aspas+soltas:", S.montar_fts('"dano moral" desconto idoso', None))
print("grupos+consulta:", S.montar_fts("idoso analfabeto", [["desconto","cobranca"]]))
print()
print("em=' ' →", S.buscar(grupos=[["prescricao"]], em=" ")[:130])
print("em='' →", S.buscar(grupos=[["prescricao"]], em="").splitlines()[1][:90])
