---
name: jurisprudencia-tjse
description: Pesquisa jurisprudência do Tribunal de Justiça de Sergipe (TJSE) pelo servidor MCP `tjse_jurisprudencia` — índice local do Boletim Jurídico oficial, inteiro teor com recibo e conferência literal de citação. Use quando o usuário pedir precedente, acórdão, ementa ou entendimento do TJSE ("o que o TJSE decide sobre…", "acha acórdão da 1ª Câmara Cível de Sergipe", "confere essa citação do TJSE"), quando o processo for da Justiça estadual de Sergipe (segmento `.8.25.` do número CNJ), ou quando for conferir citação do TJSE numa peça pronta. Funciona sozinha; se houver outras bases de jurisprudência disponíveis na sessão, combina com elas. Não use para outros tribunais, nem para pesquisar o formulário oficial do TJSE, que exige verificação anti-robô e não pode ser automatizado.
---

# Jurisprudência do TJSE

O servidor `tjse_jurisprudencia` não usa o formulário oficial de pesquisa do TJSE: ele exige Cloudflare Turnstile, e
verificação anti-robô não se contorna — nem pelo servidor, nem por navegador automatizado, nem a pedido. A fonte é o
Boletim Jurídico mensal do tribunal, indexado localmente, mais o inteiro teor pelo link oficial. Isso define o que a
pesquisa pode e não pode afirmar; o trabalho desta skill é manter essas afirmações honestas.

## Fluxo

1. **`diagnostico_tjse`** — veja de quando a quando o índice cobre e se há edição incompleta. Se o período que a tese
   pede não está coberto, **`sincronizar_boletim_tjse`** primeiro (uma chamada por vez; repita até "período completo").
   Nunca sincronize em paralelo: o portal é pequeno e o ritmo é limitado de propósito.
2. **`buscar_jurisprudencia_tjse`** — monte `grupos`: cada grupo é um conceito, com seus sinônimos dentro
   (`[["plano de saúde","operadora"],["autismo","espectro autista","TEA"],["astreintes","multa diária"]]`). Singular e
   plural já casam sozinhos; `$` no fim faz radical (`consign$`). Julgados do mesmo tema usam vocabulário diferente:
   depois da primeira busca, colha termos da melhor ementa e refaça. Não gasta rede — busque à vontade.
3. **`obter_inteiro_teor_tjse`** em no máximo 3 acórdãos que de fato importam. É aqui que se sabe o que foi decidido:
   ementa é resumo, e resumo engana. Órgão julgador e data de julgamento valem os do **fecho** (`orgao_fonte: fecho`).
4. **`verificar_citacao_tjse`** antes de qualquer trecho entre aspas. A ementa do Boletim vem em caixa alta e não é
   fonte literal. Leve a sério os alertas:
   - **TRANSCRIÇÃO** — o voto do TJSE copia ementas inteiras de outros tribunais. Trecho com esse alerta não é palavra
     do TJSE: ou se cita como "o TJSE, citando…", ou se vai buscar o original.
   - **NEGAÇÃO** — há "não", "improcedente", "rejeita-se" logo antes: o recorte pode dizer o contrário do julgado.
   - ❌ — não vai entre aspas. Falha de rede não é ❌: é "não conferido".

## O que dizer e o que não dizer

- Zero resultado = "nada no índice local, que cobre de X a Y" — **nunca** "o TJSE não tem precedente" nem "não localizado".
- O índice só tem 2º grau (Pleno, Seção Especializada Cível, Câmaras Cíveis, Câmara Criminal). Turma Recursal, Turma de
  Uniformização e monocrática ficam de fora: diga isso quando a tese for de juizado.
- `PESQUISA NÃO REALIZADA` (pausa do disjuntor, erro de rede) se relata como tal. Não tente outro caminho para o mesmo
  portal — nada de navegador, proxy ou script: isso prolonga bloqueio e o servidor é compartilhado com todo mundo.
- Nunca cite número de processo, relator ou câmara de memória. Só o que veio desta sessão.
- O inteiro teor nomeia partes, às vezes menores. Use o conteúdo para a peça; não o reproduza fora dela.

## Com e sem outras ferramentas

**Só este servidor:** para o que ele não cobre, oriente a pesquisa manual no portal oficial
(`tjse.jus.br/portal/consultas/jurisprudencia/judicial`) e peça ao usuário o par processo + acórdão (ou a URL do inteiro
teor) do que achar — com isso, passos 3 e 4 funcionam para qualquer acórdão do tribunal.

**Com outras bases na sessão** (agregador de jurisprudência, outros servidores MCP, banco de precedentes qualificados):
use-as para descobrir — período não sincronizado, juizados, IRDR/IAC e súmulas — e **confira aqui** todo julgado do
TJSE que vier delas, pelo par processo + acórdão. Súmula, IRDR e IAC do TJSE são precedente qualificado: procure na
fonte própria para isso; as 14 súmulas estão em PDF em `tjse.jus.br/portal/publicacoes/sumulas`.

## Entrega

Para cada acórdão aproveitado: tribunal e órgão (do fecho), classe e números (processo e acórdão), relator, data de
julgamento, link do inteiro teor, nível de verificação (`só ementa/índice` · `inteiro teor lido` · `lido EM PARTE`), o
trecho literal conferido (com os alertas, se houver) e uma linha dizendo **o que o acórdão decidiu e em que isso
sustenta, sustenta em parte ou contraria a tese**. Precedente contrário encontrado se entrega também — esconder não
ajuda quem vai ser confrontado com ele.
