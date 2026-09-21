# Histórico

- **v0.1.0 (21/09/2026)** — reconhecimento (Turnstile no formulário oficial; Boletim + `relatorio.wsp` sem desafio), primeira versão.
- **v0.2.0 (21/09/2026)** — o PRIMEIRO uso real pelas tools achou **799 de 1.610 relatores cortados**: o HTML do Boletim é
  irregular (relator em `<div>` próprio, `<font>` aninhado, rótulo colado no nº do recurso). `parse_secao` reescrito por célula
  `<td>` sobre texto limpo. Entraram: HTML bruto de cada seção em `base/secoes/*.html.gz` + `PARSER_VERSAO` (parser corrigido
  reindexa do disco, **zero rede** — já usado 3 vezes), `anomalias_secao`, resposta truncada não indexa, erro interno nunca
  vira "nada encontrado". Da leitura comparada dos irmãos (Sonnet): bm25, filtro por data de publicação, `orgao_fonte`,
  diagnóstico por seção, "próximo passo". Variação singular/plural na busca: a mesma consulta foi de 39 para 95 acórdãos
  (FTS5 não tem stemmer de português; prefixo não resolve "moral→morais"). O Gemini sugeriu `"desconto* indevido*"`:
  testado no SQLite, NÃO funciona (asterisco dentro de aspas é ignorado).
- **v0.3.0 (21/09/2026)** — red team adversarial offline (Opus): 8 ALTA, 13 MÉDIA, 8 BAIXA, todos reproduzidos
  (`references/red-team-2026-09-21.md`, scripts em `references/red-team-scripts/`). Corrigidos com regressão `RT*` no selftest:
  alerta de TRANSCRIÇÃO por pertencimento a faixa (detecção 39 % → 99 %, falso alarme 0 %); órgão do fecho pela posição no
  texto; recibo reconferido (sha256 + nº do acórdão) a cada leitura; seção vazia só é "baixada" se for página real do Boletim;
  negação ampliada; "captcha" numa ementa não pausa mais o servidor; laço infinito com relógio para trás; estado com tipos
  errados e `.lock` sem permissão = fail-closed; última data do fecho; "lido EM PARTE" quando a saída é cortada; dois
  relatores (144 casos reais na ed. 168: originário + substituto); grupo vazio recusado; nº CNJ recusado com explicação;
  "art . 42" do portal confere; republicação guardada e avisada; piso de 4 palavras e vão máximo de 1.500 caracteres no
  `[...]`; promessa honesta sobre partes. **Discordância registrada (achado 5)**: a correção de uma linha faria seção
  legitimamente vazia ser rebaixada para sempre; usou-se critério estrutural (cabeçalho `<h4>Boletim n.`).
  Não corrigido, aceito: achado 29 (ementa com "PROCESSO:" sem link; só estética da busca) e "1.0000 .24.449766-5" (erra para ❌).

- **v0.4.0 (21/09/2026)** — **modo híbrido** e preparo para publicação: saídas neutras quanto a ferramentas de terceiros,
  `TJSE_COMPLEMENTOS`, caminho manual para quem só tem este servidor, URL do inteiro teor aceita como entrada, User-Agent
  identificado por padrão (aceito pelo portal) e `TJSE_USER_AGENT`, fixtures e relatórios anonimizados, skill autônoma e guia de
  agente em `integracoes/`. **Paginação**: o WebIntegrator corta a seção em 1.000 linhas e só a página 1 era lida — perda
  silenciosa de ~35 % nas câmaras cíveis em meses cheios. Denunciada por quatro seções com 995 itens EXATOS; invisível aos dois
  red teams offline, porque a edição de teste cabia numa página. Seção só entra no índice com todas as páginas; retoma do disco.
- **v0.5.0 (21/09/2026)** — segundo red team (Opus, offline, sobre 8.412 acórdãos reais): 10 ALTA, 10 MÉDIA, 7 BAIXA
  (`references/red-team-2026-09-21-b.md`); o parser teve **0 divergências** contra extração independente. Corrigidos com
  regressão `RTB*`: atribuição sem hífen (`(tj-pr 0048…)`), "STJ - REsp…, Rel." sem parênteses, aberturas por rótulo
  ("Precedentes:", "transcrevo", "in verbis"); encadeamento de blocos só com cara de ementa e sem voz própria (detecção 100 %,
  falso alarme 0 % nas janelas medidas); alertas novos **VOTO DIVERGENTE**, **ALEGAÇÃO DA PARTE** e **ENTRE ASPAS**; menu vazio
  não é cacheado; seção sem acórdão nunca é "baixada" (nova tentativa em 7 dias); seção incompleta fica fora do índice;
  detector de desafio olha duas janelas e exige ausência do conteúdo esperado ("código de segurança" aparece em ementa de
  consumidor); parser que não reconhece o cabeçalho **não destrói recibo**; sem trava não há requisição; `.tmp` por processo;
  "VAGA DE DESEMBARGADOR" cede ao substituto (399 casos) ou é anotada (108); rótulo com grafia errada; conexão fechada se a
  reindexação falhar ("database is locked" não manda mais apagar a base); `data_inicio > data_fim`, filtro que zerou,
  ordem anunciada, `max_caracteres` negativo, bm25 sem varrer duas vezes, variantes de plural sem lixo (`pais→pal`),
  `§ 1º`/`nº`/ligaduras. Lição do fixture 03: a relatora **encampou** o voto divergente — por isso o alerta diz "pode ser o
  vencido", nunca "é".
  Aceitos, não corrigidos: doutrina/súmula transcrita sem aspas nem atribuição sai sem alerta; pausa que não consegue ser
  gravada em disco protege só o processo atual (B15); falso alarme em voto próprio de <1.200 caracteres entre duas citações.
