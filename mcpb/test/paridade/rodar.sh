#!/usr/bin/env bash
# Paridade Python × Node sobre o corpus REAL (precisa do Python 3, do índice em ../../../base e de ../../../recibos).
# Roda tudo numa CÓPIA: nada do índice nem dos recibos originais é tocado. Sai com erro se algo divergir.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"; PY="$AQUI/../../.."; BASE_REAL="${TJSE_BASE_REAL:-$PY}"
[ -f "$BASE_REAL/base/boletim.db" ] || { echo "sem índice real em $BASE_REAL/base (defina TJSE_BASE_REAL)"; exit 2; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/copia/base" "$T/build/base"
cp "$BASE_REAL/base/boletim.db" "$T/copia/base/"; ln -s "$BASE_REAL/base/secoes" "$T/copia/base/secoes"; ln -s "$BASE_REAL/base/secoes" "$T/build/base/secoes"
[ -d "$BASE_REAL/recibos" ] && cp -R "$BASE_REAL/recibos" "$T/copia/recibos" || mkdir -p "$T/copia/recibos"
cd "$PY"
echo "== 1/4 parsers e ementa estruturada, acórdão por acórdão =="
TJSE_DIR_DADOS="$BASE_REAL" python3 "$AQUI/dump_py.py" > "$T/py.jsonl"; TJSE_DIR_DADOS="$BASE_REAL" node "$AQUI/dump_node.mjs" > "$T/node.jsonl"
python3 "$AQUI/comparar.py" "$T/py.jsonl" "$T/node.jsonl"
echo "== 2/4 índice reconstruído pelo Node do HTML bruto =="
TJSE_DIR_DADOS="$T/build" node -e "import('$AQUI/../../server/indice.js').then(({db,importarSecoesDoBruto,fecharDb})=>{importarSecoesDoBruto(db());fecharDb()})"
python3 "$AQUI/indice_cmp.py" "$BASE_REAL/base/boletim.db" "$T/build/base/boletim.db"
echo "== 3/4 busca (bateria de casos_busca.json) =="
TJSE_DIR_DADOS="$T/copia" python3 "$AQUI/busca_py.py" > "$T/busca_py.json"; TJSE_DIR_DADOS="$T/copia" node "$AQUI/busca_node.mjs" > "$T/busca_node.json"
python3 - "$T/busca_py.json" "$T/busca_node.json" <<'PYEOF'
import json, sys
a, b = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
ruins = [k for k in a if a[k] != b.get(k)]
print(f"{len(a) - len(ruins)}/{len(a)} casos idênticos caractere a caractere"); sys.exit(1 if ruins else 0)
PYEOF
echo "== 4/4 conferência de citação e alertas de atribuição =="
if ls "$T/copia/recibos"/*.json >/dev/null 2>&1; then
  python3 "$AQUI/confere_py.py" "$T/copia/recibos" > "$T/c_py.json"; node "$AQUI/confere_node.mjs" "$T/copia/recibos" "$T/c_py.json" > "$T/c_node.json"
  python3 - "$T/c_py.json" "$T/c_node.json" <<'PYEOF'
import json, sys
a, b = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
ruins = [k for k in a if a[k]["r"] != b[k]["r"]]
print(f"{len(a) - len(ruins)}/{len(a)} conferências idênticas"); sys.exit(1 if ruins else 0)
PYEOF
else echo "(sem recibos reais: etapa pulada)"; fi
echo "PARIDADE TOTAL"
