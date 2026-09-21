"""t6 (v0.2.0) — sincronizar/indexar/parsers de lista: seção vazia SEM links marcada como feita,
contagem `falta`, relator PARA O ACÓRDÃO, ementa com 'PROCESSO:', menu com aspas, edição sem data."""
import asyncio, json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import *

H7 = fx("07-principal-168-sec5.html")
con = s._db()
con.execute("INSERT OR REPLACE INTO edicoes VALUES(168,'72026','2026-08-31')"); con.commit()

print("=== A) seção vazia SEM 'relatorio.wsp' (erro 200 do WebIntegrator) ainda é marcada como feita ===")
erro200 = "<html><body><table><tr><td>Servi&ccedil;o temporariamente indispon&iacute;vel</td></tr></table></body></html>"
itens = s.parse_secao(erro200)
print("   parse_secao ->", itens, "| 'relatorio.wsp' na resposta:", "relatorio.wsp" in erro200)
print("   guarda l.645: `if not itens and 'relatorio.wsp' in hs` -> NÃO dispara; cai em indexar_secao")
s.indexar_secao(con, 168, 6, "1ª Câmara Cível", itens)
print("   secoes:", dict(con.execute("SELECT * FROM secoes WHERE edicao=168 AND codigo=6").fetchone()))
print("   anomalias_secao([]) =", s.anomalias_secao([]), "— mas l.651 só a calcula `if itens`, então nunca é impressa")
print("   sincronizar pula seção já em `secoes` (l.633): as ~808 ementas da 1ª CC ficam fora para sempre")
print("   cobertura mente:", s.cobertura(con))

print("\n=== B) contagem `falta` para edição cujo menu nunca foi baixado ===")
con.execute("INSERT OR REPLACE INTO edicoes VALUES(167,'62026','2026-07-31')"); con.commit()
print("   menu:167 em meta?", bool(con.execute("SELECT 1 FROM meta WHERE chave='menu:167'").fetchone()),
      "-> n_secs assumido = 1 (l.657); real (ed. 168) =", len(s.parse_menu(fx("05-menu-168.html"))))
print("   'Faltam ~N seção(ões)' subconta 4 seções por edição ainda não visitada")

print("\n=== C) relator: com dois rótulos, vence o PRIMEIRO da célula ===")
it = s.parse_secao(H7)[0]
print("   item real:", {k: it[k] for k in ("acordao", "relator_rotulo", "relator")})
h2 = H7.replace("RELATOR ORIGIN&Aacute;RIO:",
                "RELATOR PARA O AC&Oacute;RD&Atilde;O: DES. RUY PINHEIRO DA SILVA</b><br /><b>RELATOR ORIGIN&Aacute;RIO:", 1)
it2 = s.parse_secao(h2)[0]
print("   com os dois rótulos ->", {k: it2[k] for k in ("relator_rotulo", "relator")})
h3 = H7.replace("RELATOR ORIGIN&Aacute;RIO: DES. CEZ&Aacute;RIO SIQUEIRA NETO",
                "RELATOR ORIGIN&Aacute;RIO: DES. CEZ&Aacute;RIO SIQUEIRA NETO</b><br /><b>RELATOR PARA O AC&Oacute;RD&Atilde;O: DES. RUY PINHEIRO DA SILVA", 1)
it3 = s.parse_secao(h3)[0]
print("   originário primeiro    ->", {k: it3[k] for k in ("relator_rotulo", "relator")})

print("\n=== D) ementa que contém 'PROCESSO:' (sem <a> logo depois) ===")
h4 = H7.replace("EXECU&Ccedil;&Atilde;O DE T&Iacute;TULO EXTRAJUDICIAL",
                "EXECU&Ccedil;&Atilde;O. NOS AUTOS DO PROCESSO: 0001/2020, SEGUE", 1)
print("   ementa:", repr(s.parse_secao(h4)[0]["ementa"][:130]))

print("\n=== E) parse_menu com aspas no nome da seção ===")
bom = 'lastPage("1&ordf; C&acirc;mara C&iacute;vel<!--6-->","&0","javascript:abre(\'6\',\'168\');")'
ruim = 'lastPage("C&acirc;mara "Especial"<!--9-->","&0","javascript:abre(\'9\',\'168\');")'
print("   normal:", s.parse_menu(bom), "\n   com aspas:", s.parse_menu(ruim), "-> seção some do menu, sem aviso")

print("\n=== F) parse_edicoes com data não reconhecida ===")
print("   ", s.parse_edicoes("ver('999');\"><b>12026</b><br><i>(30 de Fevereiro de 2026)</i>"))
print("   ", s.parse_edicoes("ver('998');\"><b>22026</b><br><i>(31 de Agôsto de 2026)</i>"))

print("\n=== G) republicação/retificação em edição posterior é descartada (l.449-450) ===")
it = s.parse_secao(H7)
retif = [dict(it[0], ementa="RETIFICAÇÃO. ONDE SE LÊ PROVIDO, LEIA-SE DESPROVIDO.")]
s.indexar_secao(con, 168, 5, "Seção Especializada Cível", it)
con.execute("INSERT OR REPLACE INTO edicoes VALUES(170,'92026','2026-10-31')"); con.commit()
print("   indexar retificação na ed. 170 ->", s.indexar_secao(con, 170, 5, "Seção Especializada Cível", retif), "novos")
print("   ementa em base:", con.execute("SELECT substr(ementa,1,55) FROM acordaos WHERE acordao=?",
      (it[0]["acordao"],)).fetchone()[0], "(a retificação não aparece em lugar nenhum da saída)")

print("\n=== H) sincronizar com orçamento inválido ===")
async def fake(*a, **k): raise s.PesquisaNaoRealizada("rede desligada no teste")
import servidor_tjse; servidor_tjse._http = fake
for mx in (0, -5, 1, 999):
    r = asyncio.run(s.sincronizar(3, mx))
    print(f"   max_requisicoes={mx:>4} -> {r.split(chr(10))[0][:80]}")
