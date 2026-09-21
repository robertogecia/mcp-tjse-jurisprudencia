"""B13 — honestidade da saída: datas invertidas, por_pagina/max_caracteres absurdos, com_partes,
ordenação anunciada, numero CNJ, docstrings x comportamento."""
import _base as b
import asyncio
import gzip
import os
import re

s = b.s
SEC = os.path.join(b.RAIZ, "base", "secoes")
arq = sorted(f for f in os.listdir(SEC) if re.fullmatch(r"\d+-\d+\.html\.gz", f))[0]
ed, cod = (int(x) for x in arq.replace(".html.gz", "").split("-"))
BRUTO = gzip.open(os.path.join(SEC, arq), "rb").read().decode("utf-8")
os.makedirs(s.DIR_SECOES, exist_ok=True)
con = s._db()
con.execute("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)", (ed, str(ed), "2026-08-31"))
s.guardar_bruto(ed, cod, BRUTO)
itens = s.parse_secao(BRUTO)
s.indexar_secao(con, ed, cod, "Tribunal Pleno", itens)
um = itens[0]
con.close()
print(f"índice: {len(itens)} acórdãos · exemplo {um['acordao']}")


def l1(t, n=3):
    return " | ".join(t.splitlines()[:n])


print("\n=== A) data_inicio > data_fim ===")
print(" ", l1(s.buscar(consulta="dano", data_inicio="01/01/2027", data_fim="01/01/2020"), 4))

print("\n=== B) por_pagina absurdo / negativo / paginação além do fim ===")
for pp in (0, -5, 1, 10000):
    print(f"  por_pagina={pp:7d} ->", l1(s.buscar(consulta="dano", por_pagina=pp), 2).split("—")[0:2])
print("  pagina=-3 ->", l1(s.buscar(consulta="dano", pagina=-3), 2))
print("  pagina=999 ->", l1(s.buscar(consulta="dano", pagina=999), 2))

print("\n=== C) ordenação anunciada x ordenação usada (só `numero`, sem consulta) ===")
r = s.buscar(numero=um["acordao"], ordenacao="relevantes")
print("  ", [x for x in r.splitlines() if "ordem:" in x])
print("   -> não há MATCH; o código cai no ramo 'ORDER BY edicao', mas a saída anuncia 'relevantes'")

print("\n=== D) numero CNJ e números fora de 9/12 dígitos ===")
for n in ("0006321-12.2026.8.25.0001", "123", "202638463", "202600737656", "", "abc"):
    r = s.buscar(numero=n)
    print(f"  {n!r:28s} -> {l1(r,2)[:150]}")

print("\n=== E) max_caracteres <= 0 / minúsculo (obter) ===")
s.gravar_recibo("202638463", "202600737656", b.fx("03-relatorio-202638463.html"))
for mc in (60000, 300, 1, 0, -10):
    out = asyncio.run(s.obter("202638463", max_caracteres=mc))
    nivel = [x for x in out.splitlines() if x.startswith("Citação:")]
    corpo = out.split("─" * 60 + "\n", 1)[-1]
    print(f"  max_caracteres={mc:6d} -> corpo {len(corpo):6d} chars · 'EM PARTE' na citação: "
          f"{'EM PARTE' in (nivel[0] if nivel else '')}")
    if mc <= 0:
        print("     citação:", (nivel[0] if nivel else "")[:150])

print("\n=== F) com_partes=True: a saída ainda diz que cortou? ===")
out = asyncio.run(s.obter("202638463", com_partes=True))
print("  linhas de ressalva:", [x[:95] for x in out.splitlines() if "QUALIFICA" in x or "partes" in x.lower()][:3])
d = s.parse_teor(b.fx("03-relatorio-202638463.html"))
print("  partes_cortadas =", d["partes_cortadas"], "· inicio_conteudo =", d["inicio_conteudo"])
out2 = asyncio.run(s.obter("202638463", com_partes=False))
for alvo in ("GENITORA FICTÍCIA", "menor impúbere", "M.F.S"):
    print(f"   com_partes=False · {alvo!r} na saída: {alvo.lower() in out2.lower()}")

print("\n=== G) docstring x comportamento: 'cole a URL do inteiro teor em numero_acordao' ===")
url = "https://www.tjse.jus.br/tjnet/jurisprudencia/relatorio.wsp?tmp.numprocesso=202600737656&tmp.numacordao=202638463"
print("  onde_mais_procurar() promete:", "cole a URL do inteiro teor em `numero_acordao`" in s.onde_mais_procurar())
print("  re.sub(r'\\D','',url) =", re.sub(r"\D", "", url)[:60])
print("  obter(url) ->", l1(asyncio.run(s.obter(url)), 2))

print("\n=== H) 'Nada no índice' quando o filtro é que não casa (e a expressão fica ilegível) ===")
print(" ", l1(s.buscar(consulta="dano", orgao="Câmara Inexistente"), 2))
print(" ", l1(s.buscar(grupos=[["dano moral"], ["xyzinexistente"]]), 2))
