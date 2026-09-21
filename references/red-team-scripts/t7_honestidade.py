"""t7 — honestidade das mensagens: índice vazio, DB corrompido, promessas do README/docstring."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import *

print("=== A) índice vazio ===")
print("   ", s.buscar(consulta="dano moral").replace("\n", "\n    ")[:400])

print("\n=== B) base SQLite corrompida ===")
os.makedirs(s.DIR_BASE, mode=0o700, exist_ok=True)
open(s.ARQ_DB, "wb").write(b"isto nao e um banco sqlite" * 200)
for nome, fn in (("buscar", lambda: s.buscar(consulta="dano")),
                 ("diagnostico_tjse", s.diagnostico),
                 ("obter", lambda: asyncio.run(s.obter("202638463", "202600737656")))):
    try:
        print(f"   {nome}: {str(fn())[:150]}")
    except Exception as ex:
        print(f"   {nome}: {type(ex).__name__}: {str(ex)[:120]}  <-- erro cru, não 'BUSCA NÃO REALIZADA'")

print("\n=== C) promessas conferidas no código ===")
import inspect
src = inspect.getsource(s)
print("   docstring de obter_inteiro_teor_tjse diz 'partes omitidas por padrão':",
      "partes e advogados omitidos" in src, "| mas o corte é só até a 1ª 'EMENTA' (l.822) e o RELATÓRIO fica")
print("   README: 'recibos/ e base/ em 0700/0600' -> makedirs só cria, não corrige modo:",
      "os.makedirs(DIR_RECIBOS, mode=0o700, exist_ok=True)" in src)
print("   verificar_citacao_tjse: 'Falha de rede = citação NÃO CONFERIDA, nunca ❌' ->",
      "A citação fica NÃO CONFERIDA (não é ❌)" in src, "(confere)")
print("   citacao() emite 'verificação: inteiro teor lido' sem saber se houve corte:",
      "'inteiro teor lido'" in src)
