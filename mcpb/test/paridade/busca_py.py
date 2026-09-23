"""Roda a bateria de casos_busca.json no PYTHON. Uso: TJSE_DIR_DADOS=<cópia> python3 busca_py.py > busca_py.json"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
import servidor_tjse as s
out = {}
for c in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "casos_busca.json"), encoding="utf-8")):
    out[c["nome"]] = s.mapa_citacoes(**c["p"]) if c.get("mapa") else s.buscar(**c["p"])
print(json.dumps(out, ensure_ascii=False))
