"""B1 — faixas_transcritas/conferir v0.3.0: falso alarme, miss, voto vencido, alegação da parte, bordas."""
import _base as b
import random
import re

s = b.s


def alerta(corpo, trecho):
    r = s.conferir(corpo, trecho)
    if not r["ok"]:
        return "❌ " + str(r.get("fragmento") or r.get("erro"))[:60]
    return ("TRANSCR" if any("TRANSCRIÇÃO" in a for a in r["alertas"]) else "") + \
           ("|NEG" if any("NEGAÇÃO" in a for a in r["alertas"]) else "") or "✅ limpo"


def janela(tn, ini, n=12):
    return " ".join(tn[ini:ini + 400].split()[:n])


print("=== A) taxa de alerta por REGIÃO, nos dois fixtures de teor ===")
for nome in ("03-relatorio-202638463.html", "08-relatorio-202640467.html"):
    d, corpo = b.teor(nome)
    tn = s.norm(corpo)
    iv = 0
    for mf in re.finditer(r"\bacordam\b", tn):
        if "estado de sergipe" in tn[mf.start(): mf.start() + 450]:
            iv = mf.start()
            break
    fx = s.faixas_transcritas(tn, iv)
    dentro = lambda p: any(a <= p < bb for a, bb in fx)
    random.seed(7)
    for rot, cond in (("DENTRO de faixa", dentro), ("FORA de faixa (palavra própria/voto)", lambda p: not dentro(p))):
        cand = [p for p in range(iv, len(tn) - 500, 37) if cond(p)]
        if not cand:
            print(f"  {nome} · {rot}: 0 posições")
            continue
        amo = random.sample(cand, min(120, len(cand)))
        res = {}
        exemplos = []
        for p in amo:
            j = janela(tn, p, random.randint(8, 15))
            a = alerta(corpo, j)
            res[a] = res.get(a, 0) + 1
            if len(exemplos) < 3:
                exemplos.append((p, a, j[:95]))
        print(f"  {nome} · {rot}: {len(amo)} janelas -> {res}")
        for p, a, j in exemplos:
            print(f"      @{p} [{a}] «{j}»")

print()
print("=== B) VOTO VENCIDO / DIVERGENTE (fixture 03, @20190 'peco venia para divergir') ===")
d, corpo = b.teor("03-relatorio-202638463.html")
tn = s.norm(corpo)
k = tn.find("peco venia para divergir")
print("  posição do 'peco venia para divergir':", k)
for off, n in ((30, 14), (300, 16), (700, 14)):
    j = janela(tn, k + off, n)
    print(f"    @{k+off} [{alerta(corpo, j)}] «{j[:100]}»")

print()
print("=== C) MISS: citações em formatos que _RE_ATRIB não cobre ===")
base_tjse = corpo[:1200]
casos = {
    "STJ sem parênteses": "O Superior Tribunal de Justiça firmou: REsp 1.234.567/SP, Rel. Min. Nancy Andrighi, DJe 12/03/2020, "
                          "no sentido de que a instituicao financeira responde objetivamente pelo defeito do servico prestado ao consumidor",
    "Precedentes:": "Precedentes: a contratacao de emprestimo consignado em nome de menor absolutamente incapaz, sem previa "
                    "autorizacao judicial, e nula de pleno direito e enseja repeticao em dobro",
    "Súmula transcrita": "Nos termos da Sumula 479 do STJ: as instituicoes financeiras respondem objetivamente pelos danos gerados "
                         "por fortuito interno relativo a fraudes e delitos praticados por terceiros no ambito de operacoes bancarias",
    "Tema repetitivo": "Tema 929/STJ: o prazo prescricional das acoes de repeticao de indebito de tarifas cobradas indevidamente "
                       "em contrato de prestacao de servico e de dez anos, contados da data do pagamento",
    "doutrina entre aspas": "Como ensina o professor Fulano de Tal, em sua Teoria Geral das Obrigacoes: a nulidade do negocio juridico "
                            "celebrado por absolutamente incapaz opera de pleno direito e independe de pronunciamento judicial constitutivo",
    "sentença de 1º grau": "Assim decidiu o juizo a quo: julgo improcedentes os pedidos formulados na inicial, porquanto nao comprovada "
                           "a alegada ausencia de autorizacao judicial para a contratacao impugnada pela parte autora",
    "parecer do MP": "O Ministerio Publico opinou nos seguintes termos: opina o parquet pelo provimento do recurso, por entender nula "
                     "a contratacao celebrada em nome do menor sem a necessaria autorizacao judicial previa",
    "razões da parte": "Sustenta o apelante que a contratacao foi regular e que houve efetiva disponibilizacao do numerario na conta "
                       "indicada pela representante legal do menor, inexistindo qualquer vicio de consentimento a ser reconhecido",
    "contrarrazões": "Aduz a parte apelada que o contrato e plenamente valido e que a devolucao dos valores implicaria enriquecimento "
                     "sem causa da parte autora, devendo ser mantida integralmente a sentenca de improcedencia",
}
for rot, txt in casos.items():
    fake = base_tjse + " " + txt + " " + corpo[1200:2000]
    trecho = " ".join(txt.split()[-14:])
    r = s.conferir(fake, trecho)
    print(f"  {rot:24s} -> ok={r['ok']} alertas={r.get('alertas')}")

