import os, sys
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
for ref in ("Súmula 297", "Súmula 297/STJ", "súmula 297 do STJ", "Tema 1061", "Súmula 9999", "IRDR 15", "SV 47", "banana"):
    print(f"cita={ref!r:22s} → _ref_citada={S._ref_citada(ref)}  | mapa: {S.mapa_citacoes(ref, 3).splitlines()[0][:110]}")
print()
print("limite absurdo:", S.mapa_citacoes("Tema 1061", 10**9).splitlines()[0][:80])
print("limite negativo:", S.mapa_citacoes("Tema 1061", -5).splitlines()[0][:80])
print()
print("=== busca cita='Súmula 297' vs 'Súmula 297/STJ'")
for r in ("Súmula 297", "Súmula 297/STJ"):
    print(" ", r, "→", S.buscar(cita=r, por_pagina=5).splitlines()[1][:120])
