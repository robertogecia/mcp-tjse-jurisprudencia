# Red team — `lint_citacoes.py` (mudança TJSE de 21/09/2026)

Alvo: `~/.claude/skills/peticao-rg/scripts/lint_citacoes.py` (1.460 linhas).
Baseline: `python3 lint_citacoes.py --selftest` → `selftest OK (48 casos)`. Nada foi editado; nenhuma
rede; todos os recibos em `tempfile.mkdtemp()`.
Scripts de prova nesta mesma pasta (`L1_…py` … `L6_…py`), rodam com `python3 <script>`.

---

## L1 — ALTA — `norm` do servidor e `norm_literal` do lint divergem em "nº <dígito>": trecho transcrito de outro tribunal é APROVADO em silêncio
**Prova:** `L1_norm_divergente.py` (usa o `norm`/`faixas_transcritas` reais do `servidor_tjse.py`).
```
DIFERE 'Súmula nº 7 do STJ' | servidor+lint: 'sumula n 7 do stj' | lint: 'sumula no 7 do stj'

texto_transcrito gravado pelo servidor:
 'precedentes: apelacao civel. incide a sumula n 7 do stj, que veda o reexame de provas em recurso
  especial. (tj-mg - apelacao civel 1.0000.24.000001-1/001, rel. des. fulano, ...)'

trecho citado (é palavra do TJMG/STJ, não do TJSE): Incide a Súmula nº 7 do STJ, que veda o reexame ...
resultado do lint: SILÊNCIO — APROVOU

mesmo trecho SEM o 'nº' (controle): veda o reexame de provas em recurso especial
resultado do lint: [('aviso', ... 'é trecho que o voto TRANSCREVE de outro julgado/tribunal ...')]
```
**Causa:** `servidor_tjse.py:185` aplica `re.sub(r"\bn[o.°]\s*(?=\d)", "n ", s)` antes de gravar
`texto_transcrito`/`texto_divergente`; o lint compara com `norm_literal` (`lint_citacoes.py:107`), que
não tem essa regra e produz `no 7`. O `texto` bruto do recibo não passou pela regra, então o trecho
**está** em `base` (`:831`) e o `ns in marcado[rot]` falha → o lint aprova. O aviso só sobrevive
quando o trecho citado por acaso não contém "nº/n./n° + dígito" — e citação de acórdão contém quase
sempre (súmula, artigo, tema, processo).
**Correção (`conferir_recibo`, antes de `marcado`):** aplicar a MESMA regra do servidor ao trecho
antes de comparar, ou comparar por posição em vez de substring:
```python
_RE_N = re.compile(r"\bn[o.°]?\s*(?=\d)")
def _norm_recibo(s): return _RE_N.sub("n ", norm_literal(s))
# usar _norm_recibo(seg) e _norm_recibo(r.get(campo)) nas comparações de marcado
```
Melhor ainda: o servidor gravar `texto_transcrito` como offsets (a,b) sobre `texto` bruto, e o lint
não depender de duas normalizações distintas.

---

## L2 — ALTA — trecho que atravessa a fronteira da faixa transcrita não dispara nada
**Prova:** `L2_fronteira_faixa.py`
```
A) todo dentro da faixa (controle)                      -> aviso TRANSCREVE  (ok)
B) começa dentro, termina fora (atravessa a atribuição)  -> SILÊNCIO — APROVOU
C) [...] com um fragmento dentro e outro fora            -> aviso TRANSCREVE  (ok)
D) começa uma palavra antes da abertura do bloco         -> SILÊNCIO — APROVOU
```
**Causa:** `lint_citacoes.py:833` testa `ns in marcado[rot]` — substring INTEIRA dentro da faixa. Um
segmento que apenas se sobrepõe à faixa (caso D: basta a citação começar em "Sergipe. Precedentes:")
cai fora e, como está em `base`, é aprovado sem aviso. O caso C só funciona porque `[...]` já quebrou
o trecho em segmentos.
**Correção:** trocar o teste de pertencimento por INTERSECÇÃO — localizar `ns` em `base` por posição e
comparar a faixa com os offsets marcados (o servidor já tem as faixas; basta gravá-las como
`faixas_transcritas: [[a,b],…]` em offsets do `texto` bruto e o lint verificar sobreposição > 0).

