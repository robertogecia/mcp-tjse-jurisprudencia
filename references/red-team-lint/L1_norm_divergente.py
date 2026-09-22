"""L1 — o `norm` do servidor e o `norm_literal` do lint divergem em "nº <dígito>".
Efeito: trecho realmente TRANSCRITO de outro tribunal não dispara o aviso e o lint APROVA."""
import importlib.util, json, os, sys, tempfile
sys.path.insert(0, "/Users/robertogrecia/.claude/skills/peticao-rg/scripts")
import lint_citacoes as L
spec = importlib.util.spec_from_file_location("srv", "/Users/robertogrecia/MCP/tjse-jurisprudencia/servidor_tjse.py")
srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)

print("--- divergência das duas normalizações (mesma entrada) ---")
for s in ["Súmula nº 7 do STJ", "acórdão n° 123", "art. 1.691", "“aspas” e travessão—"]:
    a, b = L.norm_literal(srv.norm(s)), L.norm_literal(s)
    print(("DIFERE" if a != b else "igual "), repr(s), "| servidor+lint:", repr(a), "| lint:", repr(b))

# corpo realista: o voto do TJSE transcreve a ementa de um acórdão do TJMG
corpo = ("ACORDAM os Desembargadores do Tribunal de Justica do Estado de Sergipe. Precedentes: "
         "APELACAO CIVEL. Incide a Súmula nº 7 do STJ, que veda o reexame de provas em recurso especial. "
         "(TJ-MG - Apelacao Civel 1.0000.24.000001-1/001, Rel. Des. Fulano, 5a Camara Civel, j. 01/02/2025). "
         "Nesse sentido, no caso dos autos, entendo que o recurso merece provimento. E como voto.")
tn = srv.norm(corpo)
ini = next((m.start() for m in __import__("re").finditer(r"\bacordam\b", tn)
            if "estado de sergipe" in tn[m.start(): m.start()+450]), 0)
transcrito = " \n".join(tn[a:b] for a, b in srv.faixas_transcritas(tn, ini))
print("\n--- texto_transcrito gravado pelo servidor ---\n", repr(transcrito))

pasta = tempfile.mkdtemp(prefix="L1_")
json.dump({"id_documento": "202640470", "nr_processo": "202600823569", "tribunal": "TJSE",
           "texto": corpo, "texto_transcrito": transcrito, "texto_divergente": ""},
          open(os.path.join(pasta, "202640470.json"), "w"))
F = lambda **k: L.Ficha(dict({"chave": "TJSE 202640470", "tribunal": "TJSE", "id_documento": "202640470",
                              "verificacao": "inteiro teor lido"}, **k), ("x",))
alheio = "Incide a Súmula nº 7 do STJ, que veda o reexame de provas em recurso especial"
print("\ntrecho citado (é palavra do TJMG/STJ, não do TJSE):", alheio)
print("resultado do lint:", L.conferir_recibo(F(trecho=alheio), None, None, pasta) or "SILÊNCIO — APROVOU")
sem_numero = "veda o reexame de provas em recurso especial"
print("\nmesmo trecho SEM o 'nº' (controle):", sem_numero)
print("resultado do lint:", L.conferir_recibo(F(trecho=sem_numero), None, None, pasta) or "SILÊNCIO — APROVOU")
