"""B2 — taxa de FALSO ALARME e de MISS do alerta de TRANSCRIÇÃO, janelas snapadas em palavra inteira."""
import _base as b
import random
import re

s = b.s


def medir(nome):
    d, corpo = b.teor(nome)
    tn = s.norm(corpo)
    iv = 0
    for mf in re.finditer(r"\bacordam\b", tn):
        if "estado de sergipe" in tn[mf.start(): mf.start() + 450]:
            iv = mf.start()
            break
    fx = s.faixas_transcritas(tn, iv)
    print(f"\n### {nome} · corpo {len(corpo)} · inicio_voto {iv} · faixas {fx}")
    cob = sum(bb - a for a, bb in fx)
    print(f"    cobertura das faixas: {cob} de {len(tn)-iv} chars pós-fecho = {100*cob/max(1,len(tn)-iv):.0f}%")
    palavras = [(m.start(), m.group()) for m in re.finditer(r"\S+", tn)]
    dentro = lambda a, bb: any(a < f2 and bb > f1 for f1, f2 in fx)
    random.seed(11)
    for rot, quero in (("DENTRO de faixa (é palavra de outro tribunal)", True),
                       ("FORA de faixa (é palavra própria do TJSE)", False)):
        res, exemplos = {"ALERTA": 0, "sem alerta": 0}, []
        tent = 0
        while res["ALERTA"] + res["sem alerta"] < 100 and tent < 4000:
            tent += 1
            i = random.randrange(0, len(palavras) - 16)
            n = random.randint(8, 15)
            a, bb = palavras[i][0], palavras[i + n - 1][0] + len(palavras[i + n - 1][1])
            if a < iv or dentro(a, bb) != quero:
                continue
            tre = tn[a:bb]
            r = s.conferir(corpo, tre)
            if not r["ok"]:
                continue
            tem = any("TRANSCRIÇÃO" in x for x in r["alertas"])
            res["ALERTA" if tem else "sem alerta"] += 1
            if tem != quero and len(exemplos) < 3:
                exemplos.append((a, tre[:95]))
        n = res["ALERTA"] + res["sem alerta"]
        erra = res["sem alerta"] if quero else res["ALERTA"]
        print(f"  {rot}: {n} janelas conferíveis · alerta em {res['ALERTA']}"
              f" -> {'MISS' if quero else 'FALSO ALARME'} em {erra} ({100*erra/max(1,n):.0f}%)")
        for a, t in exemplos:
            print(f"      @{a} «{t}»")


for f in ("03-relatorio-202638463.html", "08-relatorio-202640467.html"):
    medir(f)

print("\n=== dispositivo / fecho do PRÓPRIO TJSE cai dentro de faixa? ===")
for nome in ("03-relatorio-202638463.html", "08-relatorio-202640467.html"):
    d, corpo = b.teor(nome)
    tn = s.norm(corpo)
    for alvo in ("ante o exposto", "isto posto", "nego provimento", "conheco do recurso", "e como voto",
                 "acordam os desembargadores", "acordam os membros", "tese de julgamento"):
        k = tn.find(alvo)
        if k < 0:
            continue
        tre = " ".join(tn[k:k + 300].split()[:12])
        r = s.conferir(corpo, tre)
        print(f"  {nome[:2]} @{k} «{alvo}» -> ok={r['ok']} alertas={[x[:12] for x in r.get('alertas',[])]}")
