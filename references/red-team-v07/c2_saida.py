import os, sys
os.environ["TJSE_DIR_DADOS"] = "/tmp/rt07"
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S
print(S.buscar(consulta="desconto indevido em beneficio de idoso analfabeto", por_pagina=5)[:5200])
