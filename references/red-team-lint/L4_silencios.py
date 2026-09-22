"""L4 — caminhos em que o lint CALA quando deveria falar."""
import json, os, sys, tempfile
sys.path.insert(0, os.environ.get("PETICAO_RG_SCRIPTS", os.path.expanduser("~/.claude/skills/peticao-rg/scripts")))
import lint_citacoes as L
pasta = tempfile.mkdtemp(prefix="L4_")
json.dump({"id_documento": "202638463", "nr_processo": "202600737656", "tribunal": "TJSE",
           "texto": "o art. 1.691 do Codigo Civil veda aos pais contrair obrigacoes em nome dos filhos",
           "texto_transcrito": "", "texto_divergente": ""},
          open(os.path.join(pasta, "202638463.json"), "w"))
F = lambda **k: L.Ficha(dict({"chave": "TJSE 202638463", "tribunal": "TJSE",
                              "verificacao": "inteiro teor lido"}, **k), ("x",))
INV = "trecho inventado que nao esta no acordao"
print("== A) id_documento ausente/curto/lixo: nenhum aviso (o de 12 dígitos avisa) ==")
for idd in [None, "", "20263846", "00202638463", "lixo", "202600737656"]:
    d = {} if idd is None else {"id_documento": idd}
    out = L.conferir_recibo(F(trecho=INV, **d), None, None, pasta)
    print("   id_documento=%-16r -> %s" % (idd, out[0][1][:90] + "…" if out else "SILÊNCIO"))

print("\n== B) trecho com menos de 4 palavras nunca é conferido contra o recibo ==")
for tr in ["nao cabe indenizacao", "jamais houve dano moral", "veda aos pais contrair obrigacoes"]:
    out = L.conferir_recibo(F(id_documento="202638463", trecho=tr), None, None, pasta)
    print("   %-38r -> %s" % (tr, out[0][0] if out else "SILÊNCIO"))

print("\n== C) recibo existe mas sem campo 'texto' -> tratado como inexistente ==")
json.dump({"id_documento": "202699001", "nr_processo": "202600737656", "texto": ""},
          open(os.path.join(pasta, "202699001.json"), "w"))
out = L.conferir_recibo(F(id_documento="202699001", trecho=INV), None, None, pasta)
print("   ->", out[0][1][:120] if out else "SILÊNCIO")

print("\n== D) ficha TJSE sem NENHUM campo literal (trecho/tese/ementa/dispositivo) ==")
out = L.conferir_recibo(F(id_documento="202638463"), None, None, pasta)
print("   ->", out or "SILÊNCIO (recibo existe, mas nada é conferido — e nada é dito)")

print("\n== E) ficha SEM o campo `tribunal`: o recibo nunca é conferido, em silêncio ==")
P = lambda t: {"tipo": "paragrafo", "texto": t}
sem_trib = {"chave": "TJSE 202638463", "id_documento": "202638463", "verificacao": "inteiro teor lido",
            "trecho": "trecho inventado que nao esta no acordao"}
r = L.lint({"blocks": [P("Nesse sentido (TJSE, acórdão nº 202638463).")],
            "dir_recibos_tjse": pasta, "precedentes": [sem_trib]})
print("   com identidade ('tjse', ...) mas ficha sem `tribunal` ->", r.erros or "NENHUM ERRO", r.avisos)
com_trib = dict(sem_trib, tribunal="TJSE")
r = L.lint({"blocks": [P("Nesse sentido (TJSE, acórdão nº 202638463).")],
            "dir_recibos_tjse": pasta, "precedentes": [com_trib]})
print("   controle, mesma ficha com `tribunal`: ->", r.erros)