---

## L3 — ALTA — recibo com campo não-string derruba o lint inteiro (exceção não tratada)
**Prova:** `L3_recibo_corrompido.py`
```
texto_transcrito = lista  -> EXCEÇÃO NÃO TRATADA: AttributeError 'list' object has no attribute 'replace'
texto_transcrito = número -> EXCEÇÃO NÃO TRATADA: AttributeError 'int' ...
texto_divergente = dict   -> EXCEÇÃO NÃO TRATADA: AttributeError 'dict' ...
texto = número            -> EXCEÇÃO NÃO TRATADA: AttributeError 'int' ...
lint() completo -> EXCEÇÃO NÃO TRATADA: AttributeError 'list' object has no attribute 'replace'
```
A exceção sobe por `lint()` (`:1048`) e mata a geração da peça — a trava final vira um crash, não um
relatório. `_ler_recibo` (`:775`) só valida que `texto` é truthy, nunca que é `str`.
**Causa:** `lint_citacoes.py:107` (`norm_literal` assume `str`), consumido em `:784`, `:810`, `:822`.
**Correção:**
```python
def norm_literal(s):
    s = s if isinstance(s, str) else ("" if s is None else str(s))
    ...
```
e, em `_ler_recibo`, `return r if isinstance(r, dict) and isinstance(r.get("texto"), str) and r["texto"] else None`.

---

## L4 — ALTA — ficha sem o campo `tribunal` nunca é conferida contra recibo, em silêncio
**Prova:** `L4_silencios.py`, seção E
```
com identidade ('tjse', ...) mas ficha sem `tribunal` -> NENHUM ERRO
controle, mesma ficha com `tribunal`  -> ['... texto NÃO localizado no inteiro teor ...']
```
A mesma ficha, com o mesmo trecho inventado, passa ou trava conforme um campo meramente
descritivo esteja preenchido. Fichas antigas do vault não trazem `tribunal` (o próprio selftest usa
`f_ai`/`ok` sem ele), então a cadeia de custódia inteira é opcional na prática.
**Causa:** `lint_citacoes.py:791-792` — `trib` sai só de `ler_campo(ficha.dados, "tribunal")`.
**Correção:** derivar o tribunal também da identidade da citação/ficha (classe `tjse` → TJSE; CNJ com
`.8.22.` → TJRO, como `_eh_tjro` já faz em `:653`) e, se nem assim der, emitir aviso de ficha sem
tribunal em vez de sair calado.

---

## L5 — ALTA — `n°` (sinal de grau, U+00B0) apaga a citação de TODAS as classes
**Prova:** `L5_extrator_tjse.py`, seção A
```
'REsp n° 1.959.812'        -> []
'Tema n° 1265'             -> []
'Súmula n° 385'            -> []
'acórdão n° 202638463'     -> []
controle com 'nº': [('resp','1959812')] [('tjse','202638463')]
lint completo, citação com n° e SEM ficha:
  Lint de citações: 0 citação(ões), 0 com ficha, 0 sem ficha, 0 inconsistente(s), 0 aviso(s)
```
Citação inventada escrita com `n°` sai da peça sem ficha, sem erro e sem aviso. `n°` é o que portais,
PJe e colagens de Word produzem a toda hora. O próprio `norm` do servidor trata `[o.°]`; o lint não.
**Causa:** `lint_citacoes.py:172` — `_NUM = r"(?:n\.?[oº]?\.?|num\.?|numero)?"`, sem `°`; e
`_norm_char` (`:88`) não decompõe `°` (ao contrário de `º`).
**Correção:** `_NUM = r"(?:n\.?[oº°]?\.?|num\.?|numero)?"` (uma linha), e cobrir também `acórdão:` /
`acórdão de nº` no `_RE_TJSE` (`:226`), hoje perdidos — ver seção B do script.

---

