# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.4.0,<2", "httpx>=0.27", "truststore>=0.9"]
# (mcp<2 de propósito: o 2.x renomeou FastMCP → MCPServer e o registro das tools falha em silêncio)
# ///
"""
Servidor MCP — Jurisprudência do TJSE (Tribunal de Justiça de Sergipe) — v0.1.0
===============================================================================
Pesquisa de acórdãos do TJSE para uso em peça: índice local, inteiro teor com recibo, conferência
literal de citação, órgão e data lidos do FECHO. Funciona SOZINHO (só este servidor + um cliente MCP)
e também como parte de um conjunto maior de ferramentas — ver "MODO HÍBRIDO" abaixo.

O QUE ESTE SERVIDOR NÃO USA, E POR QUÊ
  O formulário oficial de pesquisa (www.tjse.jus.br/Dgorg/paginas/jurisprudencia/
  consultarJurisprudencia.tjse, JSF + PrimeFaces 8) exige Cloudflare Turnstile no POST
  (campo cf-turnstile-response; medido em 21/09/2026). Desafio anti-robô NÃO se contorna:
  este servidor não toca nesse formulário, e não deve tocar. A consulta processual antiga
  (tjnet/consultas/internet/respnumprocesso.wsp) também pede "Código de Segurança".

O QUE USA (rotas oficiais, públicas, sem desafio, Apache direto — medidas em 21/09/2026)
  1. Boletim Jurídico de Sergipe — https://diario.tjse.jus.br/revista/internet/ (WebIntegrator,
     ISO-8859-1). Ementário mensal oficial: ementa integral (EM CAIXA ALTA), nº do processo,
     nº do acórdão, classe e nº do recurso, relator, por seção (Pleno, Seção Especializada
     Cível, 1ª e 2ª Câmaras Cíveis, Câmara Criminal). A edição N sai no fim do mês e traz os
     acórdãos do mês anterior. Vira ÍNDICE LOCAL (SQLite FTS5): a busca não gasta rede.
  2. Inteiro teor — https://www.tjse.jus.br/tjnet/jurisprudencia/relatorio.wsp
     ?tmp.numprocesso=…&tmp.numacordao=… (o link que o próprio Boletim publica): ementa em
     caixa normal, fecho ("ACORDAM…"), relatório e voto. Vira RECIBO local.

LIMITES, DITOS COM TODAS AS LETRAS
  • Só acórdão de 2º grau publicado no Boletim. Turmas Recursais, Turma de Uniformização e
    decisões monocráticas NÃO estão aqui (só no formulário com Turnstile → pesquisa manual
    do advogado, ou a base de jurisprudência que ele assinar).
  • A busca enxerga só as edições já sincronizadas. "Nada encontrado" = nada NO ÍNDICE LOCAL,
    no período coberto — a saída sempre diz qual é. Nunca é "não localizado no TJSE".
  • O TJSE numera por processo (12 dígitos) e acórdão (9 dígitos); o inteiro teor não traz
    número CNJ.
  • A ementa do Boletim é caixa alta: citação literal se confere no inteiro teor, nunca nela.

MODO HÍBRIDO
  • Sem mais nada instalado: sincronize, busque, leia o inteiro teor, confira a citação. O que o
    índice não cobre, a saída manda pesquisar à mão no portal oficial e explica como trazer o
    achado de volta para conferência (processo + acórdão, ou a URL do inteiro teor).
  • Com outras fontes (agregador de jurisprudência, outro MCP, assinatura): declare-as em
    TJSE_COMPLEMENTOS="Nome A; Nome B" e as saídas passam a apontar para elas nos pontos cegos.
    Qualquer julgado do TJSE achado FORA daqui se confere AQUI, pelo par processo+acórdão.
  Variáveis: TJSE_DIR_DADOS (onde ficam índice, recibos e disjuntor; padrão: pasta do script),
  TJSE_COMPLEMENTOS, TJSE_USER_AGENT.

Licença MIT. Não é produto oficial do TJSE. Saída de IA é rascunho: quem assina confere.
"""
from __future__ import annotations

import asyncio
import contextlib
import datetime as _dt
import gzip
import hashlib
import html as _html
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
from typing import Any

try:
    import fcntl
except Exception:
    fcntl = None

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

try:
    import httpx
except Exception:
    httpx = None  # type: ignore

VERSAO = "0.7.0"
RAIZ = os.path.dirname(os.path.abspath(__file__))
DIR_DADOS = os.environ.get("TJSE_DIR_DADOS", RAIZ)
ARQ_ESTADO = os.path.join(DIR_DADOS, ".disjuntor_estado_tjse.json")
DIR_BASE = os.path.join(DIR_DADOS, "base")
DIR_RECIBOS = os.environ.get("TJSE_DIR_RECIBOS") or os.path.join(DIR_DADOS, "recibos")
ARQ_DB = os.path.join(DIR_BASE, "boletim.db")
DIR_SECOES = os.path.join(DIR_BASE, "secoes")  # HTML bruto de cada seção: reparse sem rede

BOLETIM = "https://diario.tjse.jus.br/revista/internet"
URL_TEOR = "https://www.tjse.jus.br/tjnet/jurisprudencia/relatorio.wsp"
URL_FORM_TURNSTILE = "https://www.tjse.jus.br/portal/consultas/jurisprudencia/judicial"

# User-Agent HONESTO por padrão: o cliente se identifica como o que é. Quem precisar de outro (ex.: rede corporativa
# que só deixa passar navegador) define TJSE_USER_AGENT — decisão e responsabilidade de quem define.
USER_AGENT_PADRAO = f"tjse-jurisprudencia-mcp/{{versao}} (pesquisa juridica; cliente MCP; ritmo limitado)"
HEADERS = {
    "User-Agent": os.environ.get("TJSE_USER_AGENT") or USER_AGENT_PADRAO,
    "Accept-Language": "pt-BR,pt;q=0.9",
}
COMPLEMENTOS = [c.strip() for c in os.environ.get("TJSE_COMPLEMENTOS", "").split(";") if c.strip()]


def onde_mais_procurar() -> str:
    """O parágrafo híbrido: o que fazer com o que este índice não cobre, com ou sem outras ferramentas."""
    ponte = ("Julgado do TJSE achado fora daqui se confere AQUI: `obter_inteiro_teor_tjse(numero_acordao, numero_processo)` "
             "— ou cole a URL do inteiro teor em `numero_acordao` — e depois `verificar_citacao_tjse`.")
    if COMPLEMENTOS:
        return (f"Para o que falta, consulte também: {', '.join(COMPLEMENTOS)} (declarado em TJSE_COMPLEMENTOS). " + ponte)
    return (f"Para o que falta: pesquisa manual no portal oficial ({URL_FORM_TURNSTILE}), que exige verificação humana — este "
            "servidor não a usa nem contorna — ou qualquer base de jurisprudência que você assine. " + ponte)

# Ritmo. Portal pequeno (Apache 2.4.6), seção de câmara cível passa de 2 MB: devagar.
ESPACAMENTO_S = 6.0
JANELA_S, JANELA_MAX = 600, 20
DIA_MAX = 150
MAX_REQ_POR_SINCRONIZACAO = 14
PAUSA_BLOQUEIO_S = 6 * 3600
PAUSA_DESAFIO_S = 24 * 3600
PAUSA_ERRO_S = 30 * 60
PAUSA_ILEGIVEL_S = 3600

ORGAOS_FECHO = ["Tribunal Pleno", "Seção Especializada Cível", "1ª Câmara Cível", "2ª Câmara Cível",
                "Câmara Criminal", "Turma de Uniformização", "1ª Turma Recursal", "2ª Turma Recursal",
                "Turma Recursal", "Conselho da Magistratura"]
SECOES_SEM_ACORDAO = {"abreviaturas", "composicao do tribunal"}
# O fecho escreve o ordinal por extenso tanto quanto em algarismo ("Grupo 5 da Primeira Câmara Cível" x "nesta 1ª
# Câmara Cível") — achado no 1º uso real de pesquisa, 21/09/2026: sem isso o órgão caía no cadastro e a data de
# julgamento, que é lida na janela do fecho, saía vazia.
_ORDINAL_EXTENSO = {"primeira": "1a", "segunda": "2a", "terceira": "3a", "quarta": "4a", "quinta": "5a",
                    "sexta": "6a", "setima": "7a", "oitava": "8a", "nona": "9a", "decima": "10a",
                    "primeiro": "1a", "segundo": "2a", "terceiro": "3a"}
_RE_ORDINAL_EXTENSO = re.compile(r"\b(%s)\s+(?=camara|turma|secao|grupo)" % "|".join(_ORDINAL_EXTENSO))
MESES = {m: i + 1 for i, m in enumerate(
    ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro",
     "outubro", "novembro", "dezembro"])}
# Só marcas inequívocas, e só ANTES do miolo: a ementa do Boletim começa no char ~770 e pode conter a palavra
# "captcha" (ementa criminal/consumidor) — red team 21/09/2026, achado 7.
MARCAS_DESAFIO = ("cf-turnstile", "challenges.cloudflare.com", "just a moment", "código de segurança",
                  "codigo de seguranca", "g-recaptcha", "h-captcha")


_PAUSA_MEMORIA = 0.0


class PesquisaNaoRealizada(Exception):
    """Falha de rede/ritmo/bloqueio. NUNCA equivale a 'não localizado'."""


# --------------------------------------------------------------------------- #
# Texto                                                                        #
# --------------------------------------------------------------------------- #
_CP1252_BAIXO = {0x13: "–", 0x14: "—", 0x18: "‘", 0x19: "’", 0x1C: "“", 0x1D: "”"}


def limpar_html(frag: str) -> str:
    """HTML → texto. O Boletim emite &#19; &#24; &#25; (byte baixo de U+2013/2018/2019)."""
    frag = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", frag)
    frag = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</td>|</h\d>", "\n", frag)
    frag = re.sub(r"<[^>]+>", "", frag)
    # antes do unescape: html.unescape DESCARTA &#19; (codepoint inválido) e o travessão sumiria
    frag = re.sub(r"&#(\d{1,2});", lambda m: _CP1252_BAIXO.get(int(m.group(1)), m.group(0)), frag)
    t = _html.unescape(frag).replace("\xa0", " ")
    t = re.sub(r"[ \t\r]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_orgao(s: str) -> str:
    """norm() + ordinal por extenso em algarismo, para casar "Primeira Câmara Cível" com "1ª Câmara Cível"."""
    return _RE_ORDINAL_EXTENSO.sub(lambda m: _ORDINAL_EXTENSO[m.group(1)] + " ", norm(s))


def norm(s: str) -> str:
    """Forma de comparação: sem acento, minúscula, aspas/travessões unificados, espaço único."""
    s = unicodedata.normalize("NFKC", s)  # desfaz ligaduras de PDF (ﬁ) e leva º/ª a o/a
    s = sem_acento(s).lower()
    s = re.sub(r"\bn[o.°]\s*(?=\d)", "n ", s)  # "nº 123", "n. 123", "n° 123" → mesma forma
    s = re.sub(r"§\s+", "§", s)
    s = re.sub(r"[“”‘’\"'`´]", "'", s)
    s = re.sub(r"[–—-]", "-", s)
    s = re.sub(r"\s+([.,;:)\]])", r"\1", s)  # "art . 42" e "1.0000 .24" saem assim do portal
    s = re.sub(r"([(\[])\s+", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def data_por_extenso(s: str) -> str | None:
    m = re.search(r"(\d{1,2})\s*(?:º)?\s+de\s+([A-Za-zçÇ]+)\s+de\s+(\d{4})", s)
    if not m:
        return None
    mes = MESES.get(sem_acento(m.group(2)).lower())
    if not mes:
        return None
    try:
        return _dt.date(int(m.group(3)), mes, int(m.group(1))).isoformat()
    except ValueError:
        return None


def br(iso: str | None) -> str:
    if not iso:
        return "?"
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


# --------------------------------------------------------------------------- #
# Disjuntor (estado em disco, flock, compartilhado entre processos)            #
# --------------------------------------------------------------------------- #
@contextlib.contextmanager
def _trava():
    f = None
    try:
        os.makedirs(DIR_DADOS, exist_ok=True)
        f = open(ARQ_ESTADO + ".lock", "a+")
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)
    except OSError:
        f = None  # sem trava: leitura segue; _pedir_vez recusa requisitar (dois processos sem trava perdem registro)
    try:
        yield f is not None
    finally:
        if f is not None:
            with contextlib.suppress(Exception):
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_UN)
                f.close()


def _ler_estado() -> dict[str, Any]:
    if not os.path.exists(ARQ_ESTADO):
        return {"requisicoes": [], "pausa_ate": 0, "motivo": "", "incidentes": []}
    try:
        with open(ARQ_ESTADO, encoding="utf-8") as f:
            e = json.load(f)
        agora = time.time()
        return {  # tipos saneados: JSON válido com tipo errado também é "ilegível"
            "requisicoes": [float(t) for t in e["requisicoes"] if 0 <= agora - float(t) < 86400],  # poda futuro e velho
            "pausa_ate": float(e.get("pausa_ate") or 0), "motivo": str(e.get("motivo") or ""),
            "incidentes": [i for i in (e.get("incidentes") or []) if isinstance(i, dict)][-30:]}
    except Exception:
        # fail-closed: estado ilegível não libera requisição
        return {"requisicoes": [], "pausa_ate": time.time() + PAUSA_ILEGIVEL_S,
                "motivo": "estado do disjuntor ilegível (fail-closed)", "incidentes": []}


def _gravar_estado(e: dict[str, Any]) -> None:
    tmp = f"{ARQ_ESTADO}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False)
    os.replace(tmp, ARQ_ESTADO)


def _pausar(segundos: float, motivo: str) -> None:
    global _PAUSA_MEMORIA
    _PAUSA_MEMORIA = max(_PAUSA_MEMORIA, time.time() + segundos)  # vale mesmo se o disco falhar
    with _trava(), contextlib.suppress(OSError):
        e = _ler_estado()
        e["pausa_ate"] = max(e.get("pausa_ate", 0), time.time() + segundos)  # pausa só cresce
        e["motivo"] = motivo
        e["incidentes"] = (e.get("incidentes", []) + [{"quando": _dt.datetime.now().isoformat(timespec="seconds"),
                                                       "motivo": motivo}])[-30:]
        _gravar_estado(e)


async def _pedir_vez() -> None:
    """Reserva uma requisição ou levanta PesquisaNaoRealizada. Espera só o espaçamento curto (laço limitado)."""
    for _ in range(12):
        with _trava() as travado:
            if not travado and fcntl is not None:
                raise PesquisaNaoRealizada("não consegui a trava do disjuntor (permissão em "
                                           f"`{ARQ_ESTADO}.lock`?); sem trava não há requisição (fail-closed).")
            e = _ler_estado()
            agora = time.time()
            pausa = max(e.get("pausa_ate", 0), _PAUSA_MEMORIA)
            if pausa > agora:
                falta = int((pausa - agora) / 60) + 1
                raise PesquisaNaoRealizada(f"disjuntor em pausa por mais ~{falta} min ({e.get('motivo') or 'pausa em memória'}). "
                                           "Não contornar por navegador, proxy ou outro cliente.")
            reqs = e["requisicoes"]
            if len(reqs) >= DIA_MAX:
                raise PesquisaNaoRealizada(f"teto diário de {DIA_MAX} requisições atingido.")
            if len([t for t in reqs if agora - t < JANELA_S]) >= JANELA_MAX:
                raise PesquisaNaoRealizada(f"teto de {JANELA_MAX} requisições em {JANELA_S // 60} min atingido; "
                                           "tente de novo em alguns minutos.")
            espera = (max(reqs) + ESPACAMENTO_S - agora) if reqs else 0
            if espera <= 0:
                e["requisicoes"] = reqs + [agora]
                try:
                    _gravar_estado(e)
                except OSError as ex:
                    raise PesquisaNaoRealizada(f"não consegui registrar a requisição no disjuntor ({type(ex).__name__}); "
                                               "sem registro não há requisição (fail-closed).")
                return
        await asyncio.sleep(min(max(espera, 0.05), ESPACAMENTO_S))
    raise PesquisaNaoRealizada("disputa pelo disjuntor com outro processo; tente de novo em instantes.")


