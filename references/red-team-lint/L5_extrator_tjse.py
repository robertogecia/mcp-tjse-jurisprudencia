"""L5 — _RE_TJSE / extrair_citacoes / parsear_chave: falsos negativos e colisão de identidade."""
import sys
sys.path.insert(0, "/Users/robertogrecia/.claude/skills/peticao-rg/scripts")
import lint_citacoes as L
i = lambda t: [c.ident for c in L.extrair_citacoes(t)]
P = lambda t: {"tipo": "paragrafo", "texto": t}

print("== A) 'n°' (sinal de grau, U+00B0) mata a detecção de TODAS as classes ==")
for t in ["REsp n° 1.959.812", "Tema n° 1265", "Súmula n° 385", "IRDR n° 15", "acórdão n° 202638463",
          "(TJSE, acórdão n° 202638463, Rel. Desa. Fulana)"]:
    print("   %-46r -> %s" % (t, i(t)))
print("   controle com 'nº' (masculino ordinal):", i("REsp nº 1.959.812"), i("acórdão nº 202638463"))
print("   lint completo, citação com n° e SEM ficha:",
      L.lint({"blocks": [P("Como decidiu o STJ no REsp n° 1.959.812.")]}).resumo)

print("\n== B) outras formas reais que o regex perde ==")
for t in ["acórdão: 202638463", "acórdão n.o 202638463", "TJSE, ac. 202638463",
          "202638463 (TJSE)", "acórdão nº 202.638.463", "acórdão de nº 202638463"]:
    print("   %-34r -> %s" % (t, i(t)))

print("\n== C) acórdão de OUTRO tribunal no mesmo formato vira identidade 'tjse' ==")
print("   texto:", i("TJMG, acórdão 202512345, Rel. Des. X"))
f = {"chave": "TJMG 202512345", "tribunal": "TJMG", "relator": "Des. X",
     "verificacao": "inteiro teor lido", "trecho": "y"}
r = L.lint({"blocks": [P("(TJMG, acórdão 202512345, Rel. Des. X)")], "precedentes": [f]})
print("   ficha chave 'TJMG 202512345' -> parsear_chave:", L.parsear_chave("TJMG 202512345"))
print("   ERROS:", r.erros)
print("   avisos:", r.avisos)
print("   (mesma ficha com chave 'acórdão 202512345'):",
      L.lint({"blocks": [P("(TJMG, acórdão 202512345, Rel. Des. X)")],
              "precedentes": [dict(f, chave="acórdão 202512345")]}).erros or "sem erro")
