"""B11 — corrida REAL entre processos: (a) reserva do disjuntor sem flock; (b) dois processos reindexando."""
import _base as b
import json
import multiprocessing as mp
import os
import time

s = b.s
DIR = os.environ["TJSE_DIR_DADOS"]


def reservar(sem_flock, barreira, q):
    os.environ["TJSE_DIR_DADOS"] = DIR
    import sys
    sys.path.insert(0, b.RAIZ)
    sys.modules.pop("servidor_tjse", None)
    import asyncio
    import servidor_tjse as m
    m.httpx = None
    if sem_flock:
        m.fcntl = None
    barreira.wait()
    try:
        asyncio.run(m._pedir_vez())
        q.put("ok")
    except Exception as ex:
        q.put(f"{type(ex).__name__}: {ex}")


if __name__ == "__main__":
    mp.set_start_method("fork")
    for sem_flock in (False, True):
        json.dump({"requisicoes": [], "pausa_ate": 0, "motivo": "", "incidentes": []}, open(s.ARQ_ESTADO, "w"))
        n = 6
        bar, q = mp.Barrier(n), mp.Queue()
        ps = [mp.Process(target=reservar, args=(sem_flock, bar, q)) for _ in range(n)]
        [p.start() for p in ps]
        [p.join(30) for p in ps]
        res = [q.get() for _ in range(n)]
        reg = len(json.load(open(s.ARQ_ESTADO))["requisicoes"])
        ok = sum(1 for r in res if r == "ok")
        print(f"\n  flock={'OFF' if sem_flock else 'ON '} · {n} processos simultâneos · "
              f"{ok} obtiveram vez · {reg} requisições REGISTRADAS no estado")
        if ok != reg:
            print(f"    >>> PERDA DE REGISTRO: {ok - reg} requisição(ões) feitas sem constar do disjuntor")
        for r in sorted(set(res)):
            print("     ", r[:95], f"x{res.count(r)}")