async def _http(metodo: str, url: str, *, params: dict | None = None, data: dict | None = None,
                referer: str | None = None) -> str:
    if httpx is None:
        raise PesquisaNaoRealizada("httpx não instalado neste ambiente.")
    await _pedir_vez()
    h = dict(HEADERS)
    h["User-Agent"] = h["User-Agent"].replace("{versao}", VERSAO)
    if referer:
        h["Referer"] = referer
    corpo = None
    if data is not None:  # o portal é ISO-8859-1
        corpo = "&".join(f"{k}={_quote_latin1(v)}" for k, v in data.items())
        h["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        async with httpx.AsyncClient(timeout=90, follow_redirects=False, headers=h) as c:
            r = await c.request(metodo, url, params=params, content=corpo)
    except Exception as ex:
        _pausar(PAUSA_ERRO_S, f"falha de rede: {type(ex).__name__}")
        raise PesquisaNaoRealizada(f"falha de rede ({type(ex).__name__}); pausa de 30 min, sem retentativa.")
    if r.status_code in (429, 403):
        _pausar(PAUSA_BLOQUEIO_S, f"HTTP {r.status_code}")
        raise PesquisaNaoRealizada(f"HTTP {r.status_code} — possível bloqueio; pausa de 6 h, zero retentativa.")
    if r.status_code != 200:
        _pausar(PAUSA_ERRO_S, f"HTTP {r.status_code}")
        raise PesquisaNaoRealizada(f"HTTP {r.status_code}; pausa de 30 min.")
    texto = r.content.decode("iso-8859-1")
    baixo = texto.lower()
    ib = baixo.find("<body")
    janelas = baixo[:1500] + (baixo[ib: ib + 1500] if ib >= 0 else "")
    conteudo_esperado = any(x in baixo for x in ("relatorio.wsp", "<h4>boletim n", "wiformgridnav", "onclick=\"ver('",
                                                 "javascript:abre(", "function submitwigrid"))
    # a marca só vale como desafio se a página NÃO for o que pedimos: ementa de consumidor fala em "código de segurança"
    if any(m in janelas for m in MARCAS_DESAFIO) and not conteudo_esperado:
        _pausar(PAUSA_DESAFIO_S, "desafio anti-robô/CAPTCHA detectado")
        raise PesquisaNaoRealizada("o portal respondeu com desafio anti-robô; pausa de 24 h. Nunca contornar.")
    return texto


def _quote_latin1(v: str) -> str:
    from urllib.parse import quote
    return quote(str(v).encode("iso-8859-1", "replace"), safe="")


# --------------------------------------------------------------------------- #
# Parsers (puros — testados offline contra fixtures reais)                     #
# --------------------------------------------------------------------------- #
def parse_edicoes(h: str) -> list[dict[str, Any]]:
    out = []
    for m in re.finditer(r"ver\('(\d+)'\);\"><b>(\d+)</b><br><i>\(([^)]+)\)</i>", h):
        out.append({"edicao": int(m.group(1)), "rotulo": m.group(2), "data": data_por_extenso(_html.unescape(m.group(3)))})
    return out


def parse_menu(h: str) -> list[dict[str, Any]]:
    out, vistos = [], set()
    for m in re.finditer(r'Page\("((?:[^"\\]|\\.)*?)","[^"]*","javascript:abre\(\'(\d+)\',\'(\d+)\'\)', h):
        nome = limpar_html(re.sub(r"<!--.*?-->", "", m.group(1)))
        cod = int(m.group(2))
        if cod in vistos or norm(nome) in SECOES_SEM_ACORDAO:
            continue
        vistos.add(cod)
        out.append({"codigo": cod, "nome": nome})
    return out


PARSER_VERSAO = 10  # mudou o parser → reindexa do HTML bruto em disco, sem rede
_RE_LINK_TEOR = re.compile(r"relatorio\.wsp\?(?:tmp\.numprocesso=(\d+)&(?:amp;)?tmp\.numacordao=(\d+)"
                           r"|tmp\.numacordao=(\d+)&(?:amp;)?tmp\.numprocesso=(\d+))")
# tolerante a grafia do próprio Boletim ("RELATOR ORIGNÁRIO"): "RELAT…" + até 4 palavras + ":"
_RE_ROT_RELATOR = re.compile(r"(?i)^(relat\w*(?:\(a\))?(?:\s+[\wÀ-ÿ()/]+){0,4}?)\s*:\s*(.*)$")
_RE_CARGO_VAGO = re.compile(r"(?i)vaga\s+de\s+desembargador|cargo\s+vago|^des(?:a|\(a\))?\.?\s*$")


def parse_secao(h: str) -> list[dict[str, Any]]:
    """Itens de uma seção do Boletim, por CÉLULA <td> e sobre texto limpo — o HTML é irregular (relator em <div>
    próprio, <font> aninhado, ementa partida em vários <font>/<i>; medido em 21/09/2026). O portal repete o
    conteúdo dentro de um comentário HTML: deduplica-se pelo nº do acórdão."""
    h = h.replace("<!--", "").replace("-->", "")
    classe, itens, vistos = "", [], set()
    for td in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", h):
        lk = _RE_LINK_TEOR.search(td)
        if not lk:
            if "font-size: 10pt" in td and limpar_html(td):
                classe = re.sub(r"\s+", " ", limpar_html(td))
            continue
        proc, acord = (lk.group(1), lk.group(2)) if lk.group(1) else (lk.group(4), lk.group(3))
        if acord in vistos:
            continue
        vistos.add(acord)
        # a ementa termina no ÚLTIMO "PROCESSO:" seguido do link da consulta (a palavra pode ocorrer na ementa)
        cortes = list(re.finditer(r"(?is)PROCESSO:\s*<a\b", td))
        corte = cortes[-1].start() if cortes else lk.start()
        ementa = re.sub(r"\s+", " ", limpar_html(td[:corte])).strip()
        ementa = re.sub(r"(?i)^ementa\s*:\s*", "", ementa)
        cauda_txt = re.sub(r"(?i)(?<=\S)(?=RELATOR(?:\(A\)|A)?\s+(?:ORIG|DESIGN|PARA\s+O|SUBSTIT|CONVOC))", "\n",
                           limpar_html(td[lk.end():]))  # "AC Nº 10491/2026RELATORA ORIGINÁRIA: …" vem colado
        cauda = [l.strip() for l in cauda_txt.split("\n") if l.strip()]
        recurso, rotulo, relator = "", "", ""
        for k, l in enumerate(cauda):
            m = _RE_ROT_RELATOR.match(l)
            if m:
                pares, atual = [], [m.group(1).upper(), [m.group(2)]]
                for l2 in cauda[k + 1:]:
                    m2 = _RE_ROT_RELATOR.match(l2)
                    if m2:
                        pares.append(atual)
                        atual = [m2.group(1).upper(), [m2.group(2)]]
                    else:
                        atual[1].append(l2)
                pares.append(atual)
                pares = [(r, re.sub(r"\s+", " ", " ".join(n)).strip()) for r, n in pares]
                # quem redige o acórdão é o citável; o originário, quando há os dois, ficou vencido
                esc = next((x for x in pares if re.search(r"PARA O AC|DESIGNAD", x[0])), pares[0])
                if _RE_CARGO_VAGO.search(esc[1]) and len(pares) > 1:
                    # "VAGA DE DESEMBARGADOR (G-21)" é marcador administrativo: quem julgou é o substituto/convocado
                    esc = next((x for x in pares if x != esc and not _RE_CARGO_VAGO.search(x[1])), esc)
                rotulo, relator = esc
                if _RE_CARGO_VAGO.search(relator):
                    rotulo += " (marcador administrativo do Boletim — o relator real está no cabeçalho do inteiro teor)"
                outros = [f"{r}: {n}" for r, n in pares if (r, n) != esc]
                if outros:
                    rotulo += " (há também " + "; ".join(outros) + ")"
                break
            if not recurso and re.search(r"N[ºo°]\s*\d", l):
                recurso = l
        itens.append({"acordao": acord, "processo": proc, "classe": classe, "recurso": recurso,
                      "relator": re.sub(r"\s+", " ", relator), "relator_rotulo": rotulo, "ementa": ementa})
    return itens


# --------------------------------------------------------------------------- #
# Ementa estruturada (Res. CNJ): I. caso em exame · II. questão em discussão ·  #
# III. razões de decidir · IV. dispositivo e tese + tese/legislação/jurisp.     #
# Medido em 8.974 ementas (21/09/2026): ~2/3 seguem o padrão. O numeral romano  #
# NÃO é confiável (há "II. RAZÕES DE DECIDIR" e "III. DISPOSITIVO"), o separador#
# varia (. – -) e há plural: casa-se pelo NOME da seção, na ordem do texto.     #
# --------------------------------------------------------------------------- #
CAMPOS_EMENTA = ("cabecalho", "caso", "questao", "razoes", "dispositivo", "tese", "legislacao", "juris_citada")
_SECOES_EMENTA = [
    ("caso", r"caso em exame"),
    ("questao", r"quest(?:[aã]o|[õo]es) em discuss[aã]o"),
    ("razoes", r"raz[oõ]es de decidir"),
    ("dispositivo", r"dispositivo(?:\s+e\s+tese)?"),
]
# O Boletim cola o conteúdo no rótulo de três formas: "CASO EM EXAME:RECURSO", "CASO EM EXAME1. AGRAVO" e
# "CASO EM EXAMEAGRAVO INTERNO" (sem separador algum). Então o separador é pontuação, espaço, dígito ou letra
# maiúscula — na prática, opcional. Isso só é seguro porque os rótulos são expressões longas e distintivas; o
# "dispositivo", que é palavra comum de ementa, exige numeral romano ou "e tese" (ver campos_da_ementa).
_RE_SECAO = re.compile(r"(?i)(?:^|[\s.;:])(?P<num>[ivx]{1,4}\s*[.\-–—)]?\s*)?(?P<rot>" + "|".join(p for _, p in _SECOES_EMENTA)
                       + r")(?:\s*[.:\-–—]\s*|\s+|(?=[\dA-ZÀ-Ý]))")
_SUBCAMPOS = [
    ("tese", r"teses?\s+de\s+julgamento"),
    ("legislacao", r"(?:dispositivos?|legisla[çc][aã]o)\s+relevantes?\s+citad[oa]s?"),
    ("juris_citada", r"jurisprud[eê]ncia\s+relevante\s+citada"),
]
_RE_SUBCAMPO = re.compile(r"(?i)\b(" + "|".join(p for _, p in _SUBCAMPOS) + r")(?:\s*[.:\-–—]\s*|\s+)")


def campos_da_ementa(ementa: str) -> dict[str, str]:
    """Divide a ementa estruturada. Sem estrutura, tudo vai para `cabecalho` — que é o resumo em caixa alta, o
    trecho mais denso de qualquer ementa. Assim a busca por campo nunca perde o acórdão não estruturado: ela
    só deixa de poder distingui-lo."""
    out = {k: "" for k in CAMPOS_EMENTA}
    e = ementa or ""
    marcas, com_num = [], False
    for m in _RE_SECAO.finditer(e):
        rot = next(k for k, p in _SECOES_EMENTA if re.fullmatch(p, m.group("rot"), re.I))
        # "dispositivo" sozinho é palavra comum de ementa ("dispositivo legal", "o dispositivo da sentença"): só vale
        # como seção com o numeral romano antes ou "e tese" depois. Os outros três rótulos são distintivos por si.
        if rot == "dispositivo" and not m.group("num") and not re.search(r"(?i)e\s+tese", m.group("rot")):
            continue
        marcas.append((rot, m.start("rot"), m.end(), bool(m.group("num"))))
        com_num = com_num or bool(m.group("num"))
    # "a questão em discussão nos autos" no meio de uma frase também casa. Quando ALGUMA marca veio com numeral
    # romano, só as com numeral valem: são os títulos de seção de verdade.
    if com_num:
        marcas = [x for x in marcas if x[3]]
    marcas = [x for i, x in enumerate(marcas) if i == 0 or x[0] != marcas[i - 1][0]]
    out["cabecalho"] = (e[: marcas[0][1]] if marcas else e).strip(" .;:-–—")
    for i, (rot, _, fim, _n) in enumerate(marcas):
        trecho = e[fim: marcas[i + 1][1] if i + 1 < len(marcas) else len(e)].strip()
        if len(trecho) > len(out[rot]):  # rótulo repetido: fica a ocorrência com mais conteúdo
            out[rot] = trecho
    base = out["dispositivo"] or out["cabecalho"]
    subs = [(next(k for k, p in _SUBCAMPOS if re.fullmatch(p, m.group(1), re.I)), m.start(1), m.end())
            for m in _RE_SUBCAMPO.finditer(base)]
    for i, (rot, ini, fim) in enumerate(subs):
        out[rot] = base[fim: subs[i + 1][1] if i + 1 < len(subs) else len(base)].strip()
    if subs:
        cortado = base[: subs[0][1]].strip()
        if out["dispositivo"]:
            out["dispositivo"] = cortado
    return out


_RE_PROC_TJSE = re.compile(r"\b((?:19|20)\d{10})\b")


def citacoes_da_ementa(campos: dict[str, str], ementa: str) -> list[tuple[str, str]]:
    """[(tipo, ref)] — o grafo vem do campo "Jurisprudência relevante citada" da ementa estruturada, que o próprio
    tribunal preenche, mais as âncoras (súmula/tema/IRDR/IAC) de toda a ementa. Não precisa do inteiro teor."""
    out = set()
    jc = campos.get("juris_citada") or ""
    # processo do próprio TJSE citado: só dentro do campo de jurisprudência, e só quando "TJSE" aparece antes — no
    # resto da ementa, 12 dígitos é quase sempre o número do contrato ou do benefício.
    for m in re.finditer(r"(?i)tjse[^;]{0,160}?" + _RE_PROC_TJSE.pattern, jc):
        out.add(("tjse", m.group(1)))
    for a in ancoras(ementa, 20):
        out.add(("qualificado", a))
    return sorted(out)


def anomalias_secao(itens: list[dict[str, Any]]) -> list[str]:
    """Sinais de que o layout mudou ou a resposta veio cortada. Seção com anomalia grave NÃO é marcada como baixada."""
    if not itens:
        return ["nenhum acórdão reconhecido"]
    n, out = len(itens), []
    for campo, piso in (("relator", 6), ("ementa", 60), ("recurso", 4), ("classe", 3)):
        ruins = sum(1 for i in itens if len(i[campo]) < piso)
        if ruins:
            out.append(f"{ruins}/{n} com `{campo}` vazio ou curto")
    return out


def parse_teor(h: str) -> dict[str, Any]:
    t = limpar_html(h)
    t = re.sub(r"function carregarTurma\(\)[\s\S]*?\n(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ ]{4,}\n)", "", t)  # resíduo de JS inline
    def campo(rot: str) -> str:
        m = re.search(rot + r":\s*\n?\s*([^\n]+)", t)
        return m.group(1).strip() if m else ""
    d: dict[str, Any] = {"acordao": campo("ACÓRDÃO"), "recurso": campo("RECURSO"), "processo": campo("PROCESSO"),
                         "relator": campo("RELATOR"), "texto": t}
    m_em = re.search(r"\bE\s?M\s?E\s?N\s?T\s?A\b", t)
    d["inicio_conteudo"] = m_em.start() if m_em else 0
    d["partes_cortadas"] = bool(m_em)
    # Fecho: só "acordam" seguido de "Estado de Sergipe" (o voto transcreve fechos de outros tribunais). O órgão é o
    # que aparece PRIMEIRO no texto da janela — não o primeiro da lista (red team 21/09/2026, achado 2).
    fechos = []
    for m in re.finditer(r"(?i)\bacordam\b", t):
        jan = norm_orgao(t[m.start(): m.start() + 450])
        k = jan.find("estado de sergipe")
        if k < 0:
            continue
        jan = jan[: k + 140]
        achados = sorted((jan.find(norm_orgao(o)), -len(o), o) for o in ORGAOS_FECHO if norm_orgao(o) in jan)
        if achados:
            fechos.append((achados[0][2], m.start()))
    orgs = {o for o, _ in fechos}
    d["orgao_fecho"] = fechos[0][0] if len(orgs) == 1 else None
    d["fecho_ambiguo"] = len(orgs) > 1
    d["data_julgamento"], d["datas_fecho"] = None, []
    if fechos:
        jan = t[fechos[0][1]: fechos[0][1] + 900]
        jan = re.split(r"\n\s*RELAT[ÓO]RIO\b", jan)[0]
        datas = [x for x in (data_por_extenso(g) for g in re.findall(r"Aracaju(?:\s*/\s*SE)?\s*,\s*([^\n]{8,40})", jan)) if x]
        d["datas_fecho"] = sorted(set(datas))
        if datas:
            d["data_julgamento"] = datas[-1]
    return d


# --------------------------------------------------------------------------- #
# Índice local                                                                 #
# --------------------------------------------------------------------------- #
def _db() -> sqlite3.Connection:
    os.makedirs(DIR_BASE, mode=0o700, exist_ok=True)
    con = sqlite3.connect(ARQ_DB)
    con.row_factory = sqlite3.Row
    con.executescript("""
    CREATE TABLE IF NOT EXISTS edicoes(edicao INTEGER PRIMARY KEY, rotulo TEXT, data TEXT);
    CREATE TABLE IF NOT EXISTS secoes(edicao INTEGER, codigo INTEGER, nome TEXT, itens INTEGER, baixada_em TEXT,
                                      PRIMARY KEY(edicao, codigo));
    CREATE TABLE IF NOT EXISTS acordaos(acordao TEXT PRIMARY KEY, processo TEXT, classe TEXT, recurso TEXT,
                                        relator TEXT, relator_rotulo TEXT, orgao TEXT, edicao INTEGER, ementa TEXT);
    CREATE TABLE IF NOT EXISTS meta(chave TEXT PRIMARY KEY, valor TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS fts_vocab USING fts5vocab(fts, 'row');
    CREATE TABLE IF NOT EXISTS campos(acordao TEXT PRIMARY KEY, cabecalho TEXT, caso TEXT, questao TEXT, razoes TEXT,
                                      dispositivo TEXT, tese TEXT, legislacao TEXT, juris_citada TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS fts_campos USING fts5(acordao UNINDEXED, cabecalho, caso, questao, razoes,
                                      dispositivo, tese, tokenize="unicode61 remove_diacritics 2");
    -- grafo: quem o acórdão CITA. `tjse` = processo de 12 dígitos do próprio tribunal (a maioria fora do índice,
    -- porque é julgado anterior à janela sincronizada); `qualificado` = súmula, tema, IRDR, IAC, SV.
    CREATE TABLE IF NOT EXISTS citacoes(origem TEXT, tipo TEXT, ref TEXT, PRIMARY KEY(origem, tipo, ref));
    CREATE INDEX IF NOT EXISTS ix_cit_ref ON citacoes(tipo, ref);
    CREATE TABLE IF NOT EXISTS republicacoes(acordao TEXT, edicao INTEGER, ementa TEXT, PRIMARY KEY(acordao, edicao));
    CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(acordao UNINDEXED, ementa, classe, relator,
                                                      tokenize="unicode61 remove_diacritics 2");
    """)
    try:
        _reindexar_se_parser_mudou(con)
    except BaseException:
        con.rollback()
        con.close()  # conexão aberta com transação pendente = "database is locked" em tudo que vier depois
        raise
    return con


def _arq_secao(edicao: int, codigo: int, pagina: int = 1) -> str:
    suf = "" if pagina == 1 else f".p{int(pagina)}"
    return os.path.join(DIR_SECOES, f"{int(edicao)}-{int(codigo)}{suf}.html.gz")


_RE_PROXIMA = re.compile(r"submitWIGrid\('grid\.lista_conteudoDiario',\s*(\d+)\)\"\s*class='nav_go'")


def proxima_posicao(h: str) -> int | None:
    """O WebIntegrator pagina a seção em 1.000 linhas (≈995 acórdãos + cabeçalhos de classe). Medido em 21/09/2026:
    quatro seções diferentes com 995 itens EXATOS denunciaram o teto. None = última página."""
    m = _RE_PROXIMA.search(h[-6000:])
    return int(m.group(1)) if m else None


def campos_grid(h: str) -> dict[str, str]:
    f = re.search(r'(?is)<form id="wiFormGridNav".*?</form>', h[-6000:])
    return {m.group(1): _html.unescape(m.group(2)) for m in
            re.finditer(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', f.group(0))} if f else {}


def ler_bruto(edicao: int, codigo: int, pagina: int = 1) -> str | None:
    try:
        with gzip.open(_arq_secao(edicao, codigo, pagina), "rb") as f:
            return f.read().decode("utf-8")
    except Exception:
        return None


def paginas_em_disco(edicao: int, codigo: int) -> tuple[list[str], bool]:
    """(páginas guardadas, completa?) — completa = a última página guardada não tem 'Próximo'."""
    pags = []
    while (h := ler_bruto(edicao, codigo, len(pags) + 1)) is not None:
        pags.append(h)
        if proxima_posicao(h) is None:
            return pags, True
    return pags, False


def guardar_bruto(edicao: int, codigo: int, h: str, pagina: int = 1) -> None:
    os.makedirs(DIR_SECOES, mode=0o700, exist_ok=True)
    fd = os.open(_arq_secao(edicao, codigo, pagina), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as bruto, gzip.GzipFile(fileobj=bruto, mode="wb") as f:
        f.write(h.encode("utf-8"))


def _apagar_secao(con: sqlite3.Connection, edicao: int, nome: str) -> None:
    alvo = "SELECT acordao FROM acordaos WHERE edicao=? AND orgao=?"
    for t, col in (("fts", "acordao"), ("campos", "acordao"), ("fts_campos", "acordao"), ("citacoes", "origem")):
        con.execute(f"DELETE FROM {t} WHERE {col} IN ({alvo})", (edicao, nome))
    con.execute("DELETE FROM acordaos WHERE edicao=? AND orgao=?", (edicao, nome))


def _reindexar_se_parser_mudou(con: sqlite3.Connection) -> None:
    """Parser corrigido → o índice antigo é refeito do HTML bruto em disco (0 rede). Seção sem bruto guardado
    (baixada antes da v0.2) sai do índice e volta na próxima sincronização — melhor buraco declarado que dado torto."""
    v = con.execute("SELECT valor FROM meta WHERE chave='parser_versao'").fetchone()
    if v and int(v[0]) == PARSER_VERSAO:
        return
    for r in con.execute("SELECT edicao, codigo, nome FROM secoes").fetchall():
        _apagar_secao(con, r["edicao"], r["nome"])
        pags, completa = paginas_em_disco(r["edicao"], r["codigo"])
        itens = parse_secao("\n".join(pags))  # juntas: a classe aberta na página 1 continua na 2
        if pags and completa:
            indexar_secao(con, r["edicao"], r["codigo"], r["nome"], itens, _commit=False)
        if not pags or not completa:  # sem bruto, ou faltam páginas: volta para a fila da sincronização
            con.execute("DELETE FROM secoes WHERE edicao=? AND codigo=?", (r["edicao"], r["codigo"]))
    con.execute("INSERT OR REPLACE INTO meta VALUES('parser_versao', ?)", (str(PARSER_VERSAO),))
    con.commit()


def indexar_secao(con: sqlite3.Connection, edicao: int, codigo: int, nome: str, itens: list[dict],
                  _commit: bool = True) -> int:
    novos = 0
    for it in itens:
        ja = con.execute("SELECT edicao FROM acordaos WHERE acordao=?", (it["acordao"],)).fetchone()
        if ja and ja["edicao"] != edicao:
            # mesmo acórdão em outra edição: pode ser RETIFICAÇÃO. Fica a primeira no índice, a outra é guardada e avisada.
            con.execute("INSERT OR REPLACE INTO republicacoes VALUES(?,?,?)", (it["acordao"], edicao, it["ementa"]))
            continue
        if ja:
            for t in ("fts", "acordaos", "campos", "fts_campos", "citacoes"):
                con.execute(f"DELETE FROM {t} WHERE {'origem' if t == 'citacoes' else 'acordao'}=?", (it["acordao"],))
        else:
            novos += 1
        con.execute("INSERT INTO acordaos VALUES(?,?,?,?,?,?,?,?,?)",
                    (it["acordao"], it["processo"], it["classe"], it["recurso"], it["relator"],
                     it["relator_rotulo"], nome, edicao, it["ementa"]))
        con.execute("INSERT INTO fts(acordao, ementa, classe, relator) VALUES(?,?,?,?)",
                    (it["acordao"], it["ementa"], it["classe"], it["relator"]))
        cps = campos_da_ementa(it["ementa"])
        con.execute("INSERT OR REPLACE INTO campos VALUES(?,?,?,?,?,?,?,?,?)",
                    tuple([it["acordao"]] + [cps[k] for k in CAMPOS_EMENTA]))
        con.execute("INSERT INTO fts_campos(acordao, cabecalho, caso, questao, razoes, dispositivo, tese) "
                    "VALUES(?,?,?,?,?,?,?)", (it["acordao"], cps["cabecalho"], cps["caso"], cps["questao"],
                                              cps["razoes"], cps["dispositivo"], cps["tese"]))
        for tipo, ref in citacoes_da_ementa(cps, it["ementa"]):
            con.execute("INSERT OR IGNORE INTO citacoes VALUES(?,?,?)", (it["acordao"], tipo, ref))
    con.execute("INSERT OR REPLACE INTO secoes VALUES(?,?,?,?,?)",
                (edicao, codigo, nome, len(itens), _dt.datetime.now().isoformat(timespec="seconds")))
    if _commit:
        con.commit()
    return novos


# palavras curtas ("pais", "leis", "bens") e invariáveis/funcionais não ganham variante: "pais→pal", "onus→onu", "nao→noes"
_SEM_VARIANTE = {"pais", "leis", "seis", "dois", "reis", "jamais", "demais", "quais", "tais", "onus", "lapis", "tres", "caos", "simples", "pires", "atras", "alias", "apenas", "antes", "depois", "menos",
                 "mais", "entao", "senao", "orgao", "sotao", "virus", "bonus", "campus", "status", "habeas", "corpus", "versus",
                 "reus", "deus", "juros", "custas", "ferias", "nupcias", "viveres", "anais", "arredores", "pesames", "oculos"}


def variantes_numero(w: str) -> list[str]:
    """Singular/plural de uma palavra já sem acento e minúscula. FTS5 não tem stemmer de português e prefixo não
    resolve plural irregular (moral→morais, acao→acoes). Variante inexistente é inofensiva: só não casa."""
    v = [w]
    if len(w) < 4 or not w.isalpha() or w in _SEM_VARIANTE:
        return v
    for suf, trocas in (("oes", ["ao"]), ("aes", ["ao"]), ("aos", ["ao"]), ("ais", ["al"]), ("eis", ["el"]), ("ois", ["ol"]),
                        ("ns", ["m"]), ("res", ["r"]), ("zes", ["z"]), ("ses", ["s"]), ("ao", ["oes", "aos", "aes"]),
                        ("al", ["ais"]), ("el", ["eis"]), ("ol", ["ois"]), ("il", ["is"]), ("m", ["ns"]), ("r", ["res"]),
                        ("z", ["zes"])):
        if w.endswith(suf):
            v += [w[: -len(suf)] + t for t in trocas]
            break
    else:
        v.append(w[:-1] if w.endswith("s") else w + "s")
    return v[:4]


def _frase_fts(termo: str, exato: bool = False) -> str:
    termo = termo.strip()
    radical = re.search(r"[^\W\d_]{3,}[$*]$", termo) is not None  # "R$" não é radical
    palavras = re.sub(r"[^\w\s]", " ", sem_acento(termo).lower(), flags=re.U).split()
    if not palavras:
        return ""
    if radical:
        return '"' + " ".join(palavras) + '"*'
    if exato:
        return '"' + " ".join(palavras) + '"'
    combos = [[]]
    for w in palavras:
        vs = variantes_numero(w)
        if len(combos) * len(vs) > 36:
            vs = vs[:1]
        combos = [c + [x] for c in combos for x in vs]
    fr = ['"' + " ".join(c) + '"' for c in combos]
    return fr[0] if len(fr) == 1 else "(" + " OR ".join(fr) + ")"


# Palavras que não distinguem um acórdão de outro. Sem removê-las, a pergunta em português vira um E lógico com
# artigo e preposição dentro — e o harness mediu o resultado disso: 0 % de recall nas 6 consultas (21/09/2026).
_VAZIAS = set("""a o as os um uma uns umas de do da dos das em no na nos nas por para pelo pela pelos pelas com sem
sob sobre entre ate apos ante e ou mas que se qual quais quando onde como porque pois ja nao sim ha he ser sao foi
era eram tem tinha teve havia deve devem pode podem ha existe existem qualquer algum alguma cabe cabivel caso casos
direito processual civil acordao decisao recurso apelacao agravo parte partes autos processo juizo tribunal camara
seguinte seguintes mesmo mesma outro outra seu sua seus suas este esta isso aquilo lhe lhes ao aos""".split())


def partes_fts(consulta: str | None, grupos: list[list[str]] | None, exato: bool = False) -> list[tuple[str, str]]:
    """[(rótulo legível, expressão FTS)] — um item por grupo, mais UM item com as palavras soltas da consulta.

    Palavras soltas combinam por OU (o ranking põe no topo quem tem mais delas); "entre aspas" e `grupos` é que
    são obrigatórios. Antes todas as palavras eram obrigatórias, e uma pergunta escrita como se fala não achava
    nada — era a forma mais natural de usar a ferramenta e a única que devolvia zero."""
    partes = []
    for g in grupos or []:
        fr = [f for f in (_frase_fts(x, exato) for x in g) if f]
        if not fr:
            raise ValueError(f"o grupo {g!r} não tem nenhum termo pesquisável (só pontuação?) — se ele sumisse em silêncio, "
                             "o E entre grupos deixaria de valer.")
        partes.append(("[" + " | ".join(g) + "]", "(" + " OR ".join(fr) + ")"))
    if consulta:
        fora_de_aspas = re.sub(r'"[^"]*"', " ", consulta)
        if re.search(r"\b(E|OU|NAO|NÃO|ADJ\d*|PROX\d*|AND|OR|NOT|NEAR)\b", fora_de_aspas):
            raise ValueError("operador em caixa alta não é aceito na `consulta` (índice local FTS5): use `grupos` "
                             "— cada grupo é OU entre sinônimos, grupos se combinam em E.")
        soltas = []
        for m in re.finditer(r'"([^"]+)"|(\S+)', consulta):
            aspas, tok = bool(m.group(1)), (m.group(1) or m.group(2))
            f = _frase_fts(tok, exato)
            if not f:
                continue
            if aspas:
                partes.append((f'"{tok}"', f))  # entre aspas = o usuário quer exatamente isso: obrigatório
            elif norm(tok) not in _VAZIAS and len(re.sub(r"\W", "", norm(tok), flags=re.U)) > 2:
                soltas.append((tok, f))
        if len(soltas) == 1:
            partes.append(soltas[0])
        elif soltas:
            partes.append((" ou ".join(t for t, _ in soltas), "(" + " OR ".join(f for _, f in soltas) + ")"))
        elif not partes:
            raise ValueError("a consulta só tem palavras comuns (artigos, preposições, palavras de praxe do jargão), "
                             "que não distinguem um acórdão de outro — use termos do tema, ou `grupos`.")
    return partes


def montar_fts(consulta: str | None, grupos: list[list[str]] | None, exato: bool = False) -> str:
    """grupos=[[a,b],[c]] → (a OU b) E (c). consulta livre: palavras e "frases" em E. Por padrão cada termo casa
    também no outro número (singular/plural); `exato=True` desliga."""
    return " AND ".join(e for _, e in partes_fts(consulta, grupos, exato))


def _aviso_incompletas(con: sqlite3.Connection) -> str:
    inc = [f"ed. {r['edicao']}" for r in con.execute(
        """SELECT e.edicao FROM edicoes e WHERE e.edicao BETWEEN (SELECT MIN(edicao) FROM secoes) AND (SELECT MAX(edicao) FROM secoes)
           AND (SELECT COUNT(*) FROM secoes s WHERE s.edicao=e.edicao) < 5 ORDER BY 1""")]
    return (f". ⚠ EDIÇÕES INCOMPLETAS no intervalo ({', '.join(inc)}): há seções faltando ou só parcialmente baixadas — "
            "zero resultado vale ainda menos; rode `sincronizar_boletim_tjse`") if inc else ""


# Panorama dos resultados. Ideia do servidor do TJRO (resumo de resultados por página, âncoras de precedente qualificado),
# adaptada: aqui o índice é local, então o resumo cobre TODAS as ementas que casam (até PANORAMA_MAX), não só a página.
# Índice é indício: serve para decidir o que ler e para achar âncoras, nunca como posição sobre a tese.
PANORAMA_MAX = 3000
# "não conhecido" só vale quando o SUJEITO é o recurso/ação ("recurso não conhecido"); "não conhecimento" de um argumento
# isolado, ou "ordem denegada", não são resultado do julgamento (medido: 65 casos, vários falsos na 1ª regra)
_RE_NAO_CONHECIDO = re.compile(r"\b(?:recurso|apelacao|agravo|embargos|acao|revisao criminal|mandado de seguranca|incidente|"
                               r"reclamacao|conflito|apelo)s?(?: \w+){0,4}? (?:nao (?:se )?conhecid\w+|nao conhecimento)|"
                               r"\bnao conhec(?:o|eram|eu|er|imento) d[oa]s? (?:recurso|apelacao|agravo|embargos|apelo)")
_RE_PARCIAL = re.compile(r"\bparcialmente provid\w+|\bprovid\w+ em parte|\bparcial provimento|\bdar? (?:-se )?parcial provimento|"
                         r"\bdeu-se parcial provimento|\bdera(?:m)? parcial provimento")
_RE_DESPROV = re.compile(r"\bdesprovi\w+|\bimprovi\w+|\bnao provid\w+|\bnegar? (?:-se )?provimento|\bnega-se provimento|"
                         r"\bnegou provimento|\bnegado provimento|\bprovimento negado")
_RE_PROV = re.compile(r"(?<!des)(?<!im)(?<!nao )\bprovid[oa]s?\b|\bdar? (?:-se )?provimento|\bdeu-se provimento|\bderam provimento|"
                      r"\bdou provimento")
_RE_ANCORAS = [
    (re.compile(r"s[úu]mula\s+vinculante\s+n?[º°.]*\s*(\d{1,4})", re.I), "Súmula Vinculante %s"),
    # o número da súmula colide entre tribunais (Súmula 7 do STJ ≠ do TJSE): quando o texto diz de quem é, o rótulo diz
    (re.compile(r"s[úu]mula\s+n?[º°.]*\s*(\d{1,4})(?:\s*/\s*|\s+d[oa]\s+)?(STJ|STF|TJSE|TST)?", re.I), "Súmula %s"),
    (re.compile(r"tema\s+(?:repetitivo\s+|de\s+repercuss[ãa]o\s+geral\s+)?n?[º°.]*\s*(\d{1,4}(?:\.\d{3})?)", re.I), "Tema %s"),
    (re.compile(r"\bIRDR\s+n?[º°.]*\s*(\d{1,4})", re.I), "IRDR %s"),
    (re.compile(r"\bIAC\s+n?[º°.]*\s*(\d{1,4})", re.I), "IAC %s"),
]


def resultado_declarado(ementa: str) -> str | None:
    """'desprovido' | 'provido' | 'parcialmente provido' | 'não conhecido' | None (ausente ou ambíguo). Lê a ementa inteira
    e só devolve quando UM lado é inequívoco: ementa que menciona dois (voto vencido, "autor provido, réu desprovido",
    histórico da origem) fica sem rótulo — nunca é forçada para um lado."""
    t = norm(ementa)
    achou = set()
    if _RE_NAO_CONHECIDO.search(t):
        achou.add("não conhecido")
    parcial = _RE_PARCIAL.search(t)
    if parcial:
        achou.add("parcialmente provido")
        t = _RE_PARCIAL.sub(" ", t)
    if _RE_DESPROV.search(t):
        achou.add("desprovido")
        t = _RE_DESPROV.sub(" ", t)
    if _RE_PROV.search(t):
        achou.add("provido")
    return next(iter(achou)) if len(achou) == 1 else None


_RE_TRIB_ANTES = re.compile(r"(?i)\b(STJ|STF|TJSE|TST|TNU)\b[^.;]{0,12}$")


def ancoras(texto: str, max_itens: int = 6) -> list[str]:
    """Precedentes qualificados citados. O tribunal pode vir DEPOIS ("Súmula 297/STJ") ou ANTES ("STJ, Súmula 297"):
    as duas formas têm de virar a MESMA chave, senão o grafo conta a mesma súmula duas vezes."""
    t = str(texto or "")
    achado: dict[str, int] = {}
    for rx, molde in _RE_ANCORAS:
        for m in rx.finditer(t):
            n = m.group(1).replace(".", "")
            if not n or n == "0":
                continue
            nome = molde % n
            trib = m.group(2) if (m.lastindex and m.lastindex >= 2 and m.group(2)) else None
            if not trib:
                antes = _RE_TRIB_ANTES.search(t[max(0, m.start() - 30): m.start()])
                trib = antes.group(1) if antes else None
            if trib and not nome.startswith("Tema") and not nome.startswith("IRDR") and not nome.startswith("IAC"):
                nome += f"/{trib.upper()}"
            if nome.startswith("Súmula ") and f"Súmula Vinculante {n}" in achado:
                continue
            achado.setdefault(nome, m.start())
    # "Súmula 297" e "Súmula 297/STJ" no mesmo texto são a mesma coisa: fica a forma com tribunal
    for k in [x for x in achado if "/" in x]:
        achado.pop(k.split("/")[0], None)
    return [n for n, _ in sorted(achado.items(), key=lambda kv: kv[1])][:max_itens]


_STOP_VOCAB = set("""recurso conhecido provido desprovido acordao decisao agravo apelacao relator camara civel interposto contra
    embargos direito processual civil ementa turma tribunal justica sergipe tese julgamento unanimidade unanime votos voto
    dispositivo relevantes citados jurisprudencia constituicao federal codigo artigo artigos casos exame razoes decidir
    questao discussao apelante apelado agravante agravado recorrente recorrido sentenca juizo primeiro grau parte partes""".split())


def pistas_vocabulario(con: sqlite3.Connection, ementas: list[str], excluir: set[str], max_itens: int = 12) -> list[str]:
    """Palavras bem mais frequentes nas ementas que casam do que no índice inteiro (lift), candidatas a novo grupo de
    sinônimos. Usa fts5vocab: o custo é uma consulta em lote."""
    n = len(ementas)
    if n < 8:
        return []
    df: dict[str, int] = {}
    for e in ementas:
        for w in set(re.findall(r"[a-z]{5,}", norm(e))):
            df[w] = df.get(w, 0) + 1
    piso = max(4, int(n * 0.06))
    cand = [w for w, c in df.items() if c >= piso and w not in _STOP_VOCAB and w not in excluir]
    if not cand:
        return []
    total = con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0] or 1
    geral = {}
    for k in range(0, len(cand), 400):
        lote = cand[k:k + 400]
        for r in con.execute(f"SELECT term, doc FROM fts_vocab WHERE term IN ({','.join('?' * len(lote))})", lote):
            geral[r[0]] = r[1]
    pont = []
    for w in cand:
        lift = (df[w] / n) / (max(geral.get(w, 1), 1) / total)
        if lift >= 2.5:
            pont.append((lift * (df[w] ** 0.5), w, df[w], lift))
    return [f"{w} ({c}, ×{l:.0f})" for _, w, c, l in sorted(pont, reverse=True)[:max_itens]]


def panorama(con: sqlite3.Connection, sql: str, args: list, por_bm25: bool, total: int, excluir: set[str]) -> str:
    ordem = "r.rk" if por_bm25 else "a.edicao DESC"
    linhas = con.execute(f"SELECT a.orgao, a.classe, a.ementa{sql} ORDER BY {ordem} LIMIT {PANORAMA_MAX}", args).fetchall()
    if len(linhas) < 5:
        return ""
    res: dict[str, int] = {}
    orgs: dict[str, int] = {}
    clas: dict[str, int] = {}
    cit: dict[str, int] = {}
    for orgao, classe, em in linhas:
        k = resultado_declarado(em) or "sem resultado identificável"
        res[k] = res.get(k, 0) + 1
        orgs[orgao] = orgs.get(orgao, 0) + 1
        clas[classe] = clas.get(classe, 0) + 1
        for a in set(ancoras(em, 12)):
            cit[a] = cit.get(a, 0) + 1
    top = lambda d, n=6: " · ".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:n])
    ordem_res = ["desprovido", "provido", "parcialmente provido", "não conhecido", "sem resultado identificável"]
    resumo = " · ".join(f"{k} {res[k]}" for k in ordem_res if k in res)
    pistas = pistas_vocabulario(con, [x[2] for x in linhas], excluir)
    ancs = " · ".join(f"{k} ({v})" for k, v in sorted(cit.items(), key=lambda kv: -kv[1])[:8] if v >= 2)
    parcial = f" (as {PANORAMA_MAX} mais relevantes de {total})" if total > PANORAMA_MAX else ""
    out = [f"PANORAMA das {len(linhas)} ementas que casam{parcial} — indício para decidir o que ler, NÃO posição sobre a tese "
           "(recurso provido por outro fundamento também conta como provido):",
           f"  Resultado declarado na ementa: {resumo}",
           f"  Por órgão (seção do Boletim): {top(orgs)}",
           f"  Por classe: {top(clas)}"]
    if ancs:
        out.append(f"  Citados nas ementas: {ancs} — precedentes qualificados: âncora para novo grupo de busca; confirme a "
                   "situação de cada um na fonte própria (súmula/tema/IRDR se confere no BNP do CNJ, e superação na fonte oficial)")
    if pistas:
        out.append("  Vocabulário que distingue estas ementas do resto do índice (termo (ementas, × frequência relativa)): "
                   + ", ".join(pistas) + " — hipótese de sinônimo/conceito vizinho para um novo grupo; a busca confirma ou descarta")
    return "\n".join(out) + "\n"


def diagnostico_zero(con: sqlite3.Connection, partes: list[tuple[str, str]]) -> str:
    """Busca que zerou: qual grupo/termo zera, e o que aconteceria sem cada um (análogo ao 'você quis dizer' do TJRO)."""
    if len(partes) < 2:
        return ""
    cont = lambda ex: con.execute("SELECT COUNT(*) FROM fts WHERE fts MATCH ?", (ex,)).fetchone()[0]
    linhas = []
    for k, (rot, ex) in enumerate(partes[:8]):
        so = cont(ex)
        sem = cont(" AND ".join(e for i, (_, e) in enumerate(partes) if i != k))
        linhas.append(f"  {rot}: sozinho {so} · sem ele, o resto tem {sem}")
    return ("\nO que zerou a busca (contagem por grupo/termo no índice inteiro):\n" + "\n".join(linhas)
            + "\n  → o grupo com 'sozinho 0' não existe no índice (vocabulário: tente outros sinônimos); se todos existem, é a combinação"
              " que não ocorre — afrouxe o grupo cuja retirada mais devolve.")


def outros_acordaos_do_processo(con: sqlite3.Connection, processo: str, acordao: str) -> str:
    rows = con.execute("SELECT acordao, recurso FROM acordaos WHERE processo=? AND acordao<>? ORDER BY acordao", (processo, acordao)).fetchall()
    rep_ = con.execute("SELECT COUNT(*) FROM republicacoes WHERE acordao=?", (acordao,)).fetchone()[0]
    if not rows:
        return ""
    lista = "; ".join(f"{r['acordao']} ({r['recurso'] or 'acórdão'})" for r in rows[:5])
    return (f"⚠ este PROCESSO tem outro(s) acórdão(s) no índice: {lista}{' …' if len(rows) > 5 else ''} — embargos ou recurso "
            "posterior podem ter alterado ou esclarecido o julgado; a citação vale para o acórdão que você abriu")


def cobertura(con: sqlite3.Connection) -> str:
    r = con.execute("""SELECT COUNT(DISTINCT s.edicao) n, MIN(e.data) a, MAX(e.data) b
                       FROM secoes s JOIN edicoes e USING(edicao)""").fetchone()
    tot = con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0]
    if not r["n"]:
        return "índice local VAZIO — rode `sincronizar_boletim_tjse` antes de buscar"
    nulas = con.execute("SELECT COUNT(*) FROM edicoes e WHERE data IS NULL AND EXISTS(SELECT 1 FROM secoes s WHERE s.edicao=e.edicao)").fetchone()[0]
    return (f"{tot} acórdãos de {r['n']} edição(ões) do Boletim, publicadas de {br(r['a'])} a {br(r['b'])} "
            + (f"[+{nulas} edição(ões) com data não reconhecida, fora deste intervalo] " if nulas else "")
+ "(cada edição traz os julgados do mês anterior)" + _aviso_incompletas(con))


