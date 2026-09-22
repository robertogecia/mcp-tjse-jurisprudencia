# -*- coding: utf-8 -*-
"""L1/L2/L3 — _RE_TJSE: falsos negativos e falsos positivos. Sem rede, sem escrita."""
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/peticao-rg/scripts"))
from lint_citacoes import extrair_citacoes, parsear_chave, lint

I = lambda t: [c.ident for c in extrair_citacoes(t)]

print("== FALSOS NEGATIVOS (formas reais de citar o TJSE que o regex PERDE) ==")
fn = [
 "(TJSE, 202638463)",
 "(TJSE, nº 202638463)",
 "TJSE - 202638463",
 "TJSE, Acórdão: 202638463",
 "acórdão recorrido nº 202638463",
 "acórdão de nº 202638463",
 "Acórdão n. 202.638.463",
 "TJSE, ApCiv 202600737656, ac. 202638463",
 "Acórdão (TJSE) 202638463",
 "nº do acórdão: 202638463",
]
for t in fn:
    print("  %-45r -> %s" % (t, I(t)))

print("\n== FALSOS POSITIVOS (não é citação do TJSE, mas vira uma) ==")
fp = [
 "O acórdão de fls. 202638463 do apenso",                      # fls
 "conforme o acórdão do TJMG 202512345 (numeração local)",      # OUTRO tribunal
 "Acórdão 200700001 do TJPE",
 "o acordao 202612345 daquele tribunal de Sergipe? nao",
 "não consta do acórdão 201900001 nada disso",                  # contexto de negação
 "TJSE 202600823569",                                           # 12 dígitos? ver
]
for t in fp:
    print("  %-55r -> %s" % (t, I(t)))

print("\n== sobreposição / classe errada ==")
casos = [
 "acórdão 202638463 e Tema 1300",
 "Súmula 385, acórdão 202638463",
 "(TJSE, processo nº 202600737656, acórdão nº 202638463)",
 "acórdão nº 2026384632",   # 10 dígitos
 "acórdão nº 20263846",     # 8 dígitos
]
for t in casos:
    print("  %-58r -> %s" % (t, I(t)))

print("\n== chave da ficha x identidade ==")
for k in ["TJSE 202638463", "acórdão 202638463", "TJSE nº 202638463",
          "202638463", "TJSE - 202638463", "Acórdão TJSE 202638463",
          "TJSE, acórdão 202638463", "AI 202600737656 (TJSE)"]:
    print("  %-30r -> %s" % (k, parsear_chave(k)))
