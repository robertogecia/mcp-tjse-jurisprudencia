"""B12 — sincronizar OFFLINE com _http falso (zero rede): menu vazio cacheado, página de erro COM <h4>,
seção vazia marcada como baixada, lista de edições paginada, `falta`."""
import _base as b
import asyncio
import gzip
import json
import os
import re

s = b.s
MENU = b.fx("05-menu-168.html")
LISTA = b.fx("02-pesquisa-1ano.html")
SEC = os.path.join(b.RAIZ, "base", "secoes")
arq = sorted(f for f in os.listdir(SEC) if re.fullmatch(r"\d+-\d+\.html\.gz", f))[0]
BRUTO = gzip.open(os.path.join(SEC, arq), "rb").read().decode("utf-8")

print("=== 0) lista de edições (fixture 02, pesquisa de 1 ano) ===")
eds = s.parse_edicoes(LISTA)
print(f"  {len(eds)} edições reconhecidas: {[e['edicao'] for e in eds]}")
print("  há controle de PRÓXIMA PÁGINA na lista?",
      bool(re.search(r"(?i)nav_go|pr[oó]xim|submitWIGrid", LISTA)),
      "| proxima_posicao:", s.proxima_posicao(LISTA))

CHAMADAS = []


def http_falso(mapa):
    async def f(metodo, url, *, params=None, data=None, referer=None):
        CHAMADAS.append((metodo, url.rsplit("/", 1)[-1], (data or params or {}).get("tmp.diario.cd_secao")))
        for k, v in mapa.items():
            if k in url:
                return v(data or params or {}) if callable(v) else v
        raise AssertionError("url inesperada " + url)
    return f


def zerar():
    import shutil
    shutil.rmtree(s.DIR_BASE, ignore_errors=True)
    os.makedirs(s.DIR_SECOES, exist_ok=True)
    CHAMADAS.clear()


print("\n=== A) menu que volta VAZIO fica cacheado como [] para SEMPRE ===")
zerar()
s._http = http_falso({"pesquisar.wsp": LISTA, "menu.wsp": "<html><body>erro temporario</body></html>",
                      "principal.wsp": BRUTO})
r = asyncio.run(s.sincronizar(meses=1, max_requisicoes=14))
print("  1ª chamada:", r.splitlines()[0], "|", [l for l in r.splitlines() if "Falta" in l or "completo" in l])
con = s._db()
print("  meta menu:*:", [(k, v) for k, v in con.execute("SELECT chave, valor FROM meta WHERE chave LIKE 'menu:%'")][:3])
con.close()
s._http = http_falso({"pesquisar.wsp": LISTA, "menu.wsp": MENU, "principal.wsp": BRUTO})
CHAMADAS.clear()
r2 = asyncio.run(s.sincronizar(meses=1, max_requisicoes=14))
print("  2ª chamada (menu.wsp já FUNCIONANDO):", r2.splitlines()[0])
print("   requisições feitas:", CHAMADAS)
print("   resultado:", [l for l in r2.splitlines() if "Falta" in l or "completo" in l or "Índice" in l])
print("  >>> a edição inteira ficou invisível E declarada completa; nenhuma nova requisição de menu")

print("\n=== B) página de ERRO que CONTÉM '<h4>Boletim n.' e nenhum acórdão ===")
zerar()
erro = "<html><body><h4>Boletim n. 168</h4><p>Nenhum registro encontrado para os parametros informados.</p></body></html>"
s._http = http_falso({"pesquisar.wsp": LISTA, "menu.wsp": MENU, "principal.wsp": erro})
r = asyncio.run(s.sincronizar(meses=1, max_requisicoes=14))
print("\n".join("  " + l for l in r.splitlines()))
con = s._db()
print("  tabela secoes:", [dict(x) for x in con.execute("SELECT * FROM secoes")][:3])
con.close()
print("  >>> seções marcadas como BAIXADAS com itens=0, sem ⚠ — não serão tentadas de novo")

print("\n=== C) mesma página, 2ª chamada: as seções são puladas para sempre? ===")
s._http = http_falso({"pesquisar.wsp": LISTA, "menu.wsp": MENU, "principal.wsp": BRUTO})
CHAMADAS.clear()
r = asyncio.run(s.sincronizar(meses=1, max_requisicoes=14))
print("  requisições feitas na 2ª chamada:", CHAMADAS)
print("  " + [l for l in r.splitlines() if "Índice" in l][0])

print("\n=== D) custo de rede ETERNO de uma seção que nunca é marcada (sem h4, sem links) ===")
zerar()
vazio = "<html><body>servico indisponivel</body></html>"
s._http = http_falso({"pesquisar.wsp": LISTA, "menu.wsp": MENU, "principal.wsp": vazio})
r = asyncio.run(s.sincronizar(meses=1, max_requisicoes=14))
n1 = len([c for c in CHAMADAS if c[1] == "principal.wsp"])
CHAMADAS.clear()
asyncio.run(s.sincronizar(meses=1, max_requisicoes=14))
n2 = len([c for c in CHAMADAS if c[1] == "principal.wsp"])
print(f"  requisições a principal.wsp: 1ª chamada {n1}, 2ª chamada {n2} — repete indefinidamente")
print("  (correto: NÃO marcar; o custo é {} req/chamada até o portal voltar)".format(n2))

print("\n=== E) `meses` -> janela de datas realmente pedida ===")
import datetime as dt
hoje = dt.date.today()
for m in (1, 3, 12, 24, 0, 99):
    mm = max(1, min(int(m), 24))
    ini = (hoje.replace(day=1) - dt.timedelta(days=31 * mm)).replace(day=1)
    print(f"  meses={m} -> {mm} -> dt_inicio={ini:%d/%m/%Y} ({(hoje-ini).days} dias)")