## L6 — ALTA — ficha cuja `chave` traz o nome do tribunal (não "acórdão"/"TJSE") é rejeitada e TRAVA peça correta
**Prova:** `L5_extrator_tjse.py`, seção C
```
texto: [('tjse', '202512345')]                       # "TJMG, acórdão 202512345" vira identidade TJSE
ficha chave 'TJMG 202512345' -> parsear_chave: None
ERROS:  ['citação sem ficha verificada: "acórdão 202512345" (bloco 1, paragrafo, texto)']
avisos: ['ficha 1 ("TJMG 202512345"): chave não reconhecida ...']
(mesma ficha com chave 'acórdão 202512345'): sem erro
```
O texto é capturado (`_RE_TJSE` aceita qualquer acórdão de 9 dígitos precedido de "acórdão"), mas a
ficha correspondente, escrita como o advogado escreve, não casa — a peça trava com "citação sem
ficha" tendo ficha verificada. Vale para TJSE também: `chave: "Acórdão TJSE nº 202638463"` funciona,
`chave: "TJSE, 202638463"` não (falta a palavra colada ao número).
**Causa:** `_RE_TJSE` (`:226`) exige `acordao|tjse` imediatamente antes do número; `parsear_chave`
(`:302`) reusa o mesmo extrator para a chave da ficha, onde o contexto é curto e a sigla de outro
tribunal ("TJMG", "TJPR") não habilita nada.
**Correção:** em `parsear_chave` (só na chave, nunca no corpo da peça), aceitar um número isolado de
9 dígitos começando por 19/20 como `("tjse", dig)` quando a chave não casar com nada, ou trocar
`(?:acordao|tjse)` por `(?:acordao|tj[a-z]{2})` no `_RE_TJSE`.

---

## L7 — MÉDIA — `id_documento` ausente, curto ou lixo: recibo nunca conferido, sem aviso
**Prova:** `L4_silencios.py`, seção A
```
id_documento=None           -> SILÊNCIO
id_documento=''             -> SILÊNCIO
id_documento='20263846'     -> SILÊNCIO      (8 dígitos: erro de digitação)
id_documento='00202638463'  -> SILÊNCIO      (zero à esquerda)
id_documento='lixo'         -> SILÊNCIO
id_documento='202600737656' -> aviso "12 dígitos ... nº do PROCESSO"   (único caso tratado)
```
A mudança de 21/09 criou o aviso certo para o erro de 12 dígitos e deixou todos os outros sem
diagnóstico: a ficha simplesmente não é conferida e a peça sai como se tivesse sido.
**Causa:** `lint_citacoes.py:745-749` (`_ids_da_ficha_tjse` devolve `[]`) + `:806` (`if not ids: return []`).
**Correção:** no ramo `tjse`, quando `id_documento` existir mas não for um acórdão de 9 dígitos
(inclusive vazio/ausente), devolver aviso: `ficha "X": `id_documento` "Y" não é um nº de acórdão do
TJSE (9 dígitos começando pelo ano) — a ficha não foi conferida contra a fonte`.

---

## L8 — MÉDIA — trecho com menos de 4 palavras nunca é conferido contra o recibo
**Prova:** `L4_silencios.py`, seção B
```
'nao cabe indenizacao'              -> SILÊNCIO   (3 palavras: nem conferido nem avisado)
'jamais houve dano moral'           -> erro       (4 palavras: conferido)
'veda aos pais contrair obrigacoes' -> SILÊNCIO   (5 palavras, mas confere de verdade: está no recibo)
```
O piso de 4 palavras (`:829`) é o mesmo do servidor, mas aqui ele é aplicado ao campo literal da
FICHA: uma tese curta ("dano moral in re ipsa", "há responsabilidade objetiva") entra na peça entre
aspas sem nenhuma conferência e sem nenhum aviso.
**Correção:** manter o piso para o veredito de erro, mas avisar: `campo trecho curto demais para
conferência contra o recibo (<4 palavras) — não foi conferido`.

---

