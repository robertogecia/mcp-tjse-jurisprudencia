#!/usr/bin/env python3
"""Baixa ~40 inteiros teores do TJSE (um a um, 32 s entre pedidos, teto do portal respeitado) para medir as regras de
atribuição às cegas. Autorizado pelo usuário em 06/10/2026. Para em dois PESQUISA NÃO REALIZADA seguidos."""
import asyncio, os, sqlite3, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import servidor_tjse as st
db = sqlite3.connect(os.path.expanduser("~/.tjse-jurisprudencia/base/boletim.db"))
ja = {f[:-5] for f in os.listdir(st.DIR_RECIBOS) if f.endswith(".json")}
quotas = {"1ª Câmara Cível": 14, "2ª Câmara Cível": 14, "Câmara Criminal": 6, "Tribunal Pleno": 3, "Seção Especializada Cível": 3}
alvos = []
for orgao, n in quotas.items():
    rows = db.execute("select acordao from acordaos where orgao=? and edicao>=165 order by edicao desc, acordao desc limit ?", (orgao, n + 10)).fetchall()
    alvos += [r[0] for r in rows if r[0] not in ja][:n]
print("alvos:", len(alvos), flush=True)
async def main():
    falhas, ok = 0, 0
    for i, a in enumerate(alvos):
        t0 = time.time()
        r = await st.obter(a)
        if r.startswith("PESQUISA NÃO REALIZADA") or r.startswith("Pedido recusado"):
            falhas += 1; print(f"{i+1}/{len(alvos)} {a} FALHA: {r[:160]}", flush=True)
            if falhas >= 2: print("duas falhas seguidas — parando", flush=True); break
            await asyncio.sleep(120); continue
        falhas = 0; ok += 1
        print(f"{i+1}/{len(alvos)} {a} ok ({len(r)} chars, {time.time()-t0:.1f}s)", flush=True)
        await asyncio.sleep(32)
    print("concluído:", ok, "recibos novos", flush=True)
asyncio.run(main())
