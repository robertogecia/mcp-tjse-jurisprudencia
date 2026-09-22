# Histórico

- **(22/09/2026)** — repositório tornado **PÚBLICO** por decisão do Roberto. `INSTALAR.md` reescrito do zero para
  quem nunca usou Terminal: explica o que é o Terminal e como abri-lo, como instalar Python e Git com cliques (não
  só comando), e deixa explícito, logo no início, que o projeto **baixa julgados de verdade** para o computador
  (não é busca "ao vivo") e **quanto espaço em disco reservar** — medido: ~80 MB por edição/mês do Boletim, ~1 GB
  para um ano completo, recomendação de 2 GB livres. README também aponta para o guia didático antes do resumo
  técnico. Nenhuma mudança de código.

- **v0.8.1 (22/09/2026)** — nova ferramenta `importar_pacote_tjse`: reconstrói o índice inteiro a partir só do
  HTML bruto de `base/secoes/` — zero rede, mesmo com o banco vazio — para quem recebe o pacote de outra pessoa em
  vez de sincronizar do zero (economiza ~90 requisições ao portal para um ano de Boletim). Rótulo e data da edição
  são lidos da própria página ("Boletim n. X de DIA de MÊS de ANO"); código de seção sem nome conhecido é ignorado e
  avisado, nunca inventado; seção sem a marca de fim ainda é importada, com aviso. Testado ponta a ponta contra o
  pacote real (`base-secoes-tjse-2026-09-22.tar.gz`, 77 MB, asset do release): reconstrói os mesmos 38.283 acórdãos
  em 11 edições, sem lacuna. Conferido antes de publicar: as ementas não trazem nome de parte (decisão judicial não é
  protegida por direito autoral, Lei 9.610/98 art. 8º, IV). 222 verificações.

- **v0.8.0 (22/09/2026)** — preparado para instalação por terceiros, no molde do pacote do TJRO:
  **[INSTALAR.md](INSTALAR.md)** passo a passo (requisitos, venv, ligação ao Claude Code e Desktop, montagem do
  índice, o que NÃO é coberto, como atualizar); **crédito de autoria** uma vez por processo no fim da primeira
  resposta; e **aviso de versão nova** — uma consulta a `releases/latest` deste repositório, em thread de fundo na
  subida do servidor, que nunca atrasa resposta alguma e cai em silêncio sem rede, com erro, com repositório privado
  (404) ou passados 2 s. O endereço mostrado é FIXO, nunca vem do corpo da resposta da API; nada da pesquisa ou do
  caso sai daqui. Desliga com `TJSE_MCP_SEM_AVISO_ATUALIZACAO=1`. 216 verificações.

- **v0.7.5 (22/09/2026)** — índice completo pela primeira vez: **38.283 acórdãos** em 11 edições (30/10/2025 a
  31/08/2026), sem aviso de lacuna. A ed. 159 ficava eternamente incompleta porque é de 28/11/2025 e a janela padrão
  de sincronização é de 3 meses — nenhuma chamada padrão a alcançaria. Correções: (a) `VERSAO` ficara em "0.7.3" no
  commit da v0.7.4, e o rótulo vaza para o User-Agent e para os recibos; (b) a sincronização imprimia "todas as
  edições estão completas" e "⚠ ed. 159 incompleta" no MESMO texto, porque o resumo descontava as seções que voltaram
  sem acórdão e o aviso do índice não; (c) **timeout de rede deixou de pausar o servidor por 30 min** — com seções de
  câmara cível acima de 2 MB o timeout é evento esperado, e a pausa deixava o advogado sem nem conferir citação já em
  disco; só recusa do portal (403/429/desafio) arma o disjuntor; (d) **escada de ritmo adaptativa** — recusa do portal
  aperta um degrau (6 s/20 → 12 s/10 → 30 s/6 → 60 s/3), 100 consultas limpas afrouxam, e o diagnóstico mostra o
  degrau corrente; (e) docstring da busca (14 parâmetros) reescrita em `Args:`/`Returns:`. (c), (d) e (e) vieram da
  comparação linha a linha com `servidor_trf1.py`, feita por agente Opus; o relatório com a mão inversa — o que o
  TRF1 deve adotar do TJSE — está em `~/MCP/trf1-jurisprudencia/references/correcoes-determinadas-2026-09-22.md`.
  **Rejeitado por medição:** contar resultado por julgamento em vez de por documento (40 processos com mais de um
  acórdão em 38.283, 0,1%, e agrupar esconderia o resultado dos embargos). 208 verificações.

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