## L9 — MÉDIA — ficha TJSE com recibo e SEM nenhum campo literal passa muda
**Prova:** `L4_silencios.py`, seção D — `SILÊNCIO`. A ficha tem recibo, tem id certo, e nada é
conferido porque não há `trecho`/`tese`/`ementa`/`dispositivo`. O bloco `citacao` tem aviso análogo
("ficha sem texto literal", `:1034`); o caminho do recibo não tem.
**Correção:** em `conferir_recibo`, se houver recibo e nenhum `_CAMPOS_LITERAIS` preenchido, devolver
aviso "ficha sem campo literal: o recibo existe, mas nada foi conferido".

---

## L10 — BAIXA — recibo sem `texto` é reportado como "sem recibo"
**Prova:** `L4_silencios.py`, seção C → `sem recibo do MCP TJSE para o id 202699001 ... (reabrir com
obter_inteiro_teor_tjse gera o recibo)`. O recibo existe; o que falta é o conteúdo (parser que falhou,
gravação truncada). A mensagem manda repetir a operação que já foi feita.
**Causa:** `:775-779`, `_ler_recibo` devolve `None` nos dois casos.
**Correção:** distinguir "arquivo ausente" de "recibo sem texto utilizável" na mensagem.

---

## L11 — BAIXA — o aviso de TRANSCRIÇÃO/DIVERGENTE não é restrito ao TJSE
**Prova:** `L6_nao_regressao.py`, última linha do bloco TJRO: um recibo do TJRO ao qual se acrescenta
`texto_transcrito` produz `... não é palavra do TJRO ...`. Hoje é inerte (o MCP do TJRO não grava
esses campos), mas qualquer recibo de terceiro colocado na pasta do TJRO passa a ditar avisos.
Registrado como observação, não como defeito: o comportamento genérico é o desejável se e quando o
MCP do TJRO passar a gravar os campos.

---

## Não regressão de TJRO e STJ — OK
`L6_nao_regressao.py` reproduz os casos 42-45 do selftest e os três casos do STJ com recibos
sintéticos: mensagens idênticas, mesmos níveis.
```
42 ok: True [] []
43 erro: ['... campo trecho: texto NÃO localizado no inteiro teor ... (recibo id 18238575) ...']
44 aviso: ['... não está no documento id 18238575, mas está no id 18238999 do mesmo processo ...']
45 aviso: ['... sem recibo do MCP TJRO para o id 99999999 ... (reabrir com obter_inteiro_teor_tjro ...)']
STJ ok: []
STJ erro: [('erro', '... recibo id 202401318197 ...')]
STJ sem recibo: [('aviso', '... MCP STJ ... obter_acordao_stj ...')]
```

---

## Não reproduzido (procurado e NÃO encontrado)

- **Falso positivo do `_RE_TJSE`**: `202600823569` (12 díg.), `acórdãos 202638463, 202638464 e …`
  (lista), `fls. 199200123`, `acórdão 202638463123`, `acórdão nº 2026.0012.345`, `no acórdão de
  20/06/2026 199512345`, `conforme acórdão, 202638463` — todos devolvem `[]`. O `\b`, o teto de 9
  dígitos e a exigência da palavra colada seguram bem. (`L5_…py` seção A do primeiro lote de testes.)
- **Classe errada por sobreposição**: `REsp 202638463` → `resp`; `ARE 202638463` → `are`; `acórdão no
  RE 202638463` → `re`; `acórdão 0819477-50.2024.8.22.0000` → `cnj`; `Tema 202638463` → nada. A
  ordenação por `(inicio, -tamanho)` e o corte de sobreposição (`:295-300`) não erraram em nenhum caso.
- **"Vizinho" de OUTRO processo** (`_recibos_do_processo`): não consegui produzir. Quando a `chave` da
  ficha não tem `_DIGITOS_PROCESSO[trib]` dígitos, o número vem do próprio recibo, e a comparação é
  igualdade exata de `nr_processo`; chave só com os 12 dígitos do processo é rejeitada antes, por
  `parsear_chave`.
- **Recibo do TJSE com campos novos afetando ficha do TJRO**: não afeta — o roteamento é por
  `tribunal` da ficha e por pasta (`L6_…py`).
- **`id` com máscara** (`2026-38463`, `ACÓRDÃO 202638463`): funciona, confere normalmente.
