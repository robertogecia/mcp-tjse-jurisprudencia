"""Compara py.jsonl e node.jsonl: mesmos acórdãos, mesmos hashes por campo. Sai 1 se houver qualquer diferença."""
import collections, json, sys
lê = lambda p: {(r["ed"], r["cod"], r["id"]): r for r in map(json.loads, open(p, encoding="utf-8"))}
py, nd = lê(sys.argv[1]), lê(sys.argv[2])
print(f"acórdãos: python {len(py)} · node {len(nd)}")
só_py, só_nd = set(py) - set(nd), set(nd) - set(py)
if só_py or só_nd: print(f"SÓ NO PYTHON: {len(só_py)} · SÓ NO NODE: {len(só_nd)}")
dif = collections.Counter(); exemplos = {}
for k in set(py) & set(nd):
    for campo, v in py[k].items():
        if nd[k].get(campo) != v:
            dif[campo] += 1; exemplos.setdefault(campo, k)
if dif:
    print("CAMPOS DIVERGENTES:"); [print(f"  {c}: {n}  (ex.: ed/cod/acórdão {exemplos[c]})") for c, n in dif.most_common()]
    sys.exit(1)
print("PARIDADE TOTAL" if not (só_py or só_nd) else "campos idênticos, mas conjuntos diferem"); sys.exit(1 if (só_py or só_nd) else 0)
