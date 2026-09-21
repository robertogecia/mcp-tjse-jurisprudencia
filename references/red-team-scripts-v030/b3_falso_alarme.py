"""B3 — FALSO ALARME das heurísticas 'ini = piso' (blocos em sequência) e fallback de 1.200 chars:
palavra PRÓPRIA do TJSE entre duas citações / logo antes de uma citação é marcada TRANSCRIÇÃO."""
import _base as b

s = b.s
d3, c3 = b.teor("03-relatorio-202638463.html")
t3 = s.norm(c3)
d8, c8 = b.teor("08-relatorio-202640467.html")
t8 = s.norm(c8)

fecho = t3[1505:1505 + 600]                       # fecho real do TJSE
bloco_ro = t3[6892:7087]                          # bloco transcrito TJ-RO (com atribuição)
bloco_mg = t3[11198:11400] + " " + t3[10950:11197]  # outro bloco com atribuição TJ-MG
# voto PRÓPRIO do TJSE, texto real do fixture 08 (razões do relator, fora de qualquer faixa)
proprio = t8[6300:7400]

print("len(proprio) =", len(proprio))
print("«" + proprio[:160] + "…»")

for rot, meio in (("voto próprio de ~1.100 chars ENTRE dois blocos transcritos", proprio),
                  ("voto próprio de ~500 chars ENTRE dois blocos transcritos", proprio[:500]),
                  ("voto próprio de ~5.500 chars ENTRE dois blocos transcritos", (proprio * 5)[:5500])):
    doc = fecho + " " + bloco_ro + " " + meio + " " + bloco_mg
    tre = " ".join(meio.split()[8:22])
    r = s.conferir(doc, tre)
    al = [x[:12] for x in r.get("alertas", [])]
    print(f"\n  {rot}\n    trecho «{tre[:80]}»\n    ok={r['ok']} alertas={al}"
          f"  -> {'FALSO ALARME' if 'TRANSCRIÇÃO:' in al else 'ok'}")

print("\n=== fallback de 1.200 chars: voto próprio logo ANTES da 1ª citação ===")
doc = fecho + " " + proprio + " " + bloco_ro
for off in (0, 400, 900):
    tre = " ".join(proprio[off:off + 400].split()[1:15])
    r = s.conferir(doc, tre)
    al = [x[:12] for x in r.get("alertas", [])]
    dist = len(proprio) - off
    print(f"  a ~{dist} chars antes da atribuição: alertas={al} "
          f"-> {'FALSO ALARME' if 'TRANSCRIÇÃO:' in al else 'ok'}")

print("\n=== atribuição BANAL criando faixa do nada ===")
for banal in ("(ai, rel. de forma clara, decidiu o juizo)", "(ac. unanime, rel. do voto condutor)",
              "(ms, rel. pelo proprio autor)"):
    doc = fecho + " " + proprio + " " + banal + " " + proprio[:300]
    tre = " ".join(proprio[200:600].split()[1:15])
    r = s.conferir(doc, tre)
    al = [x[:12] for x in r.get("alertas", [])]
    print(f"  {banal!r:45s} -> alertas={al} {'FALSO ALARME' if 'TRANSCRIÇÃO:' in al else ''}")
