"""Gera trechos determinísticos dos recibos reais e confere no PYTHON. Uso: python3 confere_py.py <dir recibos> > confere_py.json"""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
import servidor_tjse as s
random.seed(20260923)
casos, saida = [], {}
for f in sorted(os.listdir(sys.argv[1])):
    if not f.endswith(".json"): continue
    rec = json.load(open(os.path.join(sys.argv[1], f), encoding="utf-8"))
    d = s.parse_teor(rec["html"]); corpo = d["texto"][d["inicio_conteudo"]:]
    pal = corpo.split()
    for i in range(400):                                   # janelas de 4 a 40 palavras, em posições aleatórias
        n = random.choice([4, 5, 6, 8, 12, 20, 40]); a = random.randrange(0, max(1, len(pal) - n))
        casos.append((f, " ".join(pal[a:a + n])))
    for i in range(80):                                    # dois fragmentos com [...], próximos e distantes
        a = random.randrange(0, max(1, len(pal) - 400)); n1, n2 = random.choice([4, 6]), random.choice([4, 6]); gap = random.choice([5, 30, 150, 400])
        casos.append((f, " ".join(pal[a:a + n1]) + " [...] " + " ".join(pal[a + n1 + gap:a + n1 + gap + n2])))
    casos += [(f, "curto demais"), (f, "   "), (f, "[...]"), (f, "texto que certamente nao existe neste acordao de sergipe")]
for k, (f, t) in enumerate(casos):
    rec = json.load(open(os.path.join(sys.argv[1], f), encoding="utf-8"))
    d = s.parse_teor(rec["html"])
    saida[str(k)] = {"f": f, "t": t, "r": s.conferir(d["texto"][d["inicio_conteudo"]:], t)}
print(json.dumps(saida, ensure_ascii=False))