- **v0.6.0 (21/09/2026)** — o que vale portar do servidor do TJRO, lido de verdade (não só pelo nome das funções):
  **panorama** de TODAS as ementas que casam (não só da página; o índice é local): resultado declarado
  (desprovido / provido / parcialmente provido / não conhecido / sem resultado identificável — só quando um lado é
  inequívoco), por órgão, por classe, **âncoras** (súmula, tema, IRDR, IAC citados; o número de súmula leva a origem
  quando o texto a diz, porque "Súmula 7" do STJ não é a do TJSE) e **vocabulário** que distingue as ementas do resto do
  índice (fts5vocab, lift), como pista para novos grupos de sinônimos. Medido em 8.974 ementas: 87 % têm resultado
  inequívoco; "não conhecido" foi apertado (sujeito = o recurso) porque "não conhecimento" de um argumento isolado
  o disparava. **Busca que zera** diz qual grupo/termo zera e o que devolveria sem cada um. **Outros acórdãos do mesmo
  processo** (embargos) são avisados na busca e no inteiro teor. **Recibo de custódia**: o recibo agora traz `id_documento`,
  `nr_processo`, `tribunal` e `texto` — o formato que verificadores de ficha esperam — e recibos antigos migram sem rede;
  `TJSE_DIR_RECIBOS` escolhe a pasta.
  Deliberadamente NÃO portado: cache de 5 min (a busca é local), disjuntor adaptativo com escada (o do TJSE não foi
  bloqueado e limite sem medição é limite inventado), filtros de assunto/tipo/grau (o Boletim não os tem).

- **v0.6.1 (21/09/2026)** — o recibo passa a levar `texto_transcrito` e `texto_divergente` (texto normalizado): quem
  lê o recibo depois — um lint de citações, por exemplo — não teria como saber que parte do voto é palavra do próprio
  tribunal, porque um trecho copiado de outro julgado está literalmente no inteiro teor. Recibo antigo migra sozinho,
  sem rede, na primeira leitura. Serviu para fechar, na `peticao-rg`, o caso em que o lint aprovava como palavra do
  TJSE um fecho do TJCE transcrito no voto.

