"""t1b — mede MISS do alerta de TRANSCRIÇÃO em blocos transcritos delimitados à mão,
costura [...] fabricando proposição, e falso ❌ do 'art . 42' que o portal emite."""
import re, sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import *

d3, c3 = teor("03-relatorio-202638463.html")

# Delimitação MANUAL, conferida no fixture: o voto do TJSE vai do início da ementa até ~5.600;
# de 7.116 em diante o texto é ementa/acórdão de OUTROS tribunais (TJ-RO, TJ-MG, TJ-MT) transcritos,
# cada bloco fechado por uma atribuição "(TJ-XX - ...)".
TRANSCRITO = [(7116, 20500), (22303, 35700)]
PROPRIO = [(0, 5600)]
def em(faixas, p): return any(a <= p <= b for a, b in faixas)

print("=== A) 200 janelas de 8-15 palavras: o alerta de TRANSCRIÇÃO pega quanto? ===")
pal = c3.split()
random.seed(11)
st = {"transc_total": 0, "transc_alerta": 0, "prop_total": 0, "prop_alerta": 0}
exemplos = []
for _ in range(600):
    k = random.randint(8, 15)
    i = random.randint(0, len(pal) - k - 1)
    tr = " ".join(pal[i:i + k])
    p = c3.find(tr)
    if p < 0:
        continue
    r = s.conferir(c3, tr)
    if not r["ok"]:
        continue
    a = any("TRANSCRI" in x for x in r.get("alertas", []))
    if em(TRANSCRITO, p):
        if st["transc_total"] >= 200: continue
        st["transc_total"] += 1; st["transc_alerta"] += a
        if not a and len(exemplos) < 3: exemplos.append((p, tr))
    elif em(PROPRIO, p):
        st["prop_total"] += 1; st["prop_alerta"] += a
t, al = st["transc_total"], st["transc_alerta"]
print(f"   DENTRO de bloco transcrito: {t} janelas, alerta em {al} ({100*al/t:.0f}%) "
      f"→ MISS em {t-al} ({100*(t-al)/t:.0f}%): ✅ limpo para palavra de OUTRO tribunal")
pt, pa = st["prop_total"], st["prop_alerta"]
print(f"   NA ementa/fecho do próprio TJSE: {pt} janelas, alerta em {pa} ({100*pa/max(1,pt):.0f}% de falso alarme)")
print("   exemplos de MISS (✅ sem alerta, texto de outro tribunal):")
for p, tr in exemplos:
    print(f"     @{p}: «{tr[:110]}»")

print("\n=== B) costura [...] fabricando proposição que o acórdão não afirma ===")
f1 = "Recurso conhecido e desprovido"          # ementa do TJSE, @650
f2 = "A contratação de empréstimo consignado em nome de menor absolutamente incapaz"  # ementa do TJ-MG transcrita, @10095
tr = f1 + " [...] " + f2
r = s.conferir(c3, tr)
print(f"   trecho: {tr!r}\n   ok={r['ok']} alertas={r.get('alertas')}")
print("   (os dois fragmentos distam", c3.find(f2) - c3.find(f1), "caracteres; não há limite de distância)")

print("\n=== C) falso ❌: o portal emite 'art . 42', 'Des .', 'j . 14.02.2025' ===")
for real, citado in [("CDC, art . 42, parágrafo único", "CDC, art. 42, parágrafo único"),
                     ("Des . Marcos Alaor Diniz Grangeia", "Des. Marcos Alaor Diniz Grangeia"),
                     ("1.0000 .24.449766-5", "1.0000.24.449766-5")]:
    print(f"   texto tem {real!r}: presente={real in c3} | advogado cita {citado!r} -> ok={s.conferir(c3, citado)['ok']}")