# --------------------------------------------------------------------------- #
# Recibos e conferência                                                        #
# --------------------------------------------------------------------------- #
def _arq_recibo(acordao: str) -> str:
    return os.path.join(DIR_RECIBOS, f"{acordao}.json")


def ler_recibo(acordao: str) -> dict | None:
    """sha256 divergente = corrupção → posto de lado (com incidente). Cabeçalho que o parser ATUAL não reconhece NÃO
    destrói o recibo (um bug de parser apagaria o acervo inteiro): devolve com `aviso`. HTML de OUTRO acórdão
    (cabeçalho reconhecido e diferente) → posto de lado."""
    num = re.sub(r"\D", "", acordao or "")
    caminho = _arq_recibo(num)
    try:
        with open(caminho, encoding="utf-8") as f:
            rec = json.load(f)
        sha_ok = hashlib.sha256(rec["html"].encode("utf-8")).hexdigest() == rec["sha256"]
        cab = parse_teor(rec["html"])["acordao"]
    except FileNotFoundError:
        return None
    except Exception:
        sha_ok, cab, rec = False, "", None
    if rec is not None and sha_ok and rec.get("acordao") == num and cab in ("", num):
        try:  # parser que falha não atualiza nem destrói o recibo (o conteúdo é íntegro: o sha256 já conferiu)
            atual = _campos_de_custodia(rec)
        except Exception:
            atual = {}
        if atual and any(rec.get(k) != v for k, v in atual.items()):  # parser melhorou: atualiza sem rede
            with contextlib.suppress(Exception):
                rec.update(atual)
                tmp = f"{caminho}.{os.getpid()}.tmp"
                with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
                    json.dump(rec, f, ensure_ascii=False)
                os.replace(tmp, caminho)
        if cab == "":
            rec["aviso"] = "o cabeçalho deste recibo não foi reconhecido pelo parser atual; conteúdo íntegro (sha256 confere)"
        return rec
    with contextlib.suppress(OSError):
        os.replace(caminho, caminho + ".inconsistente")
    with contextlib.suppress(Exception):
        _pausar(0, f"recibo {num} posto de lado ({'sha256 não confere' if not sha_ok else 'HTML de outro acórdão'})")
    return None


