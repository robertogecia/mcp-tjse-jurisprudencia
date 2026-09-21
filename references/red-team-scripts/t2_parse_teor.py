"""t2 — parse_teor: ordem de ORGAOS_FECHO, filtro 'estado de sergipe', data do fecho,
inicio_conteudo. Variantes sintéticas construídas a partir do TEXTO dos fixtures reais."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import *

H3, H8 = fx("03-relatorio-202638463.html"), fx("08-relatorio-202640467.html")
T3, T8 = s.parse_teor(H3)["texto"], s.parse_teor(H8)["texto"]
print("base real 03:", s.parse_teor(H3)["orgao_fecho"], s.parse_teor(H3)["data_julgamento"],
      "| 08:", s.parse_teor(H8)["orgao_fecho"], s.parse_teor(H8)["data_julgamento"])
FECHO_REAL = "ACORDAM os Desembargadores do Tribunal de Justiça do Estado de Sergipe, nesta 1ª Câmara Cível"
assert FECHO_REAL in T3

def variar(novo_fecho, resto=""):
    return T3.replace(FECHO_REAL, novo_fecho, 1) if not resto else \
           T3.replace(FECHO_REAL, novo_fecho + resto, 1)

print("\n=== A) ORGAOS_FECHO varrido por ORDEM DA LISTA, não por posição no texto ===")
print("   ORGAOS_FECHO =", s.ORGAOS_FECHO)
casos = [
 ("2ª Câmara Cível + 'Tribunal Pleno' citado de passagem na mesma janela",
  "ACORDAM os Desembargadores do Tribunal de Justiça do Estado de Sergipe, nesta 2ª Câmara Cível, "
  "alinhando-se ao que decidiu o Tribunal Pleno desta Corte"),
 ("Câmara Criminal + 'Seção Especializada Cível' citada de passagem",
  "ACORDAM os Desembargadores do Tribunal de Justiça do Estado de Sergipe, nesta Câmara Criminal, "
  "ressalvado o entendimento da Seção Especializada Cível"),
 ("1ª Turma Recursal (fecho puro)",
  "ACORDAM os Juízes do Tribunal de Justiça do Estado de Sergipe, nesta 1ª Turma Recursal"),
 ("2ª Câmara Cível (fecho puro, controle)",
  "ACORDAM os Desembargadores do Tribunal de Justiça do Estado de Sergipe, nesta 2ª Câmara Cível"),
]
for nome, fech in casos:
    d = s.parse_teor(variar(fech))
    print(f"   {nome}\n      -> orgao_fecho = {d['orgao_fecho']!r} | ambiguo = {d['fecho_ambiguo']}")

print("\n=== B) filtro 'estado de sergipe' = mera presença na janela de 450 chars ===")
t = T8.replace("Acordam os integrantes da Eg . 3ª Câmara de Direito Privado",
               "Acordam os integrantes da Eg . Câmara Criminal, em recurso oriundo do Estado de Sergipe", 1)
d = s.parse_teor(t)
print("   fecho do TJCE transcrito no voto, mencionando 'Estado de Sergipe' na janela:")
print("   -> orgao_fecho =", d["orgao_fecho"], "| fecho_ambiguo =", d["fecho_ambiguo"],
      "(o 2º fecho, alheio, entra na contagem e ZERA o órgão)")

print("\n=== C) data do fecho ===")
d = s.parse_teor(T3.replace("Aracaju/SE, 17 de Julho de 2026.",
      "Aracaju/SE, 03 de Junho de 2026 (sessão adiada).\nAracaju/SE, 17 de Julho de 2026.", 1))
print("   duas datas após o fecho -> data_julgamento =", d["data_julgamento"], "(pega a PRIMEIRA)")
d = s.parse_teor(T3.replace("Aracaju/SE, 17 de Julho de 2026.", "Aracaju/SE, 17.07.2026.", 1))
print("   data em formato numérico -> data_julgamento =", d["data_julgamento"])

print("\n=== D) resíduo de JS 'carregarTurma' ===")
print("   'carregarTurma' no HTML bruto:", "carregarTurma" in H3,
      "| no texto limpo SEM a regex:", "carregarTurma" in s.limpar_html(H3),
      "| no texto final:", "carregarTurma" in T3)
print("   (limpar_html já remove <script>; a regex da l.334 não teve o que remover neste corpus)")

print("\n=== E) inicio_conteudo = t.find('EMENTA'), case-sensitive, 1ª ocorrência ===")
d = s.parse_teor(T3.replace("EMENTA", "E M E N T A", 1))
print("   cabeçalho grafado 'E M E N T A' -> inicio_conteudo =", d["inicio_conteudo"],
      "(pula", d["inicio_conteudo"], "chars e começa numa ementa do TJ-MG transcrita)")
print("   ", repr(d["texto"][d["inicio_conteudo"]:][:120]))
d = s.parse_teor(T8.replace("EMENTA", "E M E N T A"))
print("   documento SEM nenhuma 'EMENTA' -> inicio_conteudo =", d["inicio_conteudo"])
print("   ", repr(d["texto"][d["inicio_conteudo"]:][:230]))