- **v0.6.2 (21/09/2026)** — achado no PRIMEIRO uso real de pesquisa (caso de contratação bancária por idoso): o fecho
  escreve o órgão por extenso tanto quanto em algarismo ("acordam os integrantes do Grupo 5 da **Primeira** Câmara
  Cível"), e assim o órgão caía no cadastro e a **data de julgamento saía vazia** — ela é lida na janela do fecho.
  `norm_orgao()` passa o ordinal por extenso a algarismo. Os recibos já gravados se atualizam sozinhos, sem rede,
  quando o parser melhora (antes só migravam se faltasse `texto`); parser que falha não atualiza nem destrói o recibo.

- **v0.7.0 (21/09/2026)** — as duas capacidades que a busca por palavra não dá sozinha, ambas medidas sobre as 8.974
  ementas do índice e sem nenhuma requisição nova ao tribunal:
  **(1) Ementa estruturada em campos.** 68–69 % dos acórdãos seguem o padrão CNJ; `campos_da_ementa()` separa
  cabeçalho, caso, questão, razões, dispositivo, tese, legislação e jurisprudência citada. O Boletim cola o conteúdo
  no rótulo de três formas distintas ("EXAME:RECURSO", "EXAME1. AGRAVO", "EXAMEAGRAVO"), e o numeral romano não é
  confiável (há "II. RAZÕES DE DECIDIR" e "III. DISPOSITIVO"): casa-se pelo nome da seção, com prioridade para as
  ocorrências que têm numeral. Busca nova: `em="questao,tese"` — na medição, a mesma consulta caiu de 55 para 5
  resultados, todos no ponto.
  **(2) Grafo de citações.** 7.271 arestas tiradas do campo "Jurisprudência relevante citada": 177 acórdãos aplicam o
  Tema 1.061, 371 o Tema 1.150. E 1.566 processos do próprio TJSE citados que estão FORA do índice — o grafo vê o que
  a busca não alcança. Filtro `cita=` na busca, ferramenta `mapa_de_citacoes_tjse`, e autoridade interna ("citado por
  N acórdãos deste índice") na linha de cada resultado. Achado do próprio teste: "Súmula 297" e "Súmula 297/STJ" eram
  duas chaves para a mesma súmula, contada em dobro; o tribunal agora é reconhecido antes ou depois do número.
  Reindexação completa dos 8.974 acórdãos a partir do HTML bruto em disco: 6,6 segundos, zero rede.

- **v0.7.1 (21/09/2026)** — harness de busca (gold set de 6 consultas e 73 acórdãos essenciais, montado por um agente
  às cegas, varrendo o banco sem usar a busca) e a correção que ele exigiu. **A pergunta escrita como se fala dava
  0 % de recall nas 6 consultas**: a consulta livre exigia TODAS as palavras, artigo e preposição inclusive. Agora as
  palavras soltas combinam por OU (o ranking ordena), "entre aspas" e `grupos` é que são obrigatórios, e as palavras
  de praxe do jargão não entram. Medido de novo com o mesmo gabarito: 43 %, 67 %, 72 %, 78 %, 93 % e 100 % — em quatro
  das seis, a pergunta em português passou à frente dos grupos de sinônimos montados à mão.
  O harness também mostrou o que NÃO vale: a busca por campo da v0.7.0 não recupera nenhum acórdão perdido (ela dá
  precisão, não alcance — a FTS já lê a ementa inteira), e a busca semântica resolveria só 3 dos 40 casos perdidos,
  contra 37 que sinônimos melhores alcançam. **Embeddings ficam fora por decisão medida, não por palpite.**
  Fica aberto: `recall@10` ainda é baixo (6–13 %) porque o OU traz muito e o ranking não premia quem casa mais termos.

- **v0.7.2 (21/09/2026)** — ranking e custo, medidos com o harness antes e depois. Com palavras soltas em OU, um
  acórdão que casava UM termo periférico disputava o topo com outro que casava todos: a ordenação passa a premiar
  **quantos termos da consulta o acórdão casa**, e cada resultado mostra "casa 5/6 termos". `recall@50` médio subiu
  de 37 % para 49 %; `recall@10` de 6 % para 17 % na consulta bancária e de 0 % para 7 % na de responsabilidade do
  Estado. (O "recall total" do medidor é recall@200: onde ele oscila, é redistribuição dentro do teto, não perda.)
  A busca ficou 3,7× mais rápida no caminho novo (2,8 s → 0,75 s): o gargalo não era a consulta, era o panorama
  normalizando milhões de caracteres — `sem_acento` passou a usar tabela de tradução, cada ementa é normalizada uma
  vez só, e a amostra do panorama caiu de 3.000 para as 800 mais relevantes, que dizem o mesmo sobre a distribuição.

- **v0.7.3 (21/09/2026)** — terceiro red team, sobre o que entrou hoje (`references/red-team-v07/`): 3 ALTA, 5 MÉDIA,
  2 BAIXA, todos corrigidos com regressão (`RTC*`, selftest em 196 verificações).
  O pior era meu: **`em="questao,tese"` perdia os acórdãos sem ementa estruturada, e a documentação garantia que não
  perdia**. Agora o `cabecalho` — que toda ementa tem — entra junto com peso baixo: na medição, 35 → 108 documentos,
  com o acórdão sem estrutura incluído. Também: "Súmula 297" e "Súmula 297/STJ" eram chaves distintas ENTRE ementas
  (a dedup só valia dentro de uma), e `cita=` via metade do grafo — 60 chaves partidas, uma delas 21 contra 248;
  rótulo colado na palavra anterior ("COMPETÊNCIAIII. RAZÕES DE DECIDIR") fazia o campo anterior engolir a seção,
  em 99 acórdãos; "4. DISPOSITIVO" em algarismo arábico era descartado, em 43; `em=" "` derrubava a busca; `exato`
  não obrigava nada e as aspas aceitavam flexão; **`_VAZIAS` descartava "agravo", "recurso", "direito" e "não" em
  silêncio** — "agravo de instrumento" virava busca por "instrumento", e "não" muda o sentido jurídico; e o total do
  OU era anunciado sem dizer quantos casam todos os termos, o que vira jurimetria falsa numa peça.
  **Lição de método**: ao remedir, o recall caiu e quase dei como regressão — era o corpus, que dobrou de 8.974 para
  17.460 no mesmo intervalo. Rodando as duas versões contra o MESMO snapshot, os números são idênticos. Mudar duas
  variáveis ao mesmo tempo quase produziu a conclusão errada.
- **Dicionário de sinônimos (`references/vocabulario/`, 16 conceitos, 119 termos)** — construído do próprio corpus e
  medido: NÃO foi integrado como expansão automática. O ganho é misto — recall total sobe em 3 consultas (t5 79→86 %)
  e o `recall@10` quase triplica numa (t2 7→20 %), mas cai em outras duas, porque termo genérico ("quantum
  indenizatório", em 24 % do corpus) sobe ruído ao topo. Fica como REFERÊNCIA para quem monta os `grupos`, que é
  onde a escolha é informada, e não como expansão cega.

- **v0.7.4 (21/09/2026)** — o detector de anomalias da sincronização acusou relator vazio nas edições novas, e eram
  duas grafias do próprio Boletim que o parser não reconhecia: `RELATOR(A) ORIGINÁRIO(A)` (parênteses colados) e
  `RELATOR) ORIGINÁRIA` (o "(A" se perdeu e sobrou o parêntese). De **198 acórdãos sem relator para 1**, em 25.176 —
  os 196 restantes são "VAGA DE DESEMBARGADOR", marcador administrativo já anotado como tal. Índice em 25.176
  acórdãos, 8 edições, janeiro a agosto de 2026.

- **Cobertura e uma limitação medida (21/09/2026, fim do dia).** Índice em **29.450 acórdãos, 10 edições
  (nov/2025 a ago/2026)**, sete delas completas. Ao remedir o harness com esse corpus, o recall@50 caiu à metade do
  que era com 8.974 acórdãos — **com o código idêntico**, o que já havia sido provado rodando duas versões contra o
  mesmo snapshot. Não é regressão: é a busca ficando mais difícil conforme o índice cresce, e o número absoluto
  deixando de ser comparável entre corpora. O medidor passou a registrar o tamanho do corpus em toda medição.
  **Consequência prática**: quanto maior o índice, mais o ranking importa — é onde estão os próximos ganhos
  (os sinônimos de `references/vocabulario/` e o grafo, usados ao montar `grupos`, e não como expansão cega).
