"""Despeja, do parser PYTHON (referência), um hash por campo de cada acórdão do HTML bruto em base/secoes/.
Uso: TJSE_DIR_DADOS=<pasta com base/secoes> python3 dump_py.py > py.jsonl"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
import servidor_tjse as s

h = lambda x: hashlib.sha1(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
pares = sorted({(int(a), int(b)) for a, b in (
    (n.split("-")[0], n.split("-")[1].split(".")[0]) for n in os.listdir(s.DIR_SECOES) if n.endswith(".html.gz"))})
for ed, cod in pares:
    pags, _ = s.paginas_em_disco(ed, cod)
    for it in s.parse_secao("\n".join(pags)):
        cps = s.campos_da_ementa(it["ementa"])
        rec = {"id": it["acordao"], "ed": ed, "cod": cod,
               **{"f_" + k: h(v) for k, v in it.items()},
               **{"c_" + k: h(v) for k, v in cps.items()},
               "cit": h(s.citacoes_da_ementa(cps, it["ementa"])),
               "anc": h(s.ancoras(it["ementa"], 12)),
               "res": h(s.resultado_declarado(it["ementa"])),
               "norm": h(s.norm(it["ementa"]))}
        print(json.dumps(rec))
