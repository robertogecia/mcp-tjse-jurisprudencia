"""B14 — varredura de dado pessoal para publicação em repositório público (só arquivo:linha e rótulo)."""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PADROES = [
    ("caminho do dono da máquina", re.compile(r"/Users/[a-z]+", re.I)),
    ("e-mail", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("OAB", re.compile(r"OAB[/\s]?[A-Z]{2}\s*[\d.-]+", re.I)),
    ("nome do dono", re.compile(r"Roberto\s+Gr[ée]cia|Gr[ée]cia\s+Bessa", re.I)),
    ("qualificação de parte (AGRAVANTE/APELANTE/RÉU + nome)",
     re.compile(r"(?i)\b(AGRAVANTE|AGRAVADO|APELANTE|APELADO|RECORRENTE|RECORRIDO|EXEQUENTE|EXECUTADO|AUTOR|R[ÉE]U|"
                r"IMPETRANTE|REQUERENTE)\b\s*[:\-]?\s*[A-ZÀ-Ü][A-ZÀ-Ü'\. ]{10,}")),
    ("advogado (OAB/SE)", re.compile(r"(?i)\bADVOGAD[OA]S?\b\s*[:\-]?\s*[A-ZÀ-Ü]")),
    ("iniciais de menor (A.B.C.D.)", re.compile(r"\b(?:[A-Z]\.){3,}")),
    ("CPF/CNPJ", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")),
]
IGNORA = {".venv", "__pycache__", ".git", "base", "recibos"}
SO_ESTES = (".py", ".md", ".html", ".txt", ".json", ".toml", ".cfg")

achados = {}
for raiz, dirs, arqs in os.walk(RAIZ):
    dirs[:] = [d for d in dirs if d not in IGNORA]
    for a in arqs:
        if not a.endswith(SO_ESTES):
            continue
        p = os.path.join(raiz, a)
        rel = os.path.relpath(p, RAIZ)
        try:
            linhas = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except Exception:
            continue
        for i, l in enumerate(linhas, 1):
            for rot, rx in PADROES:
                if rx.search(l):
                    achados.setdefault((rel, rot), []).append(i)

for (rel, rot), ls in sorted(achados.items()):
    n = len(ls)
    print(f"{rel}:{ls[0]}" + (f" (+{n-1} outras linhas: {ls[1:6]}{'…' if n>7 else ''})" if n > 1 else "")
          + f"  -> {rot}")

print("\n--- fixtures: os nomes de parte ainda são reais? ---")
for f in sorted(os.listdir(os.path.join(RAIZ, "fixtures"))):
    t = open(os.path.join(RAIZ, "fixtures", f), encoding="iso-8859-1").read()
    fict = len(re.findall(r"(?i)ficticia|ficticio|fulano|beltrano|sicrano", t))
    qual = re.findall(r"(?i)(AGRAVANTE|APELANTE|ADVOGAD[OA])\s*[:\n ]{1,3}([A-ZÀ-Ü][A-ZÀ-Ü'\. ]{8,40})", t)
    print(f"  {f:34s} marcas de anonimização: {fict:3d} · blocos de qualificação: {len(qual)}"
          + (f" · 1º rótulo: {qual[0][0]}" if qual else ""))

print("\n--- permissões de pasta ---")
for d in ("base", "recibos", "fixtures", "references"):
    p = os.path.join(RAIZ, d)
    if os.path.isdir(p):
        print(f"  {d}: {oct(os.stat(p).st_mode & 0o777)}")
print("  .gitignore:", open(os.path.join(RAIZ, ".gitignore")).read().split())
