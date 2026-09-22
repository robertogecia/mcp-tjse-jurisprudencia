# -*- coding: utf-8 -*-
"""L4..L7 — avisos TRANSCRIÇÃO / VOTO DIVERGENTE: falsos negativos de fronteira,
divergência de normalização servidor x lint, e campos corrompidos."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.expanduser("~/.claude/skills/peticao-rg/scripts"))
from lint_citacoes import conferir_recibo, Ficha, norm_literal

P = tempfile.mkdtemp(prefix="rt_tjse_")           # NUNCA a pasta real
def grava(ac, **k):
    d = {"id_documento": ac, "nr_processo": "202600823569", "tribunal": "TJSE"}
    d.update(k)
    with open(os.path.join(P, "%s.json" % ac), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)

F = lambda **k: Ficha(dict({"chave": "TJSE 202640467", "tribunal": "TJSE",
                            "id_documento": "202640467",
                            "verificacao": "inteiro teor lido"}, **k), ("x",))

TEXTO = ("Não há falar em irreversibilidade. Precedentes: Acordam os integrantes da Eg. 3ª Câmara "
         "de Direito Privado do Tribunal de Justiça do Estado do Ceará, à unanimidade, negar provimento. "
         "É como voto.")
TRANSC = ("acordam os integrantes da eg. 3a camara de direito privado do tribunal de justica do estado "
          "do ceara, a unanimidade, negar provimento.")
grava("202640467", texto=TEXTO, texto_transcrito=TRANSC, texto_divergente="")

print("== L4: trecho que COMEÇA dentro da faixa transcrita e TERMINA fora ==")
t = "do Estado do Ceará, à unanimidade, negar provimento. É como voto"
r = conferir_recibo(F(trecho=t), None, None, P)
print("  trecho:", t)
print("  ->", r or "SILÊNCIO (aprovado como palavra do TJSE)")

print("\n== L4b: trecho todo dentro (controle) ==")
print("  ->", conferir_recibo(F(trecho="do Tribunal de Justiça do Estado do Ceará"), None, None, P))

print("\n== L5: trecho com [...] — 1º fragmento fora, 2º dentro; e o inverso ==")
print("  fora+dentro ->", conferir_recibo(F(trecho="Não há falar em irreversibilidade [...] do Estado do Ceará, à unanimidade"), None, None, P))
print("  dentro+fora ->", conferir_recibo(F(trecho="do Estado do Ceará, à unanimidade [...] É como voto"), None, None, P))

print("\n== L6: divergência de normalização servidor x lint — 'nº <dígito>' ==")
# o servidor grava texto_transcrito já passado pelo norm() dele, que reescreve "nº 123" -> "n 123";
# o lint compara com norm_literal, que produz "no 123".
TEXTO2 = "Vejamos. Precedentes: (TJ-MG, Apelação nº 1234567, Rel. Des. Fulano, j. 01/01/2020). É como voto."
TRANSC2 = "precedentes: (tj-mg, apelacao n 1234567, rel. des. fulano, j. 01/01/2020)."  # <- saída real do norm() do servidor
grava("202640470", texto=TEXTO2, texto_transcrito=TRANSC2, texto_divergente="")
trecho = "TJ-MG, Apelação nº 1234567, Rel. Des. Fulano"
print("  norm_literal(ficha)   =", repr(norm_literal(trecho)))
print("  norm_literal(marcado) =", repr(norm_literal(TRANSC2)))
print("  ->", conferir_recibo(F(id_documento="202640470", trecho=trecho), None, None, P) or "SILÊNCIO")

print("\n== L7: campos corrompidos (não-string / lista / número) ==")
for nome, extra in [("texto_transcrito=5", {"texto": TEXTO, "texto_transcrito": 5}),
                    ("texto_transcrito=[..]", {"texto": TEXTO, "texto_transcrito": ["a"]}),
                    ("texto=lista", {"texto": ["linha 1 do acordao", "linha 2"]}),
                    ("texto_divergente=dict", {"texto": TEXTO, "texto_divergente": {"a": 1}})]:
    grava("202640480", **extra)
    try:
        r = conferir_recibo(F(id_documento="202640480", trecho="Não há falar em irreversibilidade"), None, None, P)
        print("  %-24s -> %s" % (nome, r))
    except Exception as e:
        print("  %-24s -> EXCEÇÃO %s: %s" % (nome, type(e).__name__, e))
