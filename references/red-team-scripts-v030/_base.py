"""Base do red team TJSE. Estado/base/recibos em pasta temporária; httpx zerado; zero rede."""
import os, sys, tempfile
os.environ["TJSE_DIR_DADOS"] = tempfile.mkdtemp(prefix="tjse-redteam-")
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
sys.modules.pop("servidor_tjse", None)
import servidor_tjse as s
s.httpx = None  # qualquer rede vira PesquisaNaoRealizada, nunca requisição

def fx(n):
    return open(os.path.join(RAIZ, "fixtures", n), encoding="iso-8859-1").read()

def teor(n="03-relatorio-202638463.html"):
    d = s.parse_teor(fx(n))
    return d, d["texto"][d["inicio_conteudo"]:]
