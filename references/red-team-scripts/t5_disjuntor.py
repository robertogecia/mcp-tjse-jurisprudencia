"""t5 — disjuntor: MARCAS_DESAFIO nos 6000 primeiros chars sobre conteúdo REAL de ementa,
estado com tipos errados, .lock sem permissão, corrida entre processos."""
import json, os, re, sys, time, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import *

print("=== A) onde começa o CONTEÚDO nos 6000 primeiros chars de cada fixture ===")
for n in ("07-principal-168-sec5.html", "03-relatorio-202638463.html", "02-pesquisa-1ano.html"):
    h = fx(n)
    cab = h[:6000]
    # 1º trecho de ementa (texto em caixa alta com pelo menos 40 letras) dentro do cabeçalho
    m = re.search(r"font-size: 7pt\">(.{0,200})", cab, re.S)
    print(f"   {n}: len={len(h)} | conteúdo de ementa dentro dos 6000?",
          bool(m), "|", repr(s.limpar_html(m.group(1))[:110]) if m else "")
    print("      marcas de desafio já presentes no cabeçalho real:",
          [x for x in s.MARCAS_DESAFIO if x in cab.lower()])

print("\n=== B) ementa legítima com 'CAPTCHA'/'código de segurança' nos 6000 primeiros chars ===")
h = fx("07-principal-168-sec5.html")
i = h.find("font-size: 7pt")
print("   posição da 1ª ementa no HTML bruto:", i, "(< 6000 =", i < 6000, ")")
# injeta as palavras direto no HTML bruto (o fixture traz acentos como entidade)
falso = h[:i] + "ESTELIONATO. FRAUDE MEDIANTE QUEBRA DE CAPTCHA E DE C&Oacute;DIGO DE SEGURAN&Ccedil;A. " + h[i:]
cab = falso[:6000].lower()
print("   marcas detectadas:", [x for x in s.MARCAS_DESAFIO if x in cab])
print("   -> _http() pausaria o servidor por", s.PAUSA_DESAFIO_S // 3600, "h e a seção nunca seria indexada")

print("\n=== C) estado com JSON válido mas tipos errados ===")
def por_estado(e):
    with open(s.ARQ_ESTADO, "w") as f: json.dump(e, f)
    try:
        asyncio.run(s._pedir_vez()); return "RESERVA CONCEDIDA"
    except s.PesquisaNaoRealizada as ex: return f"PesquisaNaoRealizada: {str(ex)[:50]}"
    except Exception as ex: return f"{type(ex).__name__}: {ex}"
for nome, e in [
    ("pausa_ate como string", {"requisicoes": [], "pausa_ate": "9999999999", "motivo": "", "incidentes": []}),
    ("requisicoes com strings", {"requisicoes": ["a", "b"], "pausa_ate": 0, "motivo": "", "incidentes": []}),
    ("pausa_ate None", {"requisicoes": [], "pausa_ate": None, "motivo": "", "incidentes": []}),
    ("requisicoes ausente", {"pausa_ate": 0}),
]:
    print(f"   {nome:26} -> {por_estado(e)}")
    try:
        print(f"      diagnostico_tjse ->", s.diagnostico().split(chr(10))[1][:60])
    except Exception as ex:
        print(f"      diagnostico_tjse -> {type(ex).__name__}: {ex}")
    try:
        s._pausar(60, "teste")
        print("      _pausar ->", "ok")
    except Exception as ex:
        print(f"      _pausar -> {type(ex).__name__}: {ex}")

print("\n=== D) .lock sem permissão de escrita ===")
os.remove(s.ARQ_ESTADO) if os.path.exists(s.ARQ_ESTADO) else None
lock = s.ARQ_ESTADO + ".lock"
open(lock, "a").close(); os.chmod(lock, 0o400)
for nome, fn in (("_pedir_vez", lambda: asyncio.run(s._pedir_vez())),
                 ("diagnostico_tjse", s.diagnostico),
                 ("_pausar (usado no tratamento de erro de rede)", lambda: s._pausar(60, "x"))):
    try:
        fn(); print(f"   {nome}: sem erro")
    except s.PesquisaNaoRealizada as ex: print(f"   {nome}: PesquisaNaoRealizada")
    except Exception as ex: print(f"   {nome}: {type(ex).__name__}: {ex}")
os.chmod(lock, 0o600)

print("\n=== E) relógio para trás ===")
with open(s.ARQ_ESTADO, "w") as f:
    json.dump({"requisicoes": [time.time() + 7200], "pausa_ate": 0, "motivo": "", "incidentes": []}, f)
try:
    asyncio.run(asyncio.wait_for(s._pedir_vez(), timeout=3)); print("   reserva concedida")
except asyncio.TimeoutError: print("   _pedir_vez FICOU EM LOOP (>3 s) — timestamp no futuro")
except s.PesquisaNaoRealizada as ex: print("   PesquisaNaoRealizada:", str(ex)[:60])