def _bruto(corpo: str, tn: str, pos_norm: int) -> int:
    """Posição no texto BRUTO equivalente a `pos_norm` no texto normalizado. norm() só colapsa e remove: a razão
    entre os comprimentos é estável, então caminha-se do palpite proporcional até casar o contexto."""
    if pos_norm <= 0:
        return 0
    if pos_norm >= len(tn):
        return len(corpo)
    alvo = norm(tn[pos_norm: pos_norm + 40])[:24]
    if not alvo:
        return min(len(corpo), int(pos_norm * len(corpo) / max(len(tn), 1)))
    chute = min(len(corpo) - 1, int(pos_norm * len(corpo) / max(len(tn), 1)))
    for raio in (60, 400, 2000, len(corpo)):
        ini, fim = max(0, chute - raio), min(len(corpo), chute + raio)
        k = norm(corpo[ini:fim]).find(alvo)
        if k < 0:
            continue
        # k é índice no normalizado do recorte: reconstrói caminhando caractere a caractere
        conta = 0
        for i in range(ini, fim):
            if len(norm(corpo[ini:i + 1])) > conta:
                conta = len(norm(corpo[ini:i + 1]))
            if conta > k:
                return i
        return ini
    return chute


def _campos_de_custodia(rec: dict) -> dict:
    """Campos no formato dos recibos dos MCPs do TJRO e do STJ — `id_documento`, `nr_processo`, `texto` — para que um
    verificador de fichas (ex.: lint de citações de peça) confira o que foi citado contra o que o portal entregou."""
    d = parse_teor(rec["html"])
    corpo = d["texto"][d["inicio_conteudo"]:]
    # Quem lê o recibo depois (um lint de citações, por exemplo) não tem como saber que parte do voto é palavra do
    # TJSE: o voto transcreve ementas inteiras de outros tribunais, e um trecho copiado de lá está literalmente no
    # texto. Então o recibo leva também O QUE NÃO É palavra do tribunal, para que a conferência avise em vez de aprovar.
    tn = norm(corpo)
    ini = next((m.start() for m in re.finditer(r"\bacordam\b", tn) if "estado de sergipe" in tn[m.start(): m.start() + 450]), 0)
    div = faixa_divergente(tn, ini)
    return {"id_documento": rec["acordao"], "nr_processo": rec["processo"], "tribunal": "TJSE", "tipo": "ACÓRDÃO",
            "data_julgamento": br(d.get("data_julgamento")), "orgao": d.get("orgao_fecho") or "", "relator": d.get("relator") or "",
            "texto": corpo,
            # EM BRUTO, recortado do próprio `texto`: quem lê o recibo aplica a SUA normalização, a mesma que usa no
            # `texto`. Gravar já normalizado obrigava o leitor a ter a mesma função que o servidor — e duas
            # normalizações quase iguais deixam passar exatamente o que o alerta existe para pegar (red team do
            # lint, 21/09/2026, L1: "nº 7" virava "n 7" aqui e "no 7" lá).
            "trechos_transcritos": [corpo[_bruto(corpo, tn, a): _bruto(corpo, tn, b)] for a, b in faixas_transcritas(tn, ini)],
            "trecho_divergente": corpo[_bruto(corpo, tn, div[0]):] if div else "",
            "normalizacao": "trechos em bruto, recortados de `texto` — normalize com a sua própria função"}


