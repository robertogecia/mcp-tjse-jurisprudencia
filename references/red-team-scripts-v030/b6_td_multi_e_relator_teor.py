"""B6 — <td> com mais de um acórdão (ementa engolindo a vizinha), rótulo só na CAUDA,
e relator do Boletim x cabeçalho RELATOR do inteiro teor (fixtures 03/08)."""
import _base as b
import collections
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

print("=== A) <td> com MAIS DE UM link relatorio.wsp: o 1º acórdão da célula se perde? ===")
tot_td = multi = perdidos = 0
ex = []
for arq in ARQS:
    h = gzip.open(arq, "rb").read().decode("utf-8").replace("<!--", "").replace("-->", "")
    itens = {i["acordao"] for i in s.parse_secao(gzip.open(arq, "rb").read().decode("utf-8"))}
    for td in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", h):
        lks = list(s._RE_LINK_TEOR.finditer(td))
        if not lks:
            continue
        tot_td += 1
        acs = {(m.group(2) or m.group(3)) for m in lks}
        if len(acs) > 1:
            multi += 1
            falta = acs - itens
            perdidos += len(falta)
            if len(ex) < 3:
                ex.append((os.path.basename(arq), sorted(acs), sorted(falta)))
print(f"  {tot_td} células com link · {multi} com mais de um acórdão · {perdidos} acórdãos perdidos")
for a, acs, falta in ex:
    print(f"    {a}: acórdãos na célula {acs} · fora do índice {falta}")

print("\n=== B) <table>/<td> ANINHADO dentro da célula (a regex não-gulosa corta no 1º </td>) ===")
n_nest = 0
for arq in ARQS:
    h = gzip.open(arq, "rb").read().decode("utf-8").replace("<!--", "").replace("-->", "")
    for td in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", h):
        if re.search(r"(?is)<t[dr]\b|<table\b", td):
            n_nest += 1
print(f"  células com <td>/<tr>/<table> aninhado: {n_nest}")

print("\n=== C) rótulo de relator não reconhecido NA CAUDA (após o link), não na ementa ===")
rot_cauda = collections.Counter()
maus = []
for arq in ARQS:
    h = gzip.open(arq, "rb").read().decode("utf-8").replace("<!--", "").replace("-->", "")
    for td in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", h):
        lk = s._RE_LINK_TEOR.search(td)
        if not lk:
            continue
        cauda = s.limpar_html(td[lk.end():])
        cauda = re.sub(r"(?i)(?<=\S)(?=RELATOR(?:\(A\)|A)?\s+(?:ORIGIN|DESIGN|PARA\s+O|SUBSTIT|CONVOC))", "\n", cauda)
        for l in (x.strip() for x in cauda.split("\n")):
            m = re.match(r"(?i)^(RELATOR[A-ZÀ-Ü()\s]{0,40}?)\s*:", l)
            if m:
                r = re.sub(r"\s+", " ", m.group(1).upper())
                rot_cauda[r] += 1
                if not s._RE_ROT_RELATOR.match(l) and len(maus) < 6:
                    maus.append((os.path.basename(arq), lk.group(2) or lk.group(3), l[:90]))
for r, n in rot_cauda.most_common():
    print(f"  {n:5d}  {r!r:36s} reconhecido: {bool(s._RE_ROT_RELATOR.match(r + ': X'))}")
print("  linhas de CAUDA não casadas pela regex:")
for a, ac, l in maus:
    print(f"    {a} acórdão {ac}: {l!r}")

print("\n=== D) relator do BOLETIM x cabeçalho RELATOR do INTEIRO TEOR (fixtures 03/08) ===")
alvo = {}
for arq in ARQS:
    for i in s.parse_secao(gzip.open(arq, "rb").read().decode("utf-8")):
        if i["acordao"] in ("202638463", "202640467"):
            alvo[i["acordao"]] = (os.path.basename(arq), i)
for fx, ac in (("03-relatorio-202638463.html", "202638463"), ("08-relatorio-202640467.html", "202640467")):
    d = s.parse_teor(b.fx(fx))
    print(f"\n  acórdão {ac}")
    print(f"    teor   · campo RELATOR = {d['relator']!r}")
    print(f"    teor   · citacao() usaria = {s.nome_proprio(d['relator'])!r}")
    if ac in alvo:
        arq, i = alvo[ac]
        print(f"    boletim ({arq}) · rotulo={i['relator_rotulo']!r}")
        print(f"    boletim · relator={i['relator']!r}")
        print(f"    IGUAL? {s.norm(i['relator']) == s.norm(d['relator'])}")
    else:
        print("    (não está em nenhuma seção guardada)")
