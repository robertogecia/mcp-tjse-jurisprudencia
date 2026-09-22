"""L3 — recibo com campo não-string derruba o lint inteiro (AttributeError), impedindo a geração da peça."""
import json, os, sys, tempfile
sys.path.insert(0, "/Users/robertogrecia/.claude/skills/peticao-rg/scripts")
import lint_citacoes as L
pasta = tempfile.mkdtemp(prefix="L3_")
F = lambda **k: L.Ficha(dict({"chave": "TJSE 202640467", "tribunal": "TJSE", "id_documento": "202640467",
                              "verificacao": "inteiro teor lido"}, **k), ("x",))
def grava(**kw):
    d = {"id_documento": "202640467", "nr_processo": "202600823569", "tribunal": "TJSE",
         "texto": "alpha beta gamma delta epsilon zeta"}
    d.update(kw); json.dump(d, open(os.path.join(pasta, "202640467.json"), "w"))

for nome, kw in [("texto_transcrito = lista", {"texto_transcrito": ["a", "b"]}),
                 ("texto_transcrito = número", {"texto_transcrito": 123}),
                 ("texto_divergente = dict", {"texto_divergente": {"a": 1}}),
                 ("texto = número", {"texto": 12345678901234})]:
    grava(**kw)
    try:
        print(nome, "->", L.conferir_recibo(F(trecho="alpha beta gamma delta"), None, None, pasta))
    except Exception as e:
        print(nome, "-> EXCEÇÃO NÃO TRATADA:", type(e).__name__, e)

# o mesmo pelo fluxo completo do lint(): a exceção sobe e mata a geração da peça
grava(texto_transcrito=["a"])
cfg = {"blocks": [{"tipo": "paragrafo", "texto": "Nesse sentido (TJSE, acórdão nº 202640467)."}],
       "dir_recibos_tjse": pasta,
       "precedentes": [{"chave": "TJSE 202640467", "tribunal": "TJSE", "id_documento": "202640467",
                        "verificacao": "inteiro teor lido", "trecho": "alpha beta gamma delta"}]}
try:
    print("lint() completo ->", L.lint(cfg).texto())
except Exception as e:
    print("lint() completo -> EXCEÇÃO NÃO TRATADA:", type(e).__name__, e)
