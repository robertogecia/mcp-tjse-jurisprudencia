"""B5 — rótulos de relator não reconhecidos, 'VAGA DE DESEMBARGADOR', ementas gigantes, relator duplo."""
import _base as b
import glob
import gzip
import os
import re
import shutil
import tempfile

s = b.s
TMP = tempfile.mkdtemp(prefix="tjse-secoes-")
for f in glob.glob(os.path.join(b.RAIZ, "base", "secoes", "*.html.gz")):
    shutil.copy2(f, TMP)
ARQS = sorted(glob.glob(os.path.join(TMP, "*.html.gz")))
RE_LINK = s._RE_LINK_TEOR


def tds(arq):
    h = gzip.open(arq, "rb").read().decode("utf-8").replace("<!--", "").replace("-->", "")
    return h, re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", h)


print("=== A) rótulos que a regex NÃO reconhece: o que o parser grava nesses itens ===")
alvos = ("RELATOR (A)", "RELATOR JUIZ CONVOCADO", "RELATORA SUBSTITUTOA", "RELATORIA JÁ SE PRONUNCIOU")
achados = {a: [] for a in alvos}
for arq in ARQS:
    h, cels = tds(arq)
    itens = {i["acordao"]: i for i in s.parse_secao(gzip.open(arq, "rb").read().decode("utf-8"))}
    for td in cels:
        lk = RE_LINK.search(td)
        if not lk:
            continue
        txt = s.limpar_html(td)
        for a in alvos:
            if re.search(re.escape(a) + r"\s*:", txt, re.I):
                ac = lk.group(2) or lk.group(3)
                it = itens.get(ac)
                if it and len(achados[a]) < 3:
                    bruto = re.search(r"(?i)" + re.escape(a) + r"\s*:\s*([^\n]{0,60})", txt)
                    achados[a].append((os.path.basename(arq), ac, bruto.group(0)[:75] if bruto else "",
                                       it["relator_rotulo"], it["relator"], it["recurso"]))
for a, v in achados.items():
    print(f"\n  rótulo {a!r}:")
    for arq, ac, bruto, rot, rel, rec in v:
        print(f"    {arq} acórdão {ac}\n      bruto : {bruto!r}\n      parser: rotulo={rot!r}\n"
              f"              relator={rel!r}\n              recurso={rec!r}")

print("\n=== B) 'VAGA DE DESEMBARGADOR' como relator: o que existe na célula ===")
n = 0
for arq in ARQS:
    itens = s.parse_secao(gzip.open(arq, "rb").read().decode("utf-8"))
    vagos = [i for i in itens if "VAGA DE DESEMBARGADOR" in i["relator"].upper()]
    if vagos:
        print(f"  {os.path.basename(arq)}: {len(vagos)}/{len(itens)} itens com relator 'VAGA DE DESEMBARGADOR'")
        n += len(vagos)
        for i in vagos[:2]:
            print(f"    acórdão {i['acordao']} · rotulo={i['relator_rotulo']!r}\n      relator={i['relator']!r}")
            print(f"      citacao() diria: Rel. {s.nome_proprio(i['relator'])}")
print(f"  TOTAL: {n} itens")

print("\n=== C) ementas anômalas (>4x mediana): engoliram a vizinha? ===")
for arq in ARQS:
    itens = s.parse_secao(gzip.open(arq, "rb").read().decode("utf-8"))
    for i in itens:
        if len(i["ementa"]) > 11000:
            em = i["ementa"]
            print(f"  {os.path.basename(arq)} acórdão {i['acordao']}: {len(em)} chars")
            print(f"    início: …{em[:110]}…")
            print(f"    fim   : …{em[-110:]}…")
            marcas = len(re.findall(r"(?i)\bEMENTA\b", em))
            print(f"    ocorrências de 'EMENTA' dentro: {marcas} · 'ACÓRDÃO N' dentro: {len(re.findall(r'(?i)ACORD[AÃ]O N', em))}")

print("\n=== D) relator duplo (ORIGINÁRIO + PARA O ACÓRDÃO/DESIGNADO): quem o parser cita ===")
for arq in ARQS:
    itens = s.parse_secao(gzip.open(arq, "rb").read().decode("utf-8"))
    duplos = [i for i in itens if "há também" in i["relator_rotulo"]]
    if duplos:
        print(f"  {os.path.basename(arq)}: {len(duplos)} itens com dois rótulos")
        for i in duplos[:3]:
            print(f"    {i['acordao']}: relator={i['relator']!r}\n      rotulo={i['relator_rotulo']!r}")

print("\n=== E) nome_proprio(): partículas, apóstrofo, JÚNIOR/NETO, abreviação ===")
for x in ("DES. MARIA D'ÁVILA DE SOUZA JÚNIOR", "DESA. ANA LÚCIA FREIRE DE ALMEIDA DOS ANJOS",
          "DES. CEZÁRIO SIQUEIRA NETO", "DE OLIVEIRA FRAGA", "DES(A) VAGA DE DESEMBARGADOR (G-21)",
          "ROBERTO EUGÊNIO DA FONSECA PORTO", "JOSÉ DOS ANJOS-FILHO", "DES. RUY PINHEIRO DA SILVA"):
    print(f"  {x!r:48s} -> {s.nome_proprio(x)!r}")
