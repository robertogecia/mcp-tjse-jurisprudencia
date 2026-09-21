"""B4 — parse_secao em ESCALA sobre base/secoes/*.html.gz (copiados para temp, só leitura).
Extração independente: links relatorio.wsp únicos, rótulos de relator do bruto, resíduos na ementa."""
import _base as b
import collections
import glob
import gzip
import os
import re
import shutil
import tempfile

s = b.s
ORIG = os.path.join(b.RAIZ, "base", "secoes")
TMP = tempfile.mkdtemp(prefix="tjse-secoes-")
for f in glob.glob(os.path.join(ORIG, "*.html.gz")):
    shutil.copy2(f, TMP)

RE_LINK = re.compile(r"relatorio\.wsp\?(?:tmp\.numprocesso=(\d+)&(?:amp;)?tmp\.numacordao=(\d+)"
                     r"|tmp\.numacordao=(\d+)&(?:amp;)?tmp\.numprocesso=(\d+))")
RE_ROT_BRUTO = re.compile(r"(?i)\b(RELATOR[A-ZÀ-Ü\(\)\s]{0,40}?)\s*:")

tot_itens = tot_links = 0
div = collections.Counter()
exemplos = collections.defaultdict(list)
rotulos_bruto = collections.Counter()
rotulos_reconhecidos = collections.Counter()
tam = []

for arq in sorted(glob.glob(os.path.join(TMP, "*.html.gz"))):
    h = gzip.open(arq, "rb").read().decode("utf-8")
    hs = h.replace("<!--", "").replace("-->", "")
    links = {(m.group(1) or m.group(4), m.group(2) or m.group(3)) for m in RE_LINK.finditer(hs)}
    itens = s.parse_secao(h)
    tot_itens += len(itens)
    tot_links += len(links)
    acs_link = {a for _, a in links}
    acs_item = {i["acordao"] for i in itens}
    print(f"\n## {os.path.basename(arq)}: {len(itens)} itens · {len(links)} pares (proc,acórdão) únicos "
          f"· {len(acs_link)} acórdãos únicos no bruto")
    if acs_link - acs_item:
        div["acórdão no bruto SEM item"] += len(acs_link - acs_item)
        exemplos["acórdão no bruto SEM item"] += sorted(acs_link - acs_item)[:3]
    if acs_item - acs_link:
        div["item sem link no bruto"] += len(acs_item - acs_link)
    # um acórdão com DOIS processos diferentes no bruto?
    porac = collections.defaultdict(set)
    for p, a in links:
        porac[a].add(p)
    amb = {a: v for a, v in porac.items() if len(v) > 1}
    if amb:
        div["acórdão com >1 processo no bruto"] += len(amb)
        exemplos["acórdão com >1 processo no bruto"] += [f"{a}->{sorted(v)}" for a, v in list(amb.items())[:3]]

    for i in itens:
        em, ac = i["ementa"], i["acordao"]
        tam.append((len(em), ac, os.path.basename(arq)))
        for pad, rot in ((r"(?i)\bPROCESSO\s*:", "resíduo 'PROCESSO:' na ementa"),
                         (r"(?i)\bACORD[AÃ]O\s*:", "resíduo 'ACÓRDÃO:' na ementa"),
                         (r"(?i)\bRELATOR", "resíduo 'RELATOR' na ementa"),
                         (r"<[a-zA-Z/!]", "HTML cru na ementa"),
                         (r"&[a-zA-Z#]{2,8};", "entidade crua na ementa"),
                         (r"relatorio\.wsp", "link cru na ementa")):
            if re.search(pad, em):
                div[rot] += 1
                if len(exemplos[rot]) < 3:
                    exemplos[rot].append(f"{ac}: …{em[max(0,re.search(pad,em).start()-45):re.search(pad,em).start()+55]}…")
        if not em:
            div["ementa VAZIA"] += 1
            exemplos["ementa VAZIA"].append(ac)
        if i["recurso"] and not re.search(r"N[ºo°]\s*\d", i["recurso"]):
            div["recurso fora do formato"] += 1
        if not i["recurso"]:
            div["recurso VAZIO"] += 1
            if len(exemplos["recurso VAZIO"]) < 3:
                exemplos["recurso VAZIO"].append(f"{ac} (classe={i['classe']!r})")
        if not i["relator"]:
            div["relator VAZIO"] += 1
            if len(exemplos["relator VAZIO"]) < 3:
                exemplos["relator VAZIO"].append(ac)
        elif not re.match(r"(?i)^(des|dr|jui|min)[a-zà-ü]*\.?\s", i["relator"]) and len(i["relator"]) > 4:
            div["relator sem tratamento (DES./DR.)"] += 1
            if len(exemplos["relator sem tratamento (DES./DR.)"]) < 3:
                exemplos["relator sem tratamento (DES./DR.)"].append(f"{ac}: {i['relator'][:60]!r}")
        if re.search(r"(?i)relator|ementa|processo\s*:", i["relator"] or ""):
            div["relator com lixo dentro"] += 1
            if len(exemplos["relator com lixo dentro"]) < 3:
                exemplos["relator com lixo dentro"].append(f"{ac}: {i['relator'][:80]!r}")
        if not i["classe"]:
            div["classe VAZIA"] += 1
        rotulos_reconhecidos[i["relator_rotulo"].split(" (há também")[0]] += 1
    print("   anomalias_secao:", s.anomalias_secao(itens))

    for td in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", hs):
        if not RE_LINK.search(td):
            continue
        for m in RE_ROT_BRUTO.finditer(s.limpar_html(td)):
            rotulos_bruto[re.sub(r"\s+", " ", m.group(1).strip().upper())] += 1

print("\n" + "=" * 78)
print(f"TOTAL: {tot_itens} itens parseados · {tot_links} pares (proc,acórdão) únicos no bruto")
print("\nDIVERGÊNCIAS por tipo:")
for k, v in div.most_common():
    print(f"  {v:5d}  {k}")
    for e in exemplos[k][:3]:
        print(f"           ex.: {e}")

print("\nRÓTULOS de relator DISTINTOS no HTML bruto (contagem):")
nao_reconh = []
for r, n in rotulos_bruto.most_common():
    ok = bool(s._RE_ROT_RELATOR.match(r + ": X"))
    print(f"  {n:5d}  {r!r:46s} reconhecido pela regex: {ok}")
    if not ok:
        nao_reconh.append((r, n))
print("\nRÓTULOS que a regex do parser NÃO reconhece:", nao_reconh or "nenhum")

print("\nRÓTULOS que o parser GRAVOU:")
for r, n in rotulos_reconhecidos.most_common(15):
    print(f"  {n:5d}  {r!r}")

tam.sort()
print("\nTAMANHO de ementa — 5 menores e 5 maiores:")
for t, ac, a in tam[:5] + tam[-5:]:
    print(f"  {t:7d}  acórdão {ac} ({a})")
import statistics
print(f"  mediana {statistics.median(x[0] for x in tam):.0f} · média {statistics.mean(x[0] for x in tam):.0f}")
print("  ementas > 4x a mediana (engoliu a vizinha?):")
med = statistics.median(x[0] for x in tam)
for t, ac, a in tam:
    if t > 4 * med:
        print(f"    {t} chars · acórdão {ac} ({a})")
