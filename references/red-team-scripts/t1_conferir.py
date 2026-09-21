"""t1 — conferir(): falso ✅ por costura de fragmentos, taxa de alerta, negação, piso."""
import random, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import *

d3, c3 = teor("03-relatorio-202638463.html")
d8, c8 = teor("08-relatorio-202640467.html")

print("=== A) [...] costura EMENTA do TJSE + EMENTA do TJ-RO transcrita (falso ✅) ===")
# fragmento 1: da ementa do próprio TJSE; fragmento 2: de ementa do TJ-RO transcrita no voto
f1 = "AGRAVO DE INSTRUMENTO"
i = c3.find("CONTRATAÇÃO REALIZADA EM NOME DE MENOR ABSOLUTAMENTE INCAPAZ")
f2 = c3[i:i+95]
r = s.conferir(c3, f1 + " [...] " + f2)
print("   trecho:", repr((f1 + " [...] " + f2)[:130]))
print("   ok =", r["ok"], "| alertas =", r.get("alertas"))

print("\n=== B) trecho que atravessa EMENTA -> fecho -> nome do desembargador ===")
j = c3.find("Vistos, relatados")
cross = re.sub(r"\s+", " ", c3[j-70:j+130])
r = s.conferir(c3, cross)
print("   trecho:", repr(cross))
print("   ok =", r["ok"], "| alertas =", r.get("alertas"))

print("\n=== C) piso: trecho de 1 e de 2 palavras ===")
for t in ["de", "o recurso", "a", "nos autos"]:
    r = s.conferir(c3, t)
    print(f"   {t!r:14} ok={r['ok']} alertas={r.get('alertas')}")

print("\n=== D) fragmentos degenerados ===")
for t in ["[...]", "[...] [...]", "recurso [...] recurso", "a [...] a [...] a"]:
    r = s.conferir(c3, t)
    print(f"   {t!r:24} -> {r}" if not r["ok"] else f"   {t!r:24} ok=True alertas={r.get('alertas')}")

print("\n=== E) taxa de alerta de TRANSCRIÇÃO em 200 janelas reais de 8-15 palavras ===")
# bloco realmente transcrito = do 1º 'EMENTA:'/'Ementa:' interno em diante até o fim do bloco citado
def blocos_transcritos(txt):
    bl = []
    for m in re.finditer(r"(?m)^(?:EMENTA|Ementa):", txt):
        bl.append((m.start(), m.start() + 4500))
    for m in re.finditer(r"(?i)\((?:TJ-?[A-Z]{2}|STJ|STF)\b", txt):
        bl.append((max(0, m.start() - 4500), m.start() + 200))
    return bl

for nome, corpo in (("03", c3), ("08", c8)):
    bl = blocos_transcritos(corpo)
    pal = corpo.split()
    random.seed(7)
    tot = alerta = dentro = alerta_fora = fora = 0
    for _ in range(200):
        k = random.randint(8, 15)
        p = random.randint(0, len(pal) - k - 1)
        tr = " ".join(pal[p:p + k])
        pos = corpo.find(tr)
        if pos < 0:
            continue
        tot += 1
        eh_transc = any(a <= pos <= b for a, b in bl)
        r = s.conferir(corpo, tr)
        if not r["ok"]:
            continue
        a = any("TRANSCRI" in x for x in r.get("alertas"))
        alerta += a
        dentro += eh_transc
        if not eh_transc:
            fora += 1
            alerta_fora += a
    print(f"   fixture {nome}: {tot} janelas | alerta de TRANSCRIÇÃO em {alerta} ({100*alerta/tot:.0f}%) | "
          f"janelas REALMENTE em bloco transcrito: {dentro} ({100*dentro/tot:.0f}%) | "
          f"alerta FORA de bloco transcrito: {alerta_fora}/{fora} ({100*alerta_fora/max(1,fora):.0f}% de falso alarme)")

print("\n=== F) negação NÃO detectada ===")
casos = [
 ("não é devido o dano moral", "é devido o dano moral"),
 ("improcedente o pedido de indenização por danos morais", "o pedido de indenização por danos morais"),
 ("nega-se provimento ao recurso do banco réu", "provimento ao recurso do banco réu"),
 ("rejeita-se a tese de prescrição quinquenal", "a tese de prescrição quinquenal"),
 ("sem razão a parte agravante quanto à gratuidade", "a parte agravante quanto à gratuidade"),
 ("não se aplica o Código de Defesa do Consumidor", "o Código de Defesa do Consumidor"),
]
for contexto, trecho in casos:
    txt = "EMENTA\n" + "palavra " * 40 + contexto + " e prossegue o julgamento."
    r = s.conferir(txt, trecho)
    neg = any("NEGA" in x for x in r.get("alertas")) if r["ok"] else None
    print(f"   contexto {contexto!r}\n      -> ok={r['ok']} alerta_negacao={neg}")

print("\n=== G) falso alerta de negação (o 'não' é inócuo) ===")
for contexto, trecho in [
 ("não obstante o alegado, o contrato é válido e obriga as partes", "o contrato é válido e obriga as partes"),
 ("questão que não se confunde com a prescrição, o dano moral é devido", "o dano moral é devido")]:
    txt = "EMENTA\n" + "palavra " * 40 + contexto
    r = s.conferir(txt, trecho)
    print(f"   {contexto!r} -> alertas={r.get('alertas')}")

print("\n=== H) normalização ===")
for t in ["art. 1.691 do código civil", "art. 1691 do código civil", "art . 1.691 do código civil",
          "ART. 1.691 DO CÓDIGO CIVIL"]:
    print(f"   {t!r:38} ok={s.conferir(c3, t)['ok']}")
print("   contexto devolvido (normalizado, sem acento):")
print("   ", s.conferir(c3, "art. 1.691 do código civil")["contexto"][:160])