print()
print("=== D) alerta de ALEGAÇÃO DA PARTE: existe algo equivalente ao de NEGAÇÃO? ===")
for verbo in ("sustenta o apelante que", "alega a parte autora que", "aduz o recorrente que",
              "afirma o agravante que", "argumenta a defesa que"):
    fake = base_tjse + " " + verbo + " a contratacao e nula por ausencia de autorizacao judicial previa do juizo competente " + corpo[1200:1600]
    r = s.conferir(fake, "a contratacao e nula por ausencia de autorizacao judicial previa")
    print(f"  '{verbo}' -> ok={r['ok']} alertas={r.get('alertas')}")

print()
print("=== E) _RE_ATRIB casa coisa banal? ===")
for t in ["(ai, rel. de forma clara, o contrato)", "(re) analisando os autos, o julgador concluiu que",
          "(ac. unanime, rel. do voto) ", "(ms, rel. pelo autor)", "(hc, conforme rel. anterior)",
          "(ai) o relator", "(ms — rel"]:
    print(f"  {t!r:46s} -> casa: {bool(s._RE_ATRIB.search(s.norm(t)))}")

print()
print("=== F) piso / bordas / normalização ===")
d8, c8 = b.teor("08-relatorio-202640467.html")
amostras = []
tn8 = s.norm(c8)
casos2 = [
    ("4 palavras e 25+ chars (no limite)", " ".join(tn8[3000:3400].split()[:4])),
    ("3 palavras", " ".join(tn8[3000:3400].split()[:3])),
    ("[...] no começo", "[...] " + " ".join(tn8[3000:3400].split()[:8])),
    ("[...] no fim", " ".join(tn8[3000:3400].split()[:8]) + " [...]"),
    ("só [...]", "[...]"),
]
for rot, t in casos2:
    r = s.conferir(c8, t)
    print(f"  {rot:34s} -> ok={r['ok']} erro={str(r.get('erro') or r.get('fragmento'))[:70]}")

print()
print("  --- norm(): colagem de pontuação cria FALSO ✅? ---")
pares = [
    ("fim de frase. Inicio de outra", "frase .Inicio"),
    ("o valor de R$ 5.000,00 (cinco mil reais)", "R$ 5.000,00 ( cinco mil reais )"),
    ("art. 42, paragrafo unico do CDC", "art . 42 , paragrafo unico"),
    ("o §1º do artigo", "o § 1º do artigo"),
    ("nº 1.691", "n. 1.691"),
    ("1ª Camara", "1a Camara"),
    ("meia-tigela", "meia—tigela"),
]
for texto, trecho in pares:
    texto_full = "a" * 200 + " " + texto + " " + "b" * 200
    r = s.conferir(texto_full, trecho)
    print(f"  texto={texto!r:44s} trecho={trecho!r:34s} -> ok={r['ok']}")

print()
print("  --- fragmento repetido: casa na 2ª ocorrência e infla o vão? ---")
rep = "a contratacao sem autorizacao judicial e nula"
texto = "x " * 400 + rep + " y " * 500 + rep + " z " * 50
r = s.conferir(texto, rep + " [...] " + rep)
print("   duas ocorrências, [...] entre elas ->", {k: v for k, v in r.items() if k != "contexto"})

print()
print("  --- vão de 1.500: bordas ---")
for gap in (1400, 1499, 1501, 1600):
    texto = "alfa beta gama delta epsilon" + " q" * (gap // 2) + " zeta eta theta iota kappa"
    r = s.conferir(texto, "alfa beta gama delta epsilon [...] zeta eta theta iota kappa")
    print(f"   gap~{gap}: ok={r['ok']} {str(r.get('erro'))[:60]}")
