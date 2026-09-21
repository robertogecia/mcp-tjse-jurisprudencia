"""t3 — saída e recibos: promessa de 'partes omitidas', 'inteiro teor lido' com corte,
.title() no relator, e recibo com HTML de OUTRO acórdão."""
import asyncio, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import *

H3, H8 = fx("03-relatorio-202638463.html"), fx("08-relatorio-202640467.html")
s.gravar_recibo("202638463", "202600737656", H3)
s.gravar_recibo("202640467", "202600823569", H8)

print("=== A) `com_partes=False` promete omitir partes — o RELATÓRIO as nomeia assim mesmo ===")
o = asyncio.run(s.obter("202640467"))
print("   linha da promessa:", [l for l in o.split("\n") if "omitid" in l])
for nome in ["MÔNICA SANTOS", "M.F.S.", "menor impúbere", "BANCO"]:
    print(f"   {nome!r:20} aparece na saída com com_partes=False: {nome in o}")
i = o.find("menor impúbere")
print("   contexto:", repr(re.sub(r"\s+", " ", o[i-180:i+90])))

print("\n=== B) `inteiro teor lido` mesmo com o corpo cortado por max_caracteres ===")
o = asyncio.run(s.obter("202638463", max_caracteres=500))
print("   " + [l for l in o.split("\n") if l.startswith("Citação:")][0])
print("   " + [l for l in o.split("\n") if "cortado em" in l][0])

print("\n=== C) verificar() com recibo cortado? (verificar usa o texto inteiro) e .title() no relator ===")
v = asyncio.run(s.verificar("202638463", "voto pelo desprovimento do recurso"))
print("   " + [l for l in v.split("\n") if l.startswith("Citação:")][0])
d = s.parse_teor(H3)
print("   relator no cabeçalho:", repr(d["relator"]), "-> .title() ->", repr(d["relator"].title()))
for n in ["ANA LÚCIA FREIRE DE ALMEIDA DOS ANJOS", "JOSÉ D'ÁVILA DE OLIVEIRA", "MARIA DA CONCEIÇÃO SILVA"]:
    print(f"   {n!r}\n      -> {n.title()!r}")

print("\n=== D) recibo com o HTML de OUTRO acórdão: nenhuma reconferência na leitura ===")
p = s._arq_recibo("202638463")
rec = json.load(open(p))
rec["html"] = H8                      # conteúdo do acórdão 202640467
json.dump(rec, open(p, "w"), ensure_ascii=False)   # sha256 do recibo NÃO é recalculado nem conferido
o = asyncio.run(s.obter("202638463"))
print("   " + "\n   ".join(o.split("\n")[:5]))
print("   Citação:", [l for l in o.split("\n") if l.startswith("Citação:")][0][:200])
print("\n   verificar() contra esse recibo, com trecho que só existe no OUTRO acórdão:")
v = asyncio.run(s.verificar("202638463", "Constatada a tempestividade do Agravo de Instrumento"))
print("   " + "\n   ".join(v.split("\n")[:4]))

print("\n=== E) permissões de recibos/ quando a pasta já existe com 0755 ===")
import shutil, stat
shutil.rmtree(s.DIR_RECIBOS, ignore_errors=True)
os.makedirs(s.DIR_RECIBOS, mode=0o755)
os.chmod(s.DIR_RECIBOS, 0o755)
s.gravar_recibo("202638463", "202600737656", H3)
print("   modo da pasta após gravar_recibo:", oct(os.stat(s.DIR_RECIBOS).st_mode)[-3:],
      "(README promete 0700)")

print("\n=== F) path traversal no nº do acórdão ===")
print("   _arq_recibo('../../fora'):", s._arq_recibo("../../fora"))
try:
    print("   obter('../../fora'):", asyncio.run(s.obter("../../fora"))[:110])
except Exception as ex:
    print("   obter levantou", type(ex).__name__, ex)
