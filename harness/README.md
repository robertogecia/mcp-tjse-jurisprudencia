# Harness de qualidade de busca — MCP `tjse_jurisprudencia`

Mede recall da busca do índice local do Boletim Jurídico do TJSE contra um
gabarito montado **cego à implementação**: o gabarito (`gold.json`) foi construído
lendo a tabela `acordaos` diretamente com regex em Python (`_explore.py`), nunca
usando `buscar_jurisprudencia_tjse` nem `servidor_tjse.buscar()`. Isso evita que o
gabarito herde os acertos e erros do próprio motor que está sendo avaliado.

## Arquivos

- `_explore.py` — biblioteca de exploração cega do banco (carrega todas as 8.974
  ementas em memória e casa regex Python, ignorando FTS/LIKE do SQLite).
- `_db_index.json` — dump `{acordao: {processo, classe, relator, ementa}}` usado
  para montar justificativas e trechos de ementa no relatório.
- `gold.json` — 6 consultas, cada uma com `pergunta`, `termos_advogado` e a lista
  de acórdãos-alvo (`essencial`/`desejavel`) com justificativa curta.
- `medir.py` — roda `servidor_tjse.buscar()` (o servidor real, sem tocar no seu
  código) contra a CÓPIA do banco em `/tmp/goldtjse`, em duas formas por consulta
  (`consulta` livre e `grupos` de sinônimos), pagina até esgotar ou 200 resultados,
  e calcula recall@10, recall@50 e recall total dos essenciais.
- `medicao-2026-09-21.md` — tabela de resultado, lista nominal dos perdidos com
  trecho de ementa, diagnóstico das causas e a contagem do item 4 (quanto cada
  abordagem de melhoria recuperaria).
- `_resultado_bruto.json` — saída bruta de `medir.py` (para reprocessar o
  diagnóstico sem rodar a busca de novo).

## Como rodar de novo

```bash
# 1. cópia CONSISTENTE do banco (o original pode estar sendo escrito por outra
#    sessão — cp direto de um .db vivo pode copiar um estado inconsistente entre
#    a tabela acordaos e o índice fts; use o backup API do sqlite3, não `cp`):
mkdir -p /tmp/goldtjse/base
~/MCP/tjse-jurisprudencia/.venv/bin/python -c "
import sqlite3
src = sqlite3.connect('file:$HOME/MCP/tjse-jurisprudencia/base/boletim.db?mode=ro', uri=True)
dst = sqlite3.connect('/tmp/goldtjse/base/boletim.db')
src.backup(dst)
"

# 2. medir
~/MCP/tjse-jurisprudencia/.venv/bin/python ~/MCP/tjse-jurisprudencia/harness/medir.py
```

## Achado central (resumo — o corpo está em `medicao-2026-09-21.md`)

1. **`consulta` livre com uma pergunta em português corrente sempre devolve zero.**
   O parser transforma a frase inteira num E lógico de todas as palavras
   (artigos, pronomes, pontuação colada incluídos) — não é falta de vocabulário
   no corpus, é ausência de normalização da entrada. Use sempre `grupos`.
2. Com `grupos` bem montados, o recall varia de 39% a 80% (recall total) entre os
   6 temas — está longe de ser ruim, mas 40 essenciais ficaram de fora, por
   3 causas: vocabulário diferente do sinônimo escolhido (34), flexão de gênero
   que a expansão de plural do servidor não cobre (3, ex. "idosa" vs "idoso") e
   fato atípico dentro de categoria jurídica heterogênea (3, ex. responsabilidade
   civil do Estado por lixão/vazamento, sem o rótulo de praxe no cabeçalho).
3. Restringir a busca ao campo estruturado (questão/tese) **não teria recuperado
   nenhum** dos 40 perdidos — a FTS já cobre a ementa inteira, então recorte de
   campo só ganharia precisão, nunca recall.
4. Sinônimos manuais mais ricos resolveriam 37 dos 40; só os 3 casos de fato
   atípico em responsabilidade civil do Estado justificariam busca semântica.

## Limitações deste harness

- 6 consultas, corpus de 3 meses (jun–ago/2026) — não generaliza para todo o
  histórico do TJSE nem para outros temas.
- O gabarito é obra de um único revisor (eu, por regex); não houve segundo
  revisor conferindo os 98 itens do gold.json.
- `por_pagina` do servidor satura em 20 (linha `_buscar`, `servidor_tjse.py`);
  `paginar_tudo()` em `medir.py` faz até 10 páginas (200 resultados) antes de
  desistir — nenhuma consulta bateu esse teto neste corpus, mas o teto existe.
