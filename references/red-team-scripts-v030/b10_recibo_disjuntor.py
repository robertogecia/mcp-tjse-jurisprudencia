"""B10 — recibos (.inconsistente em cascata, 'recibo em disco' mentiroso) e disjuntor v0.3/0.4."""
import _base as b
import asyncio
import hashlib
import json
import os
import time

s = b.s
os.makedirs(s.DIR_RECIBOS, exist_ok=True)
H3 = b.fx("03-relatorio-202638463.html")
H8 = b.fx("08-relatorio-202640467.html")

print("=== A) um bug em parse_teor destrói TODOS os recibos bons, em cascata ===")
for ac, h in (("202638463", H3), ("202640467", H8)):
    s.gravar_recibo(ac, "000000000000", h)
print("  recibos gravados:", sorted(os.listdir(s.DIR_RECIBOS)))
print("  ler_recibo antes:", [bool(s.ler_recibo(a)) for a in ("202638463", "202640467")])
orig = s.parse_teor
s.parse_teor = lambda h: dict(orig(h), acordao="")   # simula regressão no cabeçalho ACÓRDÃO
print("  ler_recibo com parse_teor regredido:", [s.ler_recibo(a) for a in ("202638463", "202640467")])
print("  pasta depois:", sorted(os.listdir(s.DIR_RECIBOS)))
s.parse_teor = orig
print("  parse_teor consertado -> ler_recibo:", [s.ler_recibo(a) for a in ("202638463", "202640467")])
print("  -> os .json ORIGINAIS foram renomeados; a próxima leitura gasta REDE de novo (ou falha sem `numero_processo`)")

print("\n=== B) `buscar` usa os.path.exists: anuncia 'recibo do inteiro teor já em disco' para recibo inválido ===")
print("  _arq_recibo existe?", os.path.exists(s._arq_recibo("202638463")),
      "| _arq_recibo('…inconsistente') existe?", os.path.exists(s._arq_recibo("202638463") + ".inconsistente"))
bad = s._arq_recibo("999999999")
json.dump({"acordao": "999999999", "sha256": "0" * 64, "html": "<html>nada</html>", "processo": "1", "url": "",
           "obtido_em": ""}, open(bad, "w"))
print("  recibo corrompido gravado:", os.path.basename(bad))
print("  os.path.exists (o que `buscar` consulta):", os.path.exists(bad))
print("  ler_recibo (o que `obter` usa):", s.ler_recibo("999999999"))
print("  -> a busca diz 'recibo já em disco · 0 requisições' para algo que custará 1 requisição")

print("\n=== C) round-trip latin-1 -> utf-8 no sha256 ===")
h = H3
rec = s.gravar_recibo("202638463", "000000000000", h)
lido = json.load(open(s._arq_recibo("202638463")))
print("  sha gravado == sha recalculado:", hashlib.sha256(lido["html"].encode("utf-8")).hexdigest() == rec["sha256"])
fora = h[:100] + "€中" + h[100:]   # caracteres fora de latin-1
r2 = s.gravar_recibo("111111111", "1", fora)
print("  html com € e 中 (fora de latin-1): recibo relido confere:",
      hashlib.sha256(json.load(open(s._arq_recibo("111111111")))["html"].encode("utf-8")).hexdigest() == r2["sha256"])

print("\n=== D) disjuntor: _PAUSA_MEMORIA quando o disco falha ===")
s._PAUSA_MEMORIA = 0.0
open(s.ARQ_ESTADO, "w").write(json.dumps({"requisicoes": [], "pausa_ate": 0, "motivo": "", "incidentes": []}))
os.chmod(s.DIR_DADOS, 0o500)  # não dá para gravar o estado
try:
    s._pausar(1800, "falha de rede: teste")
    print("  _pausar com pasta só-leitura: _PAUSA_MEMORIA em", round(s._PAUSA_MEMORIA - time.time()), "s (memória)")
    print("  estado em disco:", json.load(open(s.ARQ_ESTADO)))
    print("  -> OUTRO processo lê o disco: pausa_ate =", json.load(open(s.ARQ_ESTADO))["pausa_ate"], "-> segue requisitando")
finally:
    os.chmod(s.DIR_DADOS, 0o700)

print("\n=== E) _pedir_vez com 4 voltas sob concorrência legítima ===")
s._PAUSA_MEMORIA = 0.0
agora = time.time()
json.dump({"requisicoes": [agora], "pausa_ate": 0, "motivo": "", "incidentes": []}, open(s.ARQ_ESTADO, "w"))


async def tres():
    t0 = time.time()
    r = await asyncio.gather(*(s._pedir_vez() for _ in range(3)), return_exceptions=True)
    return time.time() - t0, r


dt, r = asyncio.run(tres())
print(f"  3 pedidos concorrentes, 1 requisição há 0 s: {dt:.1f}s")
for x in r:
    print("   ", type(x).__name__, str(x)[:90])

print("\n=== F) _trava() sem flock: dois 'processos' reservam a mesma vaga? ===")
fc = s.fcntl
s.fcntl = None
json.dump({"requisicoes": [], "pausa_ate": 0, "motivo": "", "incidentes": []}, open(s.ARQ_ESTADO, "w"))


async def duas():
    return await asyncio.gather(s._pedir_vez(), s._pedir_vez(), return_exceptions=True)


print("  resultado:", [type(x).__name__ for x in asyncio.run(duas())])
print("  requisições registradas:", len(json.load(open(s.ARQ_ESTADO))["requisicoes"]))
s.fcntl = fc

print("\n=== G) poda de 24 h e DIA_MAX ===")
agora = time.time()
json.dump({"requisicoes": [agora - 90000] * 200 + [agora - 100] * 10, "pausa_ate": 0, "motivo": "", "incidentes": []},
          open(s.ARQ_ESTADO, "w"))
e = s._ler_estado()
print(f"  210 timestamps (200 com mais de 24 h) -> _ler_estado devolve {len(e['requisicoes'])}; DIA_MAX={s.DIA_MAX}")
print("  -> a poda está certa; mas DIA_MAX conta a JANELA MÓVEL de 24 h, não o dia civil (documentado?)")

print("\n=== H) detector de desafio: página de captcha SEM <body> nos 4000 primeiros chars ===")
pag = "<html><head>" + "<!-- " + "x" * 5000 + " -->" + "</head><body>cf-turnstile aqui</body></html>"
ib = pag[:4000].lower().find("<body")
cabeca = pag[: (ib + 250) if ib >= 0 else 1200].lower()
print("  <body> nos 4000 primeiros:", ib, "· marca detectada:", any(m in cabeca for m in s.MARCAS_DESAFIO))
pag2 = "<html><body>" + "y" * 400 + "cf-turnstile" + "</body></html>"
ib2 = pag2[:4000].lower().find("<body")
c2 = pag2[: ib2 + 250].lower()
print("  marca 400 chars depois de <body>:", any(m in c2 for m in s.MARCAS_DESAFIO), "(janela = <body>+250)")