def gravar_recibo(acordao: str, processo: str, html_bruto: str) -> dict:
    os.makedirs(DIR_RECIBOS, mode=0o700, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(DIR_RECIBOS, 0o700)  # makedirs não corrige pasta que já existia com 0755
    rec = {"acordao": acordao, "processo": processo, "obtido_em": _dt.datetime.now().isoformat(timespec="seconds"),
           "url": f"{URL_TEOR}?tmp.numprocesso={processo}&tmp.numacordao={acordao}",
           "sha256": hashlib.sha256(html_bruto.encode("utf-8")).hexdigest(), "html": html_bruto}
    rec.update(_campos_de_custodia(rec))
    caminho = _arq_recibo(acordao)
    with open(os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
    return rec


_TRIB = r"(?:tj-?[a-z]{2}|stj|stf|trf-?\d|tst|trt-?\d+|tnu)"
_RE_ATRIB = re.compile(r"\(" + _TRIB + r"\b"  # "(TJ-MG - …)", "(tj-pr 0048…)", "(STJ, REsp …)"
                       r"|\((?:resp|aresp|agint|agrg|edcl|eresp|rms|adi|adpf|apelacao(?: civel)?|agravo de instrumento)\b[^()]{0,220}"
                       r"\brel(?:ator[a]?|\.)?\s*(?:p/|para|min|des|juiz|dr)"
                       r"|\b" + _TRIB + r"\s*[-,–]\s*(?:resp|aresp|agint|agrg|edcl|re|are|hc|rhc|apelacao|ac|ai)\b[^.\n]{0,200}\brel")
_RE_ABRE_BLOCO = re.compile(r"\bementa\s*:|\bementa\b(?=\s*[-.]?\s*[a-z])|\bacordao\s*:|\bprecedentes?\s*:|\btranscrevo\b|"
                            r"\bin verbis\b|\bnos seguintes termos\s*:|\bassim (?:decidiu|se manifestou|ementado)\b|\bsumula\s+(?:vinculante\s+)?n?\s*\d+\s*[:-]")
_RE_VOZ_PROPRIA = re.compile(r"\b(nesse sentido|neste sentido|com efeito|no caso dos autos|no caso em tela|entendo|"
                             r"ante o exposto|diante do exposto|pelo exposto|e como voto|voto por|voto pelo|passo a|compulsando)\b")
_RE_CARA_DE_EMENTA = re.compile(r"\brecurso\s+(?:\w+\s+){0,3}(?:conhecido|provido|desprovido|improvido|nao provido)\b|"
                                r"\btese de julgamento\b|\bcaso em exame\b|\bquestao em discussao\b|\bdispositivos? relevantes?\b|"
                                r"\bsentenca (?:mantida|reformada)\b|\bapelacao\s+(?:civel\s+)?(?:conhecida|provida|desprovida)\b")
_RE_DIVERGENCIA = re.compile(r"\b(?:peco|pedi[dn]o\s+de?|com a devida|data)\s+venia\b[^.]{0,120}\b(?:diverg|discord)|\bdivirjo\b|"
                             r"\bvoto\s+(?:vencido|divergente|vista)\b|\bouso\s+divergir\b|\bvoto[- ]vista\b")
_RE_ALEGACAO = re.compile(r"\b(sustent\w+|aleg\w+|aduz\w*|argument\w+|pugn\w+|requer\w*|assever\w+|defende\w*|afirm\w+|"
                          r"em suas razoes|nas razoes|em contrarrazoes|irresignad\w+)\b")
_RE_QUEM_ALEGA = re.compile(r"\b(apelante|apelad[oa]|agravante|agravad[oa]|recorrente|recorrid[oa]|embargante|embargad[oa]|"
                            r"autor[a]?|reu|re\b|requerente|requerid[oa]|impetrante|parte|banco|ministerio publico|parquet|procuradoria)\b")
_RE_NEGACAO = re.compile(r"\b(nao|jamais|nunca|inexist\w*|descab\w*|incabivel|incabiveis|afasta\w*|inaplicav\w*|indevid\w*|"
                         r"improced\w*|nega\w*|rejeit\w*|sem\s+raz(?:ao|oes)|carece\w*|impossibilidade|vedad[oa]s?)\b[^.;:]{0,60}$")
_RE_NEGACAO_FALSA = re.compile(r"\bnao\s+(obstante|so\b|apenas|somente|se\s+confunde)")
PISO_TRECHO_PALAVRAS, PISO_TRECHO_CHARS, VAO_MAXIMO, ENCADEIA_MAX = 4, 25, 1500, 1200


def faixas_transcritas(tn: str, inicio: int = 0) -> list[tuple[int, int]]:
    """Faixas do texto NORMALIZADO que são palavra de outro julgado: da abertura do bloco ("Ementa:", "Precedentes:",
    "transcrevo") até a atribuição que o fecha ("(TJ-MG - …)", "(tj-pr 0048…)", "STJ - REsp …, Rel."). Alerta por
    PERTENCIMENTO. Blocos em sequência só se encadeiam se o intervalo for curto e sem marca de voz do próprio relator
    ("nesse sentido", "no caso dos autos", "entendo"…) — red teams de 21/09/2026 (1: achado 1; 2: B1, B11, B12)."""
    faixas, piso = [], inicio
    for m in _RE_ATRIB.finditer(tn, inicio):
        if m.start() < piso:
            continue
        prof, fim = 0, m.end()
        if tn[m.start()] == "(":
            for k in range(m.start(), min(len(tn), m.start() + 700)):  # parênteses aninhados: "Des.(a) Fulana"
                prof += (tn[k] == "(") - (tn[k] == ")")
                if prof == 0:
                    fim = k + 1
                    break
        else:
            pt = tn.find(".", m.end())
            fim = pt + 1 if 0 <= pt - m.end() < 300 else m.end()
        aberturas = [a.start() for a in _RE_ABRE_BLOCO.finditer(tn, piso, m.start())]
        intervalo = tn[piso: m.start()]
        if aberturas and m.start() - aberturas[-1] <= 9000:
            # a abertura mais próxima cuja distância até a atribuição não contenha voz própria; senão, a última
            ini = next((a for a in aberturas if not _RE_VOZ_PROPRIA.search(tn[a: m.start()])), aberturas[-1])
        elif faixas and not _RE_VOZ_PROPRIA.search(intervalo) and (
                len(intervalo) < ENCADEIA_MAX or (len(intervalo) < 6000 and _RE_CARA_DE_EMENTA.search(intervalo))):
            ini = piso
        else:
            ini = max(piso, m.start() - 300)  # sem abertura reconhecida: recuo curto, para não marcar voto próprio
        faixas.append((ini, fim))
        piso = fim
    return faixas


def faixa_divergente(tn: str, inicio: int = 0) -> tuple[int, int] | None:
    """Do primeiro sinal de divergência ("peço vênia para divergir", "voto vencido", "voto-vista") até o fim: o que está
    ali pode ser o voto VENCIDO. Citar voto vencido como se fosse o acórdão é erro sem conserto."""
    m = _RE_DIVERGENCIA.search(tn, inicio)
    return (m.start(), len(tn)) if m else None


def conferir(texto: str, trecho: str, inicio_voto: int = 0) -> dict[str, Any]:
    """Conferência literal por palavra inteira; `[...]` separa fragmentos que devem vir em ordem, a no máximo
    VAO_MAXIMO caracteres um do outro."""
    frags = [f.strip() for f in re.split(r"\[\s*\.\.\.\s*\]|\(\s*\.\.\.\s*\)", trecho) if f.strip()]
    if not frags:
        return {"ok": False, "erro": "trecho vazio"}
    util = norm(" ".join(frags))
    if len(util.split()) < PISO_TRECHO_PALAVRAS or len(util) < PISO_TRECHO_CHARS:
        return {"ok": False, "erro": f"trecho curto demais para conferência útil (mínimo {PISO_TRECHO_PALAVRAS} palavras e "
                                     f"{PISO_TRECHO_CHARS} caracteres): qualquer acórdão contém isso"}
    tn = norm(texto)
    pos, ini0, spans = 0, None, []
    for f in frags:
        fn = norm(f)
        m = re.search(r"(?<!\w)" + re.escape(fn) + r"(?!\w)", tn[pos:])
        if not m:
            return {"ok": False, "fragmento": f}
        a, b = pos + m.start(), pos + m.end()
        if spans and a - spans[-1][1] > VAO_MAXIMO:
            return {"ok": False, "fragmento": f, "erro": f"o fragmento aparece, mas a {a - spans[-1][1]} caracteres do anterior "
                    f"(máximo {VAO_MAXIMO}): `[...]` não pode costurar partes distantes do acórdão"}
        spans.append((a, b))
        if ini0 is None:
            ini0 = a
        pos = b
    alertas = []
    if not inicio_voto:  # transcrição só existe depois do fecho do próprio TJSE; antes dele é a ementa da casa
        for mf in re.finditer(r"\bacordam\b", tn):
            if "estado de sergipe" in tn[mf.start(): mf.start() + 450]:
                inicio_voto = mf.start()
                break
    faixas = faixas_transcritas(tn, inicio_voto)
    em_transcricao = any(a < fb and b > fa for a, b in spans for fa, fb in faixas)
    if em_transcricao:
        alertas.append("TRANSCRIÇÃO: o trecho está dentro de bloco que o voto transcreve de OUTRO julgado/tribunal — não é "
                       "palavra do TJSE. Se for citar, cite como o TJSE citando; melhor: pesquise o original.")
    div = faixa_divergente(tn, inicio_voto)
    if div and any(b > div[0] for _, b in spans):
        alertas.append("VOTO DIVERGENTE: o trecho vem depois de um sinal de divergência no acórdão (pedido de vênia, voto "
                       "vencido ou voto-vista). Pode ser o voto VENCIDO — leia quem venceu antes de citar como entendimento do órgão.")
    if not em_transcricao:
        # aspas: norm() leva todas a ' — ímpar antes + uma depois, perto, = o tribunal está citando alguém
        antes_q, depois_q = tn[max(0, ini0 - 1200): ini0], tn[pos: pos + 1200]
        n_q = len(re.findall(r"(?<![a-z])'|'(?![a-z])", antes_q))
        if n_q % 2 == 1 and re.search(r"'(?![a-z])", depois_q):
            alertas.append("ENTRE ASPAS: o trecho parece estar dentro de aspas no acórdão — é o tribunal citando alguém (doutrina, "
                           "lei, decisão recorrida, outro julgado). Confira de quem é a frase antes de atribuí-la ao TJSE.")
        jan = tn[max(0, ini0 - 400): ini0]
        ult = max((x.end() for x in _RE_ALEGACAO.finditer(jan)), default=-1)
        if ult >= 0 and _RE_QUEM_ALEGA.search(jan[max(0, ult - 160): ult + 160]) and not _RE_VOZ_PROPRIA.search(jan[ult:]):
            alertas.append("ALEGAÇÃO DA PARTE: pouco antes do trecho o texto relata o que uma parte (ou o MP) sustenta/alega — "
                           "o trecho pode ser tese da parte, não decisão do tribunal. Confira no relatório/voto quem fala.")
    antes = tn[max(0, ini0 - 90): ini0]
    if _RE_NEGACAO.search(antes) and not _RE_NEGACAO_FALSA.search(antes[-40:]):
        alertas.append("NEGAÇÃO: há negativa logo antes do trecho — o recorte pode inverter o julgado. Não citar sem ler.")
    return {"ok": True, "alertas": alertas, "contexto": re.sub(r"\s+", " ", tn[max(0, ini0 - 120): pos + 120])}


_PARTICULAS = {"de", "da", "do", "das", "dos", "e", "d'"}


def nome_proprio(s: str) -> str:
    return " ".join(w.lower() if (w.lower() in _PARTICULAS and i) else w.capitalize() for i, w in enumerate(s.split()))


def citacao(d: dict, orgao: str, link: str, nivel: str) -> str:
    dj = f", julgado em {br(d['data_julgamento'])}" if d.get("data_julgamento") else ""
    return (f"([TJSE, {d.get('recurso') or 'Acórdão'}, processo nº {d['processo']}, acórdão nº {d['acordao']}, "
            f"Rel. {nome_proprio(d.get('relator') or '?')}, {orgao}{dj}]({link})) — verificação: {nivel}")


# --------------------------------------------------------------------------- #
# Ferramentas                                                                  #
# --------------------------------------------------------------------------- #
async def sincronizar(meses: int = 3, max_requisicoes: int = MAX_REQ_POR_SINCRONIZACAO) -> str:
    meses = max(1, min(int(meses), 24))
    orc = max(2, min(int(max_requisicoes), MAX_REQ_POR_SINCRONIZACAO))
    con, gasto, linhas = _db(), 0, []
    hoje = _dt.date.today()
    a_, m_ = divmod(hoje.year * 12 + hoje.month - 1 - meses, 12)
    ini = _dt.date(a_, m_ + 1, 1)
    try:
        h = await _http("POST", f"{BOLETIM}/pesquisar.wsp", referer=f"{BOLETIM}/pesquisar.wsp", data={
            "tmp_origem": "", "tmp.diario.dt_inicio": ini.strftime("%d/%m/%Y"),
            "tmp.diario.dt_fim": hoje.strftime("%d/%m/%Y"), "tmp.diario.cd_caderno": "",
            "tmp.diario.cd_secao": "", "tmp.diario.pal_chave": "", "wi.token": "", "tmp.diario.id_advogado": ""})
        gasto += 1
        eds = parse_edicoes(h)
        if not eds:
            return "PESQUISA NÃO REALIZADA — a listagem de edições veio sem nenhuma edição reconhecível (layout mudou?)."
        for e in eds:
            con.execute("INSERT OR REPLACE INTO edicoes VALUES(?,?,?)", (e["edicao"], e["rotulo"], e["data"]))
        con.commit()
        for e in sorted(eds, key=lambda x: -x["edicao"]):  # mais recente primeiro
            feitas = {r["codigo"] for r in con.execute("SELECT codigo FROM secoes WHERE edicao=?", (e["edicao"],))}
            menu_conhecido = con.execute("SELECT valor FROM meta WHERE chave=?", (f"menu:{e['edicao']}",)).fetchone()
            if menu_conhecido:
                secs = json.loads(menu_conhecido[0])
            else:
                if gasto >= orc:
                    break
                hm = await _http("GET", f"{BOLETIM}/menu.wsp", referer=f"{BOLETIM}/inicial.wsp", params={
                    "tmp.diario.nu_edicao": e["edicao"], "tmp.diario.id_advogado": "", "tmp.diario.cd_caderno": "",
                    "tmp.diario.cd_secao": "", "tmp.diario.pal_chave": ""})
                gasto += 1
                secs = parse_menu(hm)
                if not secs:
                    linhas.append(f"  ⚠ menu da edição {e['edicao']} veio sem nenhuma seção reconhecível — edição NÃO sincronizada "
                                  "(será tentada de novo; se persistir, o layout mudou).")
                    continue
                _grava_meta(con, f"menu:{e['edicao']}", json.dumps(secs, ensure_ascii=False))
            for s in secs:
                if s["codigo"] in feitas:
                    continue
                vz = con.execute("SELECT valor FROM meta WHERE chave=?", (f"vazia:{e['edicao']}:{s['codigo']}",)).fetchone()
                if vz and (time.time() - float(vz[0])) < 7 * 86400:
                    continue  # veio sem acórdão há menos de 7 dias: não insiste (mas a edição segue contada como incompleta)
                if gasto >= orc:
                    break
                pags, completa = paginas_em_disco(e["edicao"], s["codigo"])  # retoma do que já está em disco
                estourou = False
                while not completa:
                    if gasto >= orc:
                        estourou = True
                        break
                    if not pags:
                        dados = {"tmp.diario.cd_secao": s["codigo"], "tmp.diario.nu_edicao": e["edicao"],
                                 "tmp.diario.id_advogado": "", "tmp.diario.pal_chave": ""}
                    else:
                        dados = campos_grid(pags[-1])
                        dados["grid.lista_conteudodiario.next"] = str(proxima_posicao(pags[-1]))
                        if "tmp.diario.cd_secao" not in dados:
                            raise PesquisaNaoRealizada(f"há página seguinte na seção {s['nome']} da edição {e['edicao']}, mas o "
                                                       "formulário de paginação não foi reconhecido (layout mudou).")
                    hs = await _http("POST", f"{BOLETIM}/principal.wsp", referer=f"{BOLETIM}/menu.wsp", data=dados)
                    gasto += 1
                    if "</html>" not in hs[-400:].lower():
                        raise PesquisaNaoRealizada(f"resposta TRUNCADA na seção {s['nome']} da edição {e['edicao']} "
                                                   f"({len(hs)} caracteres, sem </html>); nada dela foi indexado.")
                    novos_ids = {i["acordao"] for i in parse_secao(hs)}
                    if pags and novos_ids and novos_ids <= {i["acordao"] for h0 in pags for i in parse_secao(h0)}:
                        raise PesquisaNaoRealizada(f"a página {len(pags) + 1} da seção {s['nome']} (ed. {e['edicao']}) repetiu a "
                                                   "anterior — o portal ignorou a paginação; seção NÃO marcada como baixada.")
                    if not novos_ids:
                        # seção sem acórdão NUNCA é marcada como baixada: pode ser página de erro (até com o cabeçalho do
                        # Boletim — red team 2, B4) ou mês sem julgado naquele órgão. Nova tentativa só depois de 7 dias.
                        _grava_meta(con, f"vazia:{e['edicao']}:{s['codigo']}", str(time.time()))
                        linhas.append(f"  ⚠ edição {e['edicao']} · {s['nome']}: NENHUM acórdão reconhecido "
                                      + ("apesar de haver links — layout mudou" if "relatorio.wsp" in hs else
                                         "(página de erro, ou órgão sem julgado publicado no mês)")
                                      + "; seção NÃO marcada como baixada — nova tentativa em 7 dias; a edição fica como incompleta.")
                        estourou = True
                        break
                    guardar_bruto(e["edicao"], s["codigo"], hs, len(pags) + 1)
                    pags.append(hs)
                    completa = proxima_posicao(hs) is None
                if estourou or not completa:
                    if pags and not completa:
                        linhas.append(f"  … edição {e['edicao']} · {s['nome']}: {len(pags)} página(s) guardada(s), FALTAM páginas — "
                                      "seção ainda fora do índice; chame de novo.")
                    if gasto >= orc:
                        break
                    continue
                itens = parse_secao("\n".join(pags))  # juntas: a classe aberta na página 1 continua na 2
                novos = indexar_secao(con, e["edicao"], s["codigo"], s["nome"], itens)
                an = anomalias_secao(itens) if itens else []
                linhas.append(f"  edição {e['edicao']} ({br(e['data'])}) · {s['nome']}: {len(itens)} acórdãos em {len(pags)} página(s) "
                              f"({novos} novos)" + (f" ⚠ ANOMALIAS: {'; '.join(an)}" if an else ""))
        falta = 0
        for e in eds:
            m = con.execute("SELECT valor FROM meta WHERE chave=?", (f"menu:{e['edicao']}",)).fetchone()
            n_secs = len(json.loads(m[0])) if m else 5  # edição ainda não visitada: 5 seções é o medido
            n_vz = con.execute("SELECT COUNT(*) FROM meta WHERE chave LIKE ? AND CAST(valor AS REAL) > ?",
                               (f"vazia:{e['edicao']}:%", time.time() - 7 * 86400)).fetchone()[0]
            falta += max(0, n_secs - n_vz - con.execute("SELECT COUNT(*) FROM secoes WHERE edicao=?", (e["edicao"],)).fetchone()[0])
    except Exception as ex:
        if not isinstance(ex, PesquisaNaoRealizada):
            ex = f"ERRO INTERNO do servidor ({type(ex).__name__}: {ex}) — é defeito da ferramenta, não do portal; avise o advogado"
        return (f"SINCRONIZAÇÃO INTERROMPIDA — {ex}\nFeito antes da interrupção ({gasto} requisições):\n"
                + ("\n".join(linhas) or "  nada") + f"\nÍndice: {cobertura(con)}")
    curto = (f"\n⚠ Pedi {meses} mês(es) e a lista do portal trouxe {len(eds)} edição(ões) (a mais antiga de {br(min((x['data'] or '9999-12-31') for x in eds))}): "
             "o portal pode limitar a listagem — o período anterior NÃO foi coberto.") if len(eds) < meses - 1 else ""
    cont = curto + (f"\nFaltam ≥ {falta} seção(ões) no período pedido: chame de novo (o teto por chamada é {orc} requisições; "
            "o que já foi baixado não é rebaixado)." if falta else "\nTodas as edições LISTADAS pelo portal no período estão completas.")
    return (f"Sincronização do Boletim Jurídico do TJSE — {gasto} requisição(ões)\n" + ("\n".join(linhas) or "  nada novo")
            + cont + f"\nÍndice: {cobertura(con)}")


def _grava_meta(con: sqlite3.Connection, chave: str, valor: str) -> None:
    con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (chave, valor))
    con.commit()


def buscar(consulta: str | None = None, grupos: list[list[str]] | None = None, orgao: str | None = None,
           classe: str | None = None, relator: str | None = None, numero: str | None = None,
           por_pagina: int = 10, pagina: int = 1, data_inicio: str | None = None, data_fim: str | None = None,
           ordenacao: str = "relevantes", exato: bool = False, em: str = "tudo", cita: str | None = None) -> str:
    try:
        return _buscar(consulta, grupos, orgao, classe, relator, numero, por_pagina, pagina, data_inicio, data_fim,
                       ordenacao, exato, em, cita)
    except Exception as ex:
        return (f"BUSCA NÃO REALIZADA — erro do índice local ({type(ex).__name__}: {ex}). Isto NÃO é 'nada encontrado': "
                "reformule sem pontuação especial ou rode `diagnostico_tjse`.")


def _data_iso(v: str | None, rotulo: str) -> str | None:
    if not v:
        return None
    m = re.fullmatch(r"\s*(\d{2})/(\d{2})/(\d{4})\s*", v) or None
    if m:
        d, me, a = m.groups()
    else:
        m = re.fullmatch(r"\s*(\d{4})-(\d{2})-(\d{2})\s*", v)
        if not m:
            raise ValueError(f"`{rotulo}` deve ser dd/mm/aaaa ou aaaa-mm-dd")
        a, me, d = m.groups()
    return _dt.date(int(a), int(me), int(d)).isoformat()


CAMPOS_BUSCAVEIS = ("cabecalho", "caso", "questao", "razoes", "dispositivo", "tese")
_PESO_CAMPO = {"cabecalho": 3.0, "caso": 1.0, "questao": 5.0, "razoes": 2.0, "dispositivo": 1.0, "tese": 5.0}


def _ref_citada(cita: str) -> tuple[str, str] | None:
    """Normaliza o que o usuário pediu em `cita` para a chave do grafo."""
    dig = re.sub(r"\D", "", cita or "")
    if len(dig) == 12:
        return ("tjse", dig)
    a = ancoras(cita or "", 1)
    return ("qualificado", a[0]) if a else None


def _buscar(consulta, grupos, orgao, classe, relator, numero, por_pagina, pagina, data_inicio, data_fim,
            ordenacao, exato, em="tudo", cita=None) -> str:
    con = _db()
    cab = f"Índice local do Boletim Jurídico do TJSE: {cobertura(con)}.\n"
    rodape = ("\nLIMITES: só 2º grau publicado no Boletim — sem Turmas Recursais, Turma de Uniformização nem monocráticas, e só "
              "as edições sincronizadas. Zero resultado aqui NÃO é 'não localizado no TJSE'. " + onde_mais_procurar() + " Ementa do Boletim vem em CAIXA ALTA: para citar entre "
              "aspas, `verificar_citacao_tjse` (confere no inteiro teor).")
    where, args = [], []
    if numero:
        n = re.sub(r"\D", "", numero)
        if len(n) not in (9, 12):
            return (f"Pedido recusado: `numero` com {len(n)} dígitos. O TJSE numera por PROCESSO (12 dígitos, ex. 202600737656) e "
                    "ACÓRDÃO (9 dígitos); o Boletim e o inteiro teor não trazem número CNJ, então não há como buscar por ele aqui. "
                    "Isto NÃO é 'não localizado'.")
        where.append("(a.acordao=? OR a.processo=?)"); args += [n, n]
    try:
        partes = partes_fts(consulta, grupos, exato)
        q = " AND ".join(e for _, e in partes)
        di, df = _data_iso(data_inicio, "data_inicio"), _data_iso(data_fim, "data_fim")
        if di and df and di > df:
            raise ValueError(f"`data_inicio` ({br(di)}) é posterior a `data_fim` ({br(df)}) — filtro impossível, não ausência de julgado")
    except ValueError as ex:
        return f"Consulta recusada: {ex}"
    if not q and not numero and not cita:
        return "Informe `consulta`, `grupos`, `numero` ou `cita`."
    campos_pedidos = [c.strip().lower() for c in re.split(r"[,;+ ]+", em or "tudo") if c.strip()]
    if campos_pedidos == ["tudo"]:
        tab_fts, q_fts, pesos = "fts", q, "0, 5.0, 2.0, 1.0"
    else:
        ruins = [c for c in campos_pedidos if c not in CAMPOS_BUSCAVEIS]
        if ruins:
            return (f"`em` não conhece {ruins}. Use 'tudo' ou um ou mais de: {', '.join(CAMPOS_BUSCAVEIS)} "
                    "(são as partes da ementa estruturada; ~2/3 dos acórdãos a seguem — nos demais tudo está em "
                    "`cabecalho`, então busca por campo NÃO perde acórdão, só deixa de distingui-lo).")
        tab_fts = "fts_campos"
        q_fts = "{" + " ".join(campos_pedidos) + "} : (" + (q or "") + ")" if q else q
        pesos = "0, " + ", ".join(str(_PESO_CAMPO[c] if c in campos_pedidos else 0.0) for c in CAMPOS_BUSCAVEIS)
    if cita:
        ref = _ref_citada(cita)
        if not ref:
            return (f"`cita`={cita!r} não é uma referência que o grafo conheça. Use 'Tema 1061', 'Súmula 479/STJ', "
                    "'IRDR 15', 'SV 47' ou o nº de PROCESSO do TJSE (12 dígitos).")
        where.append("a.acordao IN (SELECT origem FROM citacoes WHERE tipo=? AND ref=?)"); args += [ref[0], ref[1]]
        filtros_cita = f"cita={ref[1]}"
    else:
        filtros_cita = ""
    por_bm25 = bool(q) and ordenacao == "relevantes"
    if q and not por_bm25:  # com bm25 o MATCH já está na subconsulta: não varrer o FTS duas vezes
        where.append(f"a.acordao IN (SELECT acordao FROM {tab_fts} WHERE {tab_fts} MATCH ?)"); args.append(q_fts)
    for col, val in (("orgao", orgao), ("classe", classe), ("relator", relator)):
        if val:
            esc = val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            where.append(f"a.{col} LIKE ? ESCAPE '\\'"); args.append(f"%{esc}%")
    if di:
        where.append("e.data >= ?"); args.append(di)
    if df:
        where.append("e.data <= ?"); args.append(df)
    filtros = [f"{k}={v!r}" for k, v in (("orgao", orgao), ("classe", classe), ("relator", relator), ("numero", numero),
                                         ("data_inicio", data_inicio), ("data_fim", data_fim), ("cita", cita)) if v]
    cond = " AND ".join(where) or "1=1"
    if por_bm25:
        base = (f"(SELECT acordao ac, bm25({tab_fts}, {pesos}) rk FROM {tab_fts} WHERE {tab_fts} MATCH ?) r "
                "JOIN acordaos a ON a.acordao = r.ac JOIN edicoes e USING(edicao)")
        args = [q_fts] + args
    else:
        base = "acordaos a JOIN edicoes e USING(edicao)"
    sql = f" FROM {base} WHERE {cond}"
    total = con.execute("SELECT COUNT(*)" + sql, args).fetchone()[0]
    if not q:
        ordenacao = "recentes" if ordenacao == "relevantes" else ordenacao  # sem texto não há relevância: diz a ordem real
    por_pagina = 5 if por_pagina <= 5 else (10 if por_pagina <= 10 else 20)
    pagina = max(1, int(pagina))
    if ordenacao not in ("relevantes", "recentes", "antigos"):
        return "`ordenacao` deve ser 'relevantes', 'recentes' ou 'antigos'."
    if por_bm25:
        rows = con.execute(f"SELECT a.*, e.data ed_data{sql} ORDER BY r.rk, a.edicao DESC, a.acordao DESC LIMIT ? OFFSET ?",
                           args + [por_pagina, (pagina - 1) * por_pagina]).fetchall()
    else:
        ordem = "ASC" if ordenacao == "antigos" else "DESC"
        rows = con.execute(f"SELECT a.*, e.data ed_data{sql} ORDER BY a.edicao {ordem}, a.acordao {ordem} LIMIT ? OFFSET ?",
                           args + [por_pagina, (pagina - 1) * por_pagina]).fetchall()
    filtro_data = f" · publicação de {br(di)} a {br(df)} (data do BOLETIM, não do julgamento)" if (di or df) else ""
    if not rows and total:
        return cab + f"{total} resultado(s), mas a página {pagina} está além do fim (última: {-(-total // por_pagina)})." + rodape
    if not rows:
        sem_filtro = ""
        if q and filtros:
            n0 = con.execute(f"SELECT COUNT(*) FROM {tab_fts} WHERE {tab_fts} MATCH ?", (q_fts,)).fetchone()[0]
            sem_filtro = (f" SEM os filtros ({', '.join(filtros)}) a mesma expressão tem {n0} resultado(s) — foi o filtro que zerou, "
                          "não a falta de julgado." if n0 else "")
        return cab + f"Nada no índice local para {q or numero!r}{filtro_data}.{sem_filtro}" + (diagnostico_zero(con, partes) if q else "") + rodape
    termos = [norm(t) for g in (grupos or []) for t in g]
    termos += [norm(a or b) for a, b in re.findall(r'"([^"]+)"|(\S+)', consulta or "")]
    out = [cab + f"{total} resultado(s) — página {max(1, pagina)} ({por_pagina}/pág.) — ordem: {ordenacao}{filtro_data}"
           + (f" · campo: {'+'.join(campos_pedidos)}" if campos_pedidos != ["tudo"] else "")
           + (f" · {filtros_cita}" if filtros_cita else "") + "\n"
           f"expressão{'' if exato else ' (com variação singular/plural; `exato=true` desliga)'}: "
           f"{q if len(q) < 700 else q[:700] + '…'}\n"]
    if pagina == 1 and total >= 5:
        excl = set(re.findall(r"[a-z]{5,}", q))  # a própria consulta e suas variantes não são "pista"
        out.append(panorama(con, sql, args, por_bm25, total, excl))
    for r in rows:
        em_txt = r["ementa"]
        en = norm(em_txt)
        p = min([en.find(t.rstrip("$*")) for t in termos if en.find(t.rstrip("$*")) >= 0] or [0])
        trecho = em_txt if len(em_txt) <= 900 else ("…" if p > 200 else "") + em_txt[max(0, p - 200): max(0, p - 200) + 900] + "…"
        link = f"{URL_TEOR}?tmp.numprocesso={r['processo']}&tmp.numacordao={r['acordao']}"
        rec = " · recibo do inteiro teor já em disco" if ler_recibo(r["acordao"]) else ""
        rep_ = [x[0] for x in con.execute("SELECT edicao FROM republicacoes WHERE acordao=?", (r["acordao"],))]
        if rep_:
            rec += f"\n  ⚠ REPUBLICADO na(s) edição(ões) {rep_} — pode haver retificação de ementa: confira no inteiro teor"
        cita_ = ancoras(em_txt)
        outros = outros_acordaos_do_processo(con, r["processo"], r["acordao"])
        aut = con.execute("SELECT COUNT(DISTINCT origem) FROM citacoes WHERE tipo='tjse' AND ref=?", (r["processo"],)).fetchone()[0]
        rec += ("\n  Cita: " + " · ".join(cita_)) if cita_ else ""
        rec += (f"\n  ⬆ CITADO por {aut} acórdão(s) deste índice — autoridade interna: julgado que a própria câmara "
                "reusa" if aut else "")
        rec += ("\n  " + outros) if outros else ""
        out.append(f"■ Acórdão {r['acordao']} · processo {r['processo']} · {r['recurso'] or r['classe']}\n"
                   f"  {r['orgao']} (seção do Boletim; o órgão citável é o do FECHO) · {r['relator_rotulo'] or 'Relator'}: {r['relator']}\n"
                   f"  Boletim ed. {r['edicao']}, publicado em {br(r['ed_data'])} (data do julgamento só no inteiro teor){rec}\n"
                   f"  Ementa (Boletim, caixa alta): {trecho}\n  Inteiro teor: {link}\n  verificação: só ementa/índice\n")
    out.append("Próximo passo: `obter_inteiro_teor_tjse(numero_acordao=…)` no que interessar (lê o voto, fixa órgão e data pelo "
               "fecho); antes de aspas, `verificar_citacao_tjse`.")
    return "\n".join(out) + rodape


async def _teor(acordao: str, processo: str | None) -> tuple[dict, dict, bool]:
    lk = _RE_LINK_TEOR.search(acordao or "")  # aceita a URL do inteiro teor colada
    if lk:
        processo, acordao = (lk.group(1), lk.group(2)) if lk.group(1) else (lk.group(4), lk.group(3))
    acordao = re.sub(r"\D", "", acordao or "")
    if len(acordao) == 12 and not processo:
        raise ValueError("isso parece nº de PROCESSO (12 dígitos); o inteiro teor pede o nº do ACÓRDÃO (9 dígitos). "
                         "Ache-o com `buscar_jurisprudencia_tjse(numero=…)`.")
    if not acordao:
        raise ValueError("informe o nº do acórdão (9 dígitos, como sai na busca).")
    rec = ler_recibo(acordao)
    do_disco = rec is not None
    if rec is None:
        processo = re.sub(r"\D", "", processo or "")
        if not processo:
            row = _db().execute("SELECT processo FROM acordaos WHERE acordao=?", (acordao,)).fetchone()
            if not row:
                raise ValueError("acórdão fora do índice local: informe também `numero_processo` (o link do TJSE exige os dois), "
                                 "ou cole a URL do inteiro teor. " + ("" if COMPLEMENTOS else "Os dois números aparecem em qualquer "
                                 "citação completa do TJSE e na página do acórdão no portal oficial."))
            processo = row["processo"]
        h = await _http("GET", URL_TEOR, params={"tmp.numprocesso": processo, "tmp.numacordao": acordao})
        d = parse_teor(h)
        if d["acordao"] != acordao or len(d["texto"]) < 400:
            raise PesquisaNaoRealizada("o portal respondeu, mas sem o acórdão pedido (par processo/acórdão errado, ou página "
                                       "vazia). Nada foi gravado.")
        rec = gravar_recibo(acordao, processo, h)
    return rec, parse_teor(rec["html"]), do_disco


def _orgao_fonte(d: dict) -> str:
    return "fecho" if (d.get("orgao_fecho") and not d.get("fecho_ambiguo")) else "cadastro (seção do Boletim)"


def _orgao_e_avisos(d: dict, acordao: str) -> tuple[str, list[str]]:
    row = _db().execute("SELECT orgao FROM acordaos WHERE acordao=?", (acordao,)).fetchone()
    cad, avisos = (row["orgao"] if row else None), []
    if d["fecho_ambiguo"]:
        avisos.append("FECHO AMBÍGUO: o texto tem fechos de órgãos diferentes (embargos que transcrevem o acórdão "
                      "embargado?). Órgão exibido é o da seção do Boletim, com ressalva — confira lendo.")
        return (cad or "órgão não determinado"), avisos
    if d["orgao_fecho"]:
        if cad and norm_orgao(cad) != norm_orgao(d["orgao_fecho"]):
            avisos.append(f"DIVERGÊNCIA: Boletim publica em '{cad}', o fecho diz '{d['orgao_fecho']}'. Vale o fecho.")
        return d["orgao_fecho"], avisos
    avisos.append("Fecho ('ACORDAM… Tribunal de Justiça do Estado de Sergipe') não localizado: órgão é o da seção do Boletim.")
    return (cad or "órgão não determinado"), avisos


async def obter(numero_acordao: str, numero_processo: str | None = None, com_partes: bool = False,
                max_caracteres: int = 60000) -> str:
    try:
        rec, d, do_disco = await _teor(numero_acordao, numero_processo)
    except PesquisaNaoRealizada as ex:
        return f"PESQUISA NÃO REALIZADA — {ex} Isto NÃO é 'não localizado'."
    except ValueError as ex:
        return f"Pedido recusado: {ex}"
    orgao, avisos = _orgao_e_avisos(d, rec["acordao"])
    max_caracteres = max(2000, int(max_caracteres or 0))
    with contextlib.suppress(Exception):
        outros = outros_acordaos_do_processo(_db(), rec["processo"], rec["acordao"])
        if outros:
            avisos.append(outros.removeprefix("⚠ "))
    if rec.get("aviso"):
        avisos.append(rec["aviso"])
    corpo = d["texto"] if com_partes else d["texto"][d["inicio_conteudo"]:]
    nivel = "inteiro teor lido"
    if len(corpo) > max_caracteres:
        corpo = corpo[:max_caracteres] + f"\n[… cortado em {max_caracteres} de {len(d['texto'])} caracteres; o recibo tem tudo]"
        nivel = "inteiro teor lido EM PARTE (saída cortada — peça o resto com max_caracteres maior antes de afirmar o que o voto diz)"
    if len(d.get("datas_fecho") or []) > 1:
        avisos.append(f"Há {len(d['datas_fecho'])} datas no fecho ({', '.join(br(x) for x in d['datas_fecho'])}); usei a última. Confira.")
    if not com_partes and not d.get("partes_cortadas"):
        avisos.append("Cabeçalho 'EMENTA' não localizado: a qualificação das partes NÃO pôde ser cortada desta saída.")
    return (f"TJSE — acórdão {rec['acordao']} · processo {rec['processo']} · {d['recurso']}\n"
            f"Relator(a): {d['relator']} · Órgão: {orgao} · Julgamento: {br(d['data_julgamento'])}\n"
            f"orgao_fonte: {_orgao_fonte(d)}\n"
            f"Fonte: {rec['url']}\nRecibo: {'lido do disco' if do_disco else 'gravado agora'} · obtido em {rec['obtido_em']} · sha256 {rec['sha256'][:16]}…\n"
            + "".join(f"⚠ {a}\n" for a in avisos)
            + "⚠ O voto costuma TRANSCREVER ementas de outros tribunais: trecho destacado não é, por isso, palavra do TJSE.\n"
            + ("" if com_partes else "(só o bloco de QUALIFICAÇÃO das partes foi cortado; relatório e voto continuam nomeando "
                                     "pessoas, às vezes menor de idade e seu representante — não colar em lugar nenhum fora da peça)\n")
            + f"Citação: {citacao(d, orgao, rec['url'], nivel)}\n{'─' * 60}\n{corpo}")


async def verificar(numero_acordao: str, trecho: str, numero_processo: str | None = None) -> str:
    try:
        rec, d, do_disco = await _teor(numero_acordao, numero_processo)
    except PesquisaNaoRealizada as ex:
        return f"PESQUISA NÃO REALIZADA — {ex} A citação fica NÃO CONFERIDA (não é ❌)."
    except ValueError as ex:
        return f"Pedido recusado: {ex}"
    r = conferir(d["texto"][d["inicio_conteudo"]:], trecho)
    orgao, avisos = _orgao_e_avisos(d, rec["acordao"])
    base = f"acórdão {rec['acordao']} (recibo {'do disco' if do_disco else 'gravado agora'}, sha256 {rec['sha256'][:16]}…)"
    if not r["ok"]:
        return (f"❌ NÃO CONFERE — {base}\nFragmento que não aparece literalmente: «{r.get('fragmento') or r.get('erro')}»\n"
                "Não vai entre aspas. (Diferença de número '1.000'≠'1000' ou palavra cortada também dá ❌ — o lado seguro.)")
    return (f"✅ CONFERE LITERALMENTE — {base}\n" + "".join(f"⚠ {a}\n" for a in r["alertas"] + avisos)
            + f"Contexto (normalizado): …{r['contexto']}…\nCitação: {citacao(d, orgao, rec['url'], 'inteiro teor lido')}")


def mapa_citacoes(referencia: str | None = None, limite: int = 15) -> str:
    """Sem `referencia`: o que o recorte mais cita. Com: quem cita aquilo."""
    con = _db()
    n = con.execute("SELECT COUNT(*) FROM citacoes").fetchone()[0]
    if not n:
        return ("O grafo de citações está vazio — o índice precisa ser (re)sincronizado para extrair o campo "
                "'Jurisprudência relevante citada' das ementas. Rode `diagnostico_tjse`.")
    limite = max(3, min(int(limite or 15), 50))
    if not referencia:
        qual = con.execute("SELECT ref, COUNT(DISTINCT origem) k FROM citacoes WHERE tipo='qualificado' "
                           "GROUP BY ref ORDER BY k DESC LIMIT ?", (limite,)).fetchall()
        lid = con.execute("SELECT ref, COUNT(DISTINCT origem) k FROM citacoes WHERE tipo='tjse' "
                          "GROUP BY ref ORDER BY k DESC LIMIT ?", (limite,)).fetchall()
        dentro = {r["processo"] for r in con.execute("SELECT processo FROM acordaos")}
        linhas = [f"Grafo de citações do índice ({n} arestas, extraídas das ementas — zero rede).",
                  "\nPrecedentes QUALIFICADOS mais citados (súmula, tema, IRDR, IAC):"]
        linhas += [f"  {r['ref']}: {r['k']} acórdão(s)" for r in qual] or ["  —"]
        linhas.append("\nAcórdãos do próprio TJSE mais citados pelos pares (candidatos a julgado-líder):")
        for r in lid:
            onde = "no índice" if r["ref"] in dentro else "FORA do índice (anterior ao período sincronizado)"
            linhas.append(f"  processo {r['ref']}: citado por {r['k']} — {onde}")
        fora = con.execute("SELECT COUNT(DISTINCT ref) FROM citacoes WHERE tipo='tjse' AND ref NOT IN "
                           "(SELECT processo FROM acordaos)").fetchone()[0]
        linhas.append(f"\n{fora} processo(s) do TJSE são citados pelos acórdãos do índice mas estão FORA dele (julgados "
                      "anteriores ao período sincronizado): o grafo enxerga além da janela, mas para LER cada um é "
                      "preciso o nº do ACÓRDÃO (9 dígitos), que a ementa citante não traz — busque-o na base que você "
                      "assinar, ou no portal oficial, e confira aqui com `obter_inteiro_teor_tjse`.")
        linhas.append("Para ver quem cita um deles: `mapa_de_citacoes_tjse(referencia='Tema 1061')` ou o nº do processo.")
        return "\n".join(linhas)
    ref = _ref_citada(referencia)
    if not ref:
        return (f"Não reconheci {referencia!r}. Use 'Tema 1061', 'Súmula 479/STJ', 'IRDR 15', 'SV 47' ou o nº de "
                "PROCESSO do TJSE (12 dígitos).")
    tot = con.execute("SELECT COUNT(DISTINCT origem) FROM citacoes WHERE tipo=? AND ref=?", ref).fetchone()[0]
    if not tot:
        return (f"Nenhum acórdão do índice cita {ref[1]} — no período coberto ({cobertura(con)}). Isso NÃO significa "
                "que o TJSE não tenha aplicado: o grafo só vê o campo 'Jurisprudência relevante citada', que ~1/3 das "
                "ementas preenche.")
    rows = con.execute("SELECT a.acordao, a.processo, a.orgao, a.relator, a.classe, SUBSTR(a.ementa,1,220) e "
                       "FROM citacoes c JOIN acordaos a ON a.acordao=c.origem WHERE c.tipo=? AND c.ref=? "
                       "ORDER BY a.edicao DESC LIMIT ?", (ref[0], ref[1], limite)).fetchall()
    out = [f"{tot} acórdão(s) do índice citam {ref[1]} (mostrando {len(rows)}):"]
    for r in rows:
        out.append(f"■ Acórdão {r['acordao']} · processo {r['processo']} · {r['classe']}\n  {r['orgao']} · {r['relator']}\n"
                   f"  {re.sub(chr(92) + 's+', ' ', r['e'])}…\n  Inteiro teor: {URL_TEOR}?tmp.numprocesso={r['processo']}"
                   f"&tmp.numacordao={r['acordao']}")
    out.append("\nO campo 'Jurisprudência relevante citada' existe em ~1/3 das ementas: quem não o preenche não aparece "
               "aqui, ainda que aplique o mesmo precedente. Para esses, use `buscar_jurisprudencia_tjse`.")
    return "\n".join(out)


def diagnostico() -> str:
    try:
        return _diagnostico()
    except Exception as ex:
        if "locked" in str(ex).lower():
            return (f"tjse_jurisprudencia v{VERSAO}: índice OCUPADO por outro processo ({ex}) — provavelmente uma sincronização ou "
                    "reindexação em curso. Aguarde e repita; NÃO apague a base.")
        return (f"tjse_jurisprudencia v{VERSAO}: o índice local está ILEGÍVEL ({type(ex).__name__}: {ex}). Buscas não são confiáveis. "
                f"Remédio: mover `{ARQ_DB}` para fora e sincronizar de novo (o HTML bruto em `{DIR_SECOES}` não reindexa sozinho "
                "uma base nova — é preciso rebaixar).")


def _diagnostico() -> str:
    with _trava():
        e = _ler_estado()
    agora = time.time()
    reqs = [t for t in e["requisicoes"] if agora - t < 86400]
    pausa = e.get("pausa_ate", 0) - agora
    con = _db()
    n_rec = len([f for f in os.listdir(DIR_RECIBOS)]) if os.path.isdir(DIR_RECIBOS) else 0
    por_secao = "\n".join(f"  {r['nome']}: {r['n']} acórdãos em {r['eds']} edição(ões), publicadas de {br(r['a'])} a {br(r['b'])}"
                          for r in con.execute("""SELECT s.nome, SUM(s.itens) n, COUNT(*) eds, MIN(e.data) a, MAX(e.data) b
                                                  FROM secoes s JOIN edicoes e USING(edicao) GROUP BY s.nome ORDER BY s.nome""")) or "  —"
    buracos = [f"ed. {r['edicao']} ({br(r['data'])})" for r in con.execute(
        """SELECT e.edicao, e.data FROM edicoes e WHERE e.edicao BETWEEN (SELECT MIN(edicao) FROM secoes) AND
           (SELECT MAX(edicao) FROM secoes) AND (SELECT COUNT(*) FROM secoes s WHERE s.edicao=e.edicao) < 5""")]
    mb = os.path.getsize(ARQ_DB) / 1e6 if os.path.exists(ARQ_DB) else 0
    n_cit = con.execute("SELECT COUNT(*) FROM citacoes").fetchone()[0]
    n_proc_cit = con.execute("SELECT COUNT(DISTINCT ref) FROM citacoes WHERE tipo='tjse'").fetchone()[0]
    inc = "\n".join(f"  {i['quando']} — {i['motivo']}" for i in e.get("incidentes", [])[-8:]) or "  nenhum"
    return (f"tjse_jurisprudencia v{VERSAO} (sem rede nesta chamada)\n"
            f"Disjuntor: {'EM PAUSA por ~%d min — %s' % (pausa / 60 + 1, e.get('motivo')) if pausa > 0 else 'livre'}\n"
            f"Requisições: {len([t for t in reqs if agora - t < JANELA_S])}/{JANELA_MAX} em 10 min · {len(reqs)}/{DIA_MAX} em 24 h · "
            f"espaçamento {ESPACAMENTO_S:.0f} s\nÍndice ({mb:.1f} MB, parser v{PARSER_VERSAO}): {cobertura(con)}\nPor seção:\n{por_secao}\n"
            + (f"⚠ Edições INCOMPLETAS dentro do intervalo coberto: {', '.join(buracos)} — sincronize antes de confiar em zero resultado.\n" if buracos else "")
            + f"Grafo de citações: {n_cit} arestas ({n_proc_cit} processos do TJSE citados)\n"
            + f"Recibos de inteiro teor: {n_rec}\nIncidentes:\n{inc}\n"
            f"Modo: {'híbrido — complementos declarados: ' + ', '.join(COMPLEMENTOS) if COMPLEMENTOS else 'autônomo (TJSE_COMPLEMENTOS vazio)'} · "
            f"User-Agent: {'definido por TJSE_USER_AGENT' if os.environ.get('TJSE_USER_AGENT') else 'padrão (identificado)'}\n"
            f"Fora do alcance: formulário oficial com Cloudflare Turnstile ({URL_FORM_TURNSTILE}) — não é usado nem contornado.")


# --------------------------------------------------------------------------- #
# Registro MCP                                                                 #
# --------------------------------------------------------------------------- #
def _servidor():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("tjse_jurisprudencia")

    @mcp.tool()
    async def sincronizar_boletim_tjse(meses: int = 3, max_requisicoes: int = MAX_REQ_POR_SINCRONIZACAO) -> str:
        """Baixa para o índice local as edições do Boletim Jurídico do TJSE dos últimos `meses` (1-24), da mais
        recente para a mais antiga. ÚNICA ferramenta de busca que gasta rede: 1 requisição pela lista de edições,
        1 por menu de edição e 1 por seção (5 por edição; seção de câmara cível passa de 2 MB). Teto de 14
        requisições por chamada, 6 s entre elas — chame de novo até dizer 'período completo'. Nada é rebaixado."""
        return await sincronizar(meses, max_requisicoes)

    @mcp.tool()
    def buscar_jurisprudencia_tjse(consulta: str | None = None, grupos: list[list[str]] | None = None,
                                   orgao: str | None = None, classe: str | None = None, relator: str | None = None,
                                   numero: str | None = None, por_pagina: int = 10, pagina: int = 1,
                                   data_inicio: str | None = None, data_fim: str | None = None,
                                   ordenacao: str = "relevantes", exato: bool = False, em: str = "tudo",
                                   cita: str | None = None) -> str:
        """Busca acórdãos de 2º grau do TJSE no ÍNDICE LOCAL do Boletim Jurídico (zero rede). Sem acento e sem caixa.
        `grupos`=[["dano moral"],["negativação","inscrição indevida"]] → E entre grupos, OU dentro; termo com `$`
        no fim é radical (`consign$`). `consulta` livre: palavras e "frases" em E (operador em caixa alta é recusado).
        Cada termo casa também no outro número (dano moral ↔ danos morais); `exato=true` desliga.
        Filtros: `orgao` (ex. "1ª Câmara Cível"), `classe`, `relator`, `numero` (processo de 12 dígitos ou acórdão de 9),
        `data_inicio`/`data_fim` (dd/mm/aaaa — data de PUBLICAÇÃO do Boletim; o julgamento é do mês anterior).
        `ordenacao`: relevantes (bm25, padrão) | recentes | antigos.
        `em` busca só numa parte da ementa estruturada (padrão CNJ, ~2/3 dos acórdãos): `questao` (a pergunta que o
        tribunal se põe), `tese` (a tese de julgamento), `razoes`, `caso`, `dispositivo`, `cabecalho` — vale combinar
        ("questao,tese"). Quem não segue o padrão tem tudo em `cabecalho`, então buscar por campo não perde acórdão.
        `cita` filtra pelo que o acórdão CITA: "Tema 1061", "Súmula 479/STJ", "IRDR 15" ou nº de processo do TJSE.
        Cobre só as edições sincronizadas (a saída diz quais) e NÃO cobre Turmas Recursais nem monocráticas: zero
        resultado aqui nunca é 'não localizado no TJSE'. Resultado é 'só ementa/índice' até `obter_inteiro_teor_tjse`."""
        return buscar(consulta, grupos, orgao, classe, relator, numero, por_pagina, pagina, data_inicio, data_fim,
                      ordenacao, exato, em, cita)

    @mcp.tool()
    async def obter_inteiro_teor_tjse(numero_acordao: str, numero_processo: str | None = None,
                                      com_partes: bool = False, max_caracteres: int = 60000) -> str:
        """Inteiro teor (ementa em caixa normal, fecho, relatório, voto) pelo link oficial que o Boletim publica.
        1 requisição na primeira vez; depois lê o recibo do disco (0). Órgão julgador e data saem do FECHO
        ('ACORDAM… Tribunal de Justiça do Estado de Sergipe, nesta …'), não do cadastro; a saída traz `orgao_fonte`.
        `numero_processo` só é necessário se o acórdão não estiver no índice local — ou cole em `numero_acordao` a URL
        do inteiro teor (serve para acórdão achado em qualquer outra fonte). Saída cortada = 'lido EM PARTE'."""
        return await obter(numero_acordao, numero_processo, com_partes, max_caracteres)

    @mcp.tool()
    async def verificar_citacao_tjse(numero_acordao: str, trecho: str, numero_processo: str | None = None) -> str:
        """Confere se `trecho` aparece LITERALMENTE no inteiro teor (palavra inteira, sem acento/caixa; `[...]` separa
        fragmentos que devem vir em ordem). Obrigatório antes de qualquer aspas — a ementa do Boletim é caixa alta e
        não serve de fonte literal. Mínimo de 4 palavras. ✅ pode vir com alertas — TRANSCRIÇÃO (trecho de outro tribunal
        copiado no voto), VOTO DIVERGENTE (pode ser o voto vencido), ALEGAÇÃO DA PARTE (relatório narrando o que a parte
        sustenta), ENTRE ASPAS (o tribunal citando alguém), NEGAÇÃO (recorte que inverte o julgado): cada um muda A QUEM
        a frase pode ser atribuída. Falha de rede = citação NÃO CONFERIDA, nunca ❌."""
        return await verificar(numero_acordao, trecho, numero_processo)

    @mcp.tool()
    def mapa_de_citacoes_tjse(referencia: str | None = None, limite: int = 15) -> str:
        """Grafo de citações do índice, montado do campo "Jurisprudência relevante citada" das ementas (zero rede).
        Sem `referencia`: os precedentes qualificados mais citados e os acórdãos do próprio TJSE que as câmaras mais
        reusam — inclusive ANTERIORES ao período sincronizado, que a busca não alcança. Com `referencia` ("Tema 1061",
        "Súmula 479/STJ", "IRDR 15" ou nº de processo do TJSE): quais acórdãos do índice citam aquilo."""
        return mapa_citacoes(referencia, limite)

    @mcp.tool()
    def diagnostico_tjse() -> str:
        """Estado do disjuntor, consumo de requisições, cobertura do índice local e incidentes. Sempre 0 requisições."""
        return diagnostico()

    return mcp


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        import selftest_tjse

        sys.exit(selftest_tjse.main(online="--online" in sys.argv))
    _servidor().run()
