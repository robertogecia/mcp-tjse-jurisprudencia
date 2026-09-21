# Protocolo — Boletim Jurídico de Sergipe e inteiro teor (medido em 21/09/2026)

User-Agent identificado (`tjse-jurisprudencia-mcp/<versão>`) aceito pelo portal em 21/09/2026 (sincronização real de 3 edições).

App WebIntegrator (`.wsp`), Apache 2.4.6, ISO-8859-1, cookies `JSESSIONID`/`cookiesession1` dispensáveis (o POST
de seção respondeu sem sessão). `wi.token` vem vazio no formulário e é aceito vazio.

1. **Lista de edições** — `POST /revista/internet/pesquisar.wsp` com `tmp_origem=`, `tmp.diario.dt_inicio=dd/mm/aaaa`,
   `tmp.diario.dt_fim`, `tmp.diario.cd_caderno=`, `tmp.diario.cd_secao=`, `tmp.diario.pal_chave=`, `wi.token=`,
   `tmp.diario.id_advogado=`. O limite de 30 dias é só do JavaScript (`executarPesq`); o servidor aceitou 1 ano (12 edições).
   Resposta: `onClick="ver('168');"><b>72026</b><br><i>(31 de Agosto de 2026)</i>`. Com `pal_chave`, devolve só as
   (edição, seção) que contêm a palavra — inútil como filtro (seção de câmara tem ~800 ementas) e o conteúdo NÃO vem filtrado.
   Fixture `02`.
2. **Menu da edição** — `GET menu.wsp?tmp.diario.nu_edicao=168&…`: `lastPage("1ª Câmara Cível<!--6-->","&0","javascript:abre('6','168');")`.
   Códigos na ed. 168: 0 composição, 11 abreviaturas, 10 Pleno, 5 Seção Esp. Cível, 6 1ª CC, 7 2ª CC, 8 Criminal.
   ATENÇÃO: os códigos do formulário de pesquisa (`cd_caderno` 7 = 1ª CC) são OUTROS. Lê-se o menu de cada edição. Fixture `05`.
3. **Seção** — `POST principal.wsp` com `tmp.diario.cd_secao`, `tmp.diario.nu_edicao`, `tmp.diario.id_advogado=`,
   `tmp.diario.pal_chave=`. Linhas `<font … font-size: 10pt"><b>Classe</b>` (cabeçalho) e `font-size: 7pt">EMENTA<br />PROCESSO: <a …respnumprocesso…>
   <br />ACÓRDÃO: <a …relatorio.wsp?tmp.numprocesso=…&amp;tmp.numacordao=…><br /><b>AI Nº 05094/2026</b><br /><b>RELATORA ORIGINÁRIA: …</b>`.
   Conteúdo duplicado dentro de `<!-- -->`. Ed. 168: 43 + 2 + 808 + 639 + 118 = 1.610 acórdãos; 1ª CC = 2,2 MB. Fixtures `06`, `07`.
   PDF da edição inteira: `/revista/boletins/168.pdf` (não usado).
3b. **Paginação da seção (achada em 21/09/2026)** — o WebIntegrator corta a seção em **1.000 linhas** (≈995 acórdãos + cabeçalhos
   de classe). Página com continuação traz `<a href="javascript:submitWIGrid('grid.lista_conteudoDiario',1001)" class='nav_go'>` e o
   formulário oculto `wiFormGridNav` (`tmp.diario.cd_secao`, `nu_edicao`, `dc_caderno`, `dc_secao`, `dt_diario`). Página seguinte =
   `POST principal.wsp` com esses campos + `grid.lista_conteudodiario.next=1001` (nome em minúsculas, como faz o `gridnav.js`, cópia em
   `references/gridnav.js.txt`). A classe aberta na página 1 continua na 2 sem repetir o cabeçalho: as páginas se leem juntas.
   Ed. 167: 1ª CC = 1.497 e 2ª CC = 1.528 acórdãos em 2 páginas de ~11 MB. A ed. 168 (808/639) cabia numa página — por isso o teto
   passou despercebido no primeiro dia e por dois red teams offline. Sinal que denunciou: quatro seções com 995 itens EXATOS.
4. **Inteiro teor** — `GET https://www.tjse.jus.br/tjnet/jurisprudencia/relatorio.wsp?tmp.numprocesso=&tmp.numacordao=` (o Boletim
   publica com `http://`; usa-se `https://`). Cabeçalho ACÓRDÃO/RECURSO/PROCESSO/RELATOR, partes, EMENTA, ACÓRDÃO (fecho + "Aracaju/SE, 17 de Julho de 2026."),
   RELATÓRIO, VOTO, votos divergentes. Há JS inline (`carregarTurma`) a remover. Fixtures `03`, `08`.

Fora do alcance, de propósito: `Dgorg/.../consultarJurisprudencia.tjse` (Turnstile; campos mapeados sem submeter: `itTermos`, `nrProc`,
`nrUnico`, `sorTipoDocumento`, `sorCompetencia` 2º grau/Turma Recursal, 9 órgãos julgadores, 113 relatores, botões "na ementa" e "na ementa + voto").
