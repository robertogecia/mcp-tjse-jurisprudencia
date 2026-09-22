"""L6 — TJRO e STJ depois da mudança de 21/09: mensagens idênticas às do selftest, e campos novos
do TJSE num recibo do TJRO não mudam nada."""
import json, os, sys, tempfile
sys.path.insert(0, os.environ.get("PETICAO_RG_SCRIPTS", os.path.expanduser("~/.claude/skills/peticao-rg/scripts")))
import lint_citacoes as L
P = lambda t: {"tipo": "paragrafo", "texto": t}
def run(blocks, **raiz):
    cfg = {"blocks": blocks}; cfg.update(raiz); return L.lint(cfg)

pasta = tempfile.mkdtemp(prefix="L6_tjro_")
def grava(ident, texto, nr="7050907-04.2019.8.22.0001", **extra):
    d = {"id_documento": ident, "nr_processo": nr, "texto": texto}; d.update(extra)
    json.dump(d, open(os.path.join(pasta, "%s.json" % ident), "w"))
grava("18238575", "ACORDAM os Magistrados da 1ª Câmara Cível. É devida a fixação de honorários nos próprios "
                  "embargos quando o agravo foi julgado prejudicado sem exame da verba.")
grava("18238999", "VOTO VENCIDO. Entendo que não cabe fixar honorários em sede de embargos de declaração.")
T = lambda **k: dict({"chave": "7050907-04.2019.8.22.0001", "tribunal": "TJRO", "orgao": "1ª Câmara Cível",
                      "orgao_fonte": "fecho", "relator": "Des. Sansão Saldanha", "julgamento": "2022-11-30",
                      "id_documento": "18238575", "verificado_em": "2026-09-19",
                      "verificacao": "inteiro teor lido"}, **k)
cita = [P("Nesse sentido (TJRO, 7050907-04.2019.8.22.0001, 1ª Câmara Cível, Rel. Des. Sansão Saldanha, j. 30/11/2022).")]
r = run(cita, dir_recibos=pasta, precedentes=[T(trecho="É devida a fixação de honorários nos próprios embargos [...] sem exame da verba")])
print("42 ok:", not r.erros and not any("recibo" in a for a in r.avisos), r.erros, r.avisos)
r = run(cita, dir_recibos=pasta, precedentes=[T(trecho="É sempre devida a fixação de honorários em embargos")])
print("43 erro:", r.erros)
r = run(cita, dir_recibos=pasta, precedentes=[T(trecho="não cabe fixar honorários em sede de embargos")])
print("44 aviso:", r.avisos)
r = run(cita, dir_recibos=pasta, precedentes=[T(id_documento="99999999", trecho="qualquer texto literal aqui")])
print("45 aviso:", r.avisos)

# campos novos do TJSE presentes num recibo do TJRO: não podem mudar nada
grava("18238575", "ACORDAM os Magistrados da 1ª Câmara Cível. É devida a fixação de honorários nos próprios "
                  "embargos quando o agravo foi julgado prejudicado sem exame da verba.",
      texto_transcrito="e devida a fixacao de honorarios nos proprios embargos", texto_divergente="")
r = run(cita, dir_recibos=pasta, precedentes=[T(trecho="É devida a fixação de honorários nos próprios embargos")])
print("TJRO com texto_transcrito do TJSE:", r.avisos)

_ps = tempfile.mkdtemp(prefix="L6_stj_")
json.dump({"id_documento": "202401318197", "texto": "A querela nullitatis é cabível quando ausente a citação válida do réu no processo originário."},
          open(os.path.join(_ps, "202401318197.json"), "w"))
_fs = lambda **k: L.Ficha(dict({"chave": "REsp 2145294", "tribunal": "STJ", "id_documento": "2024/0131819-7",
                                "verificacao": "inteiro teor lido"}, **k), ("x",))
print("STJ ok:", L.conferir_recibo(_fs(trecho="a querela nullitatis é cabível quando ausente a citação válida"), None, _ps))
print("STJ erro:", L.conferir_recibo(_fs(trecho="a querela nullitatis é sempre cabível em qualquer hipótese"), None, _ps))
print("STJ sem recibo:", L.conferir_recibo(_fs(id_documento="202499999999", trecho="qualquer texto com mais de quatro palavras"), None, _ps))
