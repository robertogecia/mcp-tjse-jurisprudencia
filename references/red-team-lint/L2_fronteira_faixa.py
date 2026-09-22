"""L2 — trecho que COMEÇA dentro da faixa transcrita e TERMINA fora (ou vice-versa) não dispara
nenhum aviso: `ns in marcado` exige a faixa inteira. O trecho está no `texto` -> aprovado em silêncio."""
import importlib.util, json, os, re, sys, tempfile
sys.path.insert(0, os.environ.get("PETICAO_RG_SCRIPTS", os.path.expanduser("~/.claude/skills/peticao-rg/scripts")))
import lint_citacoes as L
spec = importlib.util.spec_from_file_location("srv", os.environ.get("TJSE_RAIZ", os.path.expanduser("~/MCP/tjse-jurisprudencia")) + "/servidor_tjse.py")
srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)

corpo = ("ACORDAM os Desembargadores do Tribunal de Justica do Estado de Sergipe. Precedentes: "
         "A jurisprudencia e pacifica no sentido de que a clausula de reajuste por faixa etaria e abusiva "
         "quando nao demonstrada a base atuarial. (TJ-MG - Apelacao Civel 1.0000.24.000001-1/001, Rel. Des. "
         "Fulano, 5a Camara Civel, j. 01/02/2025). Nesse sentido, no caso dos autos, entendo que o recurso "
         "merece provimento. E como voto.")
tn = srv.norm(corpo)
ini = next((m.start() for m in re.finditer(r"\bacordam\b", tn) if "estado de sergipe" in tn[m.start():m.start()+450]), 0)
faixas = srv.faixas_transcritas(tn, ini)
transcrito = " \n".join(tn[a:b] for a, b in faixas)
pasta = tempfile.mkdtemp(prefix="L2_")
json.dump({"id_documento": "202640471", "nr_processo": "202600823569", "tribunal": "TJSE",
           "texto": corpo, "texto_transcrito": transcrito, "texto_divergente": ""},
          open(os.path.join(pasta, "202640471.json"), "w"))
F = lambda **k: L.Ficha(dict({"chave": "TJSE 202640471", "tribunal": "TJSE", "id_documento": "202640471",
                              "verificacao": "inteiro teor lido"}, **k), ("x",))
print("faixa transcrita:", repr(transcrito[:80]), "...")
casos = {
  "A) todo dentro da faixa (controle)":
      "a clausula de reajuste por faixa etaria e abusiva quando nao demonstrada a base atuarial",
  "B) começa dentro, termina fora (atravessa a atribuição)":
      "quando nao demonstrada a base atuarial. (TJ-MG - Apelacao Civel 1.0000.24.000001-1/001, Rel. Des. Fulano, 5a Camara Civel, j. 01/02/2025). Nesse sentido",
  "C) [...] com um fragmento dentro e outro fora":
      "A jurisprudencia e pacifica no sentido de que a clausula de reajuste [...] entendo que o recurso merece provimento",
}
for nome, tr in casos.items():
    print("\n", nome)
    print("   ->", L.conferir_recibo(F(trecho=tr), None, None, pasta) or "SILÊNCIO — APROVOU")

# D) variante natural: o trecho começa UMA palavra antes da abertura do bloco ("Precedentes:")
d = "Sergipe. Precedentes: A jurisprudencia e pacifica no sentido de que a clausula de reajuste por faixa etaria e abusiva"
print("\n D) começa uma palavra antes da abertura do bloco")
print("   ->", L.conferir_recibo(F(trecho=d), None, None, pasta) or "SILÊNCIO — APROVOU")
