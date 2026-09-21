"""B15 — veredito sobre os achados ALTA/MÉDIA do 1º red team (21/09/2026) contra a versão corrente."""
import _base as b
import asyncio
import json
import os
import re
import time

s = b.s
d3, c3 = b.teor("03-relatorio-202638463.html")
d8, c8 = b.teor("08-relatorio-202640467.html")
print("VERSAO auditada agora:", s.VERSAO)

print("\n1 (ALTA) alerta de TRANSCRIÇÃO por pertencimento à faixa")
tn = s.norm(c3)
fx = s.faixas_transcritas(tn, 1505)
dentro = sum(bb - a for a, bb in fx)
print(f"   faixas cobrem {dentro} chars; trecho no meio de bloco TJ-RO @9483:",
      s.conferir(c3, " ".join(tn[9483:9800].split()[:12])).get("alertas"))
print("   VEREDITO: fechado para atribuição '(TJ-XX - …)'; ver B1 (formato sem parênteses) e B3 (falso alarme)")

print("\n2 (ALTA) órgão do fecho pela POSIÇÃO no texto")
fake = c3[:1500] + "\nACORDAM os Desembargadores da 2ª Câmara Cível do Tribunal de Justiça do Estado de Sergipe, tendo o Tribunal Pleno já decidido, em negar provimento.\n"
d = s.parse_teor(fake)
print("   2ª Câmara Cível + 'Tribunal Pleno' de passagem ->", d["orgao_fecho"], "| ambiguo:", d["fecho_ambiguo"])
fake2 = c3[:1500] + "\nACORDAM os membros da Câmara Criminal do Tribunal de Justiça do Estado de Sergipe, na linha da Seção Especializada Cível, em negar.\n"
print("   Câmara Criminal + 'Seção Especializada Cível' ->", s.parse_teor(fake2)["orgao_fecho"])
print("   VEREDITO:", "fechado" if s.parse_teor(fake)["orgao_fecho"] == "2ª Câmara Cível" else "ABERTO")

print("\n3 (ALTA) com_partes=False promete omitir partes")
s.gravar_recibo("202638463", "202600737656", b.fx("03-relatorio-202638463.html"))
out = asyncio.run(s.obter("202638463"))
print("   frase da ressalva:", [l[:110] for l in out.splitlines() if "QUALIFICA" in l])

print("\n4 (ALTA) recibo com o HTML de OUTRO acórdão")
caminho = s._arq_recibo("202638463")
rec = json.load(open(caminho))
rec["html"] = b.fx("08-relatorio-202640467.html")
rec["sha256"] = __import__("hashlib").sha256(rec["html"].encode()).hexdigest()
json.dump(rec, open(caminho, "w"))
print("   ler_recibo com HTML trocado:", s.ler_recibo("202638463"))
print("   VEREDITO: fechado (recibo posto de lado) — mas ver B-cascata")

print("\n5 (ALTA) seção vazia marcada como baixada -> ver B12(B): REABERTO pelo critério `<h4>Boletim n.`")
print("   anomalias_secao([]) =", s.anomalias_secao([]), "| chamada só `if itens` (l.~869): segue nunca impressa")

print("\n6 (ALTA) negação não detectada")
for t in ("improcedente o pedido de indenização por danos morais que o autor formulou",
          "nega-se provimento ao recurso do banco réu por falta de amparo legal nenhum",
          "rejeita-se a tese de prescrição quinquenal suscitada pela parte ré nos autos",
          "sem razão a parte agravante quanto à gratuidade da justiça ora requerida"):
    doc = "x" * 300 + " " + t + " " + "y" * 300
    tre = " ".join(t.split()[1:9])
    r = s.conferir(doc, tre)
    print(f"   {t[:40]!r:44s} alerta_negacao={any('NEGA' in a for a in r.get('alertas', []))}")

print("\n7 (ALTA) MARCAS_DESAFIO e ementa com 'captcha'")
sec = b.fx("07-principal-168-sec5.html")
ib = sec[:4000].lower().find("<body")
cab = sec[: (ib + 250) if ib >= 0 else 1200].lower()
print("   seção real marcaria desafio?", any(m in cab for m in s.MARCAS_DESAFIO), "| 'captcha' ainda na lista?",
      any("captcha" == m for m in s.MARCAS_DESAFIO))
print("   VEREDITO: fechado — mas ver B (evasão: <body> além de 4000 chars / marca além de +250)")

print("\n8 (ALTA) _pedir_vez com timestamp no FUTURO")
json.dump({"requisicoes": [time.time() + 7200], "pausa_ate": 0, "motivo": "", "incidentes": []}, open(s.ARQ_ESTADO, "w"))
t0 = time.time()
try:
    asyncio.run(s._pedir_vez())
    print(f"   retornou em {time.time()-t0:.1f}s (sem laço infinito)")
except Exception as ex:
    print(f"   {type(ex).__name__} em {time.time()-t0:.1f}s: {ex}")

