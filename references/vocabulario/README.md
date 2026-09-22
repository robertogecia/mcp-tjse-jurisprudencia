# Dicionário de sinônimos jurídicos do corpus TJSE

## O que é

`sinonimos.json` — 16 conceitos, 119 termos, extraídos do próprio corpus (nunca inventados):
os 6 conceitos das consultas do gabarito (`harness/gold.json`) mais 10 conceitos gerais
frequentes no boletim (dano moral, prescrição, honorários, tutela de urgência, juros e
correção, cerceamento de defesa, responsabilidade bancária, obrigação de fazer,
gratuidade de justiça, precedente qualificado/repetitivo).

Cada termo tem `origem` (`semente` = já estava no grupo original do harness;
`coocorrencia` = achado minerando o corpus; `flexao` = variação de gênero/número que o
motor não cobre sozinho; `sigla` = abreviação corrente) e `exemplos` com 1-2 números de
acórdão **verificados** (script de conferência rodado duas vezes — a primeira bateu numa
cópia do banco que tinha sido feita a meio de uma escrita concorrente, ver "Nota sobre o
banco" abaixo — a segunda, contra a cópia correta, fechou 119/119 sem problema).

## Método

1. Li `harness/medicao-2026-09-21.md`, que lista os essenciais perdidos com a ementa
   cortada e a causa atribuída. Isso deu o primeiro lote de termos, todos com acórdão de
   origem já apontado pelo harness (ex.: "hipervulnerável", "RCC" em vez de "RMC",
   "biometria facial", "SCR", "avalista"/"cédula de crédito bancário", "menor impúbere",
   "infante", "terreno de marinha"/"aforamento").
2. Para cada conceito, rodei `mine.py` (script de mineração, não faz parte da entrega
   formal — fica só citado aqui para reprodutibilidade): pega o conjunto de acórdãos que
   contêm os termos-semente do conceito e mede, para cada termo candidato, a frequência
   dentro desse conjunto contra a frequência geral do corpus (via `fts_vocab`, quando o
   termo é uma palavra única) ou contra uma varredura direta do texto (quando é uma
   expressão de duas ou mais palavras, que `fts_vocab` não tokeniza como unidade).
3. Descartei candidatos que a mineração mostrou não existirem no corpus — ficou registrado
   como "nota" dentro do próprio `sinonimos.json` em vez de simplesmente omitir: em
   `idoso_analfabeto_bancario`, "iletrado" tem zero ocorrências (doc_geral=0, no_alvo=0);
   em `responsabilidade_civil_estado`, "omissão do poder público" como frase fixa também
   não ocorre — o tribunal usa "omissão" solta junto de um substantivo concreto.

## Medição (`medir_vocab.py`)

Não toca em `harness/gold.json` nem em `harness/medir.py` — só os lê. Reproduz os grupos
de sinônimos **originais** do harness (porque `harness/medir.py` não os expõe como
função/constante importável e a regra do exercício proíbe tratar `harness/` como
dependência) e gera uma segunda versão **enriquecida**, que só ACRESCENTA termos do
dicionário a um dos três grupos de cada consulta — nunca remove nada do gabarito. Roda as
duas formas contra `s.buscar(grupos=...)` e mede recall@10, recall@50 e recall total dos
itens `essencial`, exatamente como o harness original.

**Nota sobre o banco**: a cópia deste corpus está VIVA — outra sessão está sincronizando o
Boletim Jurídico em paralelo (regra do enunciado avisou disso). A primeira cópia que fiz
pegou o banco a meio de uma escrita e ficou com as tabelas `secoes`/`edicoes` vazias
(a`acordaos` e `campos` ficaram intactos, mas o servidor lê `secoes`/`edicoes` para decidir
se o índice está "vazio" e recusou buscar). Refiz a cópia; a segunda ficou consistente
(17.460 acórdãos, 6 edições — mais que os 8.974 originais do enunciado, porque o banco
cresceu entre o começo e o fim desta sessão). Os números abaixo são medidos nesse segundo
snapshot, congelado por mim em `/tmp/vocab` só para esta medição — por isso não batem
exatamente com `harness/medicao-2026-09-21.md` (que foi gerado num momento diferente do
mesmo banco vivo). A comparação original-vs-enriquecido é válida porque as duas rodam
contra o MESMO snapshot congelado.

## Resultado (ver tabela completa em `medicao-vocabulario.md`)

| Consulta | recall@10 antes→depois | recall@50 antes→depois | recall total antes→depois | termos no grupo (antes→depois) |
|---|---|---|---|---|
| t1_bancario_idoso_analfabeto | 6%→6% | 33%→28% | 44%→56% | 5→14 |
| t2_plano_saude_autismo | 7%→20% | 40%→47% | 80%→80% | 3→10 |
| t3_cartao_consignado_rmc | 0%→6% | 11%→11% | 39%→33% | 5→12 |
| t4_negativacao_dano_moral | 6%→0% | 11%→28% | 50%→56% | 6→12 |
| t5_responsabilidade_civil_estado | 36%→29% | 79%→86% | 79%→86% | 6→15 |
| t6_usucapiao | 27%→27% | 53%→53% | 53%→53% | 2→11 |

## Onde NÃO houve ganho, e por quê

- **t6_usucapiao**: recall idêntico em TODAS as três colunas, apesar de ter quase
  sextuplicado o vocabulário do grupo (2→11 termos). Motivo: a consulta usa grupos
  E-entre-si (semente "usucapião" já está no grupo mais amplo, que praticamente não filtra
  nada — 118 dos 17.460 acórdãos já casam com ele); o gargalo real está nos outros dois
  grupos ("posse mansa e pacífica"/"animus domini" e a lista de subtipos de usucapião) e
  na ordenação por relevância, não no vocabulário do grupo que enriquecemos. Acrescentar
  sinônimo a um grupo que já não é o gargalo não move a agulha — é um resultado honesto,
  não um erro do dicionário.
- **t3_cartao_consignado_rmc**: recall total PIOROU (39%→33%), embora recall@10 tenha
  melhorado (0%→6%). Ao encher o grupo "cartão/RMC/RCC" com termos como "biometria
  facial" e "termo de consentimento", o motor (FTS5 BM25) redistribuiu a pontuação de
  relevância e empurrou para fora da janela paginada (200 resultados) alguns essenciais
  que antes apareciam por coincidência de outro grupo — sinal de que esses termos, embora
  corretos como vocabulário, são ambíguos demais dentro do universo de acórdãos bancários
  do TJSE (aparecem em muitos casos de cartão consignado que NÃO são o padrão RMC/RCC do
  gabarito) e por isso diluem em vez de concentrar.
- **t4_negativacao_dano_moral**: recall@10 também piorou (6%→0%), mesmo com recall@50 e
  total subindo — mais um sinal de que o dicionário aqui ajuda a achar (recall maior numa
  janela mais larga) mas piora a precisão no topo. Termos como "SCR" e "quantum
  indenizatório" são corretos e ligados ao conceito, mas "quantum indenizatório" aparece
  em ~24% de TODAS as ementas do corpus (é vocabulário de qualquer condenação, não
  específico de negativação) — por isso ele enche o topo de resultados genéricos de dano
  moral que não são sobre negativação.
- **Conceitos gerais fora do gold** (dano_moral_geral, prescricao, honorarios,
  tutela_urgencia, juros_correcao, cerceamento_defesa, responsabilidade_civil_bancaria,
  obrigacao_de_fazer, gratuidade_justica, precedente_qualificado_repetitivo): não entraram
  na medição de recall porque o gabarito não tem consultas para eles — ficam disponíveis
  no dicionário para uso direto em buscas futuras do escritório, mas sem medição própria
  (seria preciso um gold.json próprio para cada um, fora do escopo desta tarefa).

## Onde houve ganho real

- **t5_responsabilidade_civil_estado**: recall total 79%→86% e recall@50 79%→86%, com
  termos como "detento"/"suicídio"/"abordagem policial"/"erro médico"/"lixão" — todos
  vieram diretamente da lista de perdidos do harness, cobrindo o padrão "mesmo pedido
  (indenização contra o Estado), fato completamente diferente" que é exatamente o tipo de
  lacuna que sinônimo de conceito (e não de palavra) resolve.
- **t2_plano_saude_autismo**: recall@10 quase triplicou (7%→20%) com "menor impúbere",
  "infante", "autogestão" e "cerceamento de defesa" — termos que capturam o mesmo caso
  fático descrito com vocabulário processual ou etário diferente do óbvio ("autismo/TEA").
- **t1** e **t4**: ganho no recall total (44%→56% e 50%→56%) mas com o alerta de precisão
  no topo já registrado acima — ganho real, mas com contrapartida.

## Arquivos

- `sinonimos.json` — o dicionário.
- `medir_vocab.py` — mede antes/depois contra o gabarito, sem tocar `harness/`.
- `medicao-vocabulario.md` — tabela completa gerada pelo script, com a lista nominal dos
  essenciais que ainda ficam de fora mesmo depois do enriquecimento.
- `_resultado_vocab.json` — saída bruta da medição (para reprocessar sem rodar de novo).