print("\n9 (MÉDIA) data_julgamento: última data + aviso")
fake = c3[:1500] + "\nACORDAM os Desembargadores da 1ª Câmara Cível do Tribunal de Justiça do Estado de Sergipe em negar.\nAracaju, 3 de junho de 2026.\nAracaju, 17 de julho de 2026.\n"
d = s.parse_teor(fake)
print("   duas datas ->", d["data_julgamento"], "| datas_fecho:", d["datas_fecho"])
fake3 = c3[:1500] + "\nACORDAM ... do Tribunal de Justiça do Estado de Sergipe em negar.\nAracaju, 17/07/2026.\n"
print("   data numérica ->", s.parse_teor(fake3)["data_julgamento"], "(ainda some sem aviso)")

print("\n10 (MÉDIA) 'EM PARTE' quando corta -> ver B13(E): fechado")
print("\n11 (MÉDIA) relator duplo -> ver B5: fechado para rótulos conhecidos; ABERTO para rótulo com erro de grafia")

print("\n12 (MÉDIA) estado com tipos errados")
for mau in ({"requisicoes": [], "pausa_ate": "amanha"}, {"requisicoes": ["x", 1.0]}, {"requisicoes": {}},
            {"pausa_ate": None}):
    json.dump(mau, open(s.ARQ_ESTADO, "w"))
    try:
        e = s._ler_estado()
        print(f"   {str(mau)[:38]:40s} -> ok, pausa_ate={e['pausa_ate']!r} reqs={e['requisicoes']}")
    except Exception as ex:
        print(f"   {str(mau)[:38]:40s} -> {type(ex).__name__}: {ex}")
    try:
        s._pausar(60, "t")
    except Exception as ex:
        print("       _pausar ->", type(ex).__name__, ex)

print("\n13 (MÉDIA) .lock sem permissão de escrita")
json.dump({"requisicoes": [], "pausa_ate": 0, "motivo": "", "incidentes": []}, open(s.ARQ_ESTADO, "w"))
os.chmod(s.DIR_DADOS, 0o500)
try:
    try:
        asyncio.run(s._pedir_vez())
        print("   _pedir_vez: passou SEM trava e SEM registrar?")
    except Exception as ex:
        print("   _pedir_vez ->", type(ex).__name__, str(ex)[:100])
    try:
        print("   diagnostico ->", s.diagnostico().splitlines()[0][:90])
    except Exception as ex:
        print("   diagnostico ->", type(ex).__name__, ex)
    try:
        s._pausar(1800, "rede")
        print("   _pausar: ok (memória), _PAUSA_MEMORIA em", round(s._PAUSA_MEMORIA - time.time()), "s")
    except Exception as ex:
        print("   _pausar ->", type(ex).__name__, ex)
finally:
    os.chmod(s.DIR_DADOS, 0o700)

print("\n14 (MÉDIA) grupo que se reduz a vazio")
try:
    print("   grupos=[['conflito'],['§§§']] ->", s.montar_fts(None, [["conflito"], ["§§§"]]))
except ValueError as ex:
    print("   recusado:", str(ex)[:100])
print("   consulta='conflito §§§' ->", repr(s.montar_fts("conflito §§§", None)), "<<< some em silêncio")

print("\n15 (MÉDIA) inicio_conteudo sem EMENTA / grafia espaçada")
print("   'E M E N T A' ->", s.parse_teor(b.fx("03-relatorio-202638463.html").replace("EMENTA", "E M E N T A"))["inicio_conteudo"])
sem = b.fx("03-relatorio-202638463.html").replace("EMENTA", "XXXXXX")
d = s.parse_teor(sem)
print("   sem nenhuma EMENTA -> inicio_conteudo =", d["inicio_conteudo"], "| partes_cortadas =", d["partes_cortadas"])

print("\n16 (MÉDIA) 'Faltam ≥ N' -> B12: usa 5 e diz '≥'; mas menu cacheado como [] faz n_secs=0")
print("\n17 (MÉDIA) numero CNJ -> B13(D): recusado com explicação. fechado")
print("\n18 (MÉDIA) falso ❌ em 'art . 42'")
for texto, cit in (("o CDC, art . 42, parágrafo único, impõe a devolução em dobro dos valores",
                    "art. 42, parágrafo único, impõe a devolução em dobro"),
                   ("o processo 1.0000 .24.449766-5 do TJMG foi mencionado no voto condutor",
                    "1.0000.24.449766-5 do TJMG foi mencionado")):
    print("   ->", s.conferir("z" * 200 + " " + texto + " " + "w" * 200, cit)["ok"])

print("\n19 (MÉDIA) republicação -> tabela `republicacoes` + ⚠ na busca: existe (B7 mostra a tabela)")
print("\n20 (MÉDIA) modo de recibos/:", oct(os.stat(s.DIR_RECIBOS).st_mode & 0o777) if os.path.isdir(s.DIR_RECIBOS) else "—")
print("\n21 (MÉDIA) diagnostico com base corrompida:")
open(s.ARQ_DB, "wb").write(b"nao sou um banco")
print("   buscar ->", s.buscar(consulta="dano")[:80])
print("   diagnostico ->", s.diagnostico()[:110])
