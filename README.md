# Jurisprudência TJSE no Claude — instalação em 1 clique

[![tests](https://github.com/robertogecia/mcp-tjse-jurisprudencia/actions/workflows/test.yml/badge.svg)](https://github.com/robertogecia/mcp-tjse-jurisprudencia/actions/workflows/test.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Extensão MCP que dá ao **Claude Desktop** a capacidade de **pesquisar acórdãos de 2º grau do Tribunal de Justiça de
Sergipe** e, antes de você citar em peça, **conferir se a frase está literalmente no acórdão e de quem ela é** (do TJSE,
de outro tribunal transcrito no voto, do voto vencido, da parte...). Sem login, sem resolver captcha e sem programar.

> **Esta extensão BAIXA JULGADOS de verdade para o seu computador** e pesquisa nessa cópia local — não é uma busca "ao
> vivo". Reserve **cerca de 80 MB de disco por mês de Boletim (~1 GB para um ano; recomendado: 2 GB livres)**.

## Instalar (5 minutos)

### ⬇️ [BAIXE AQUI O ARQUIVO DE INSTALAÇÃO (`Jurisprudencia-TJSE.mcpb`)](https://github.com/robertogecia/mcp-tjse-jurisprudencia/releases/latest/download/Jurisprudencia-TJSE.mcpb)

> **⚠️ NÃO use o botão verde "Code → Download ZIP" desta página.** Aquele zip é o código-fonte e **não instala**. O que
> instala é só o **`.mcpb`** do link acima.

Depois de baixar:

1. **Dê dois cliques** no arquivo `Jurisprudencia-TJSE.mcpb`. O Claude Desktop abre na tela de instalação: clique em
   **Instalar**. *Se nada acontecer*, abra **Configurações → Extensões** e **arraste o arquivo** para essa janela.
2. **Abra uma conversa nova** e peça: ***"Importe o pacote do TJSE."*** (baixa ~80 MB de julgados já prontos, sem tocar o
   site do tribunal; leva poucos minutos).
3. Confira com: ***"Rode o diagnóstico do TJSE."*** — deve mostrar cerca de 38 mil acórdãos. Pronto: pergunte o que quiser.

Não precisa instalar mais nada: o Claude Desktop já traz o Node.js necessário.

> Requisitos: **Claude Desktop atualizado**, no **Mac ou Windows**. **Nunca usou uma extensão?** O
> **[guia passo a passo, sem Terminal](INSTALAR.md)** explica cada clique.

**Se não funcionar:**

| Sintoma | O que é |
|---|---|
| Arrastei o zip do GitHub e não instalou | Era o código-fonte. Baixe o `.mcpb` no link acima. |
| O Claude diz que não tem a ferramenta | Abra uma **conversa nova** (conversa antiga não enxerga extensão instalada depois) e confira se a extensão está **ativada** em Configurações → Extensões. |
| A busca responde "índice local VAZIO" | Falta o passo 2: *"Importe o pacote do TJSE."* |
| "este ambiente não tem o SQLite…" | O Claude Desktop está antigo: atualize-o. |
| A busca deu zero resultado | **Nunca é "não existe no TJSE"** — é "não existe no que você baixou". Rode o diagnóstico antes de concluir qualquer coisa. |
| Preciso resolver um captcha para pesquisar | Não. O formulário oficial com Cloudflare Turnstile nunca é usado nem contornado — veja abaixo por quê. |

### Quanto espaço em disco

| O que | Tamanho medido |
|---|---|
| A extensão | ~3 MB |
| Cada edição/mês do Boletim (índice + texto bruto) | ~80 MB |
| 1 ano completo de julgados | ~1 GB |
| **Folga recomendada** | **2 GB livres** |

Os dados ficam em `~/.tjse-jurisprudencia` (Mac) ou `%USERPROFILE%\.tjse-jurisprudencia` (Windows), **fora da extensão**:
atualizar a extensão não apaga o que você baixou, e apagar a pasta libera o espaço.

### Prefere o Terminal ou o Claude Code?

Há também o servidor em Python (mesmo comportamento, conferido contra o mesmo corpus): **[INSTALAR-PYTHON.md](INSTALAR-PYTHON.md)**.

## Por que ele é assim

O formulário oficial de pesquisa do TJSE exige **Cloudflare Turnstile** (verificação anti-robô) a cada consulta.
**Este projeto não usa esse formulário e não contorna a verificação** — nem por HTTP, nem por navegador automatizado.
Pedidos para "resolver o captcha" serão recusados.

O que o tribunal publica de forma aberta, sem desafio:

| Fonte oficial | O que entrega |
|---|---|
| **Boletim Jurídico de Sergipe** (`diario.tjse.jus.br/revista`) | ementário mensal: ementa integral, processo, acórdão, classe, relator, por órgão (Pleno, Seção Especializada Cível, 1ª e 2ª Câmaras Cíveis, Câmara Criminal) — cerca de 1.600 acórdãos por edição |
| **Inteiro teor** (`tjse.jus.br/tjnet/jurisprudencia/relatorio.wsp`) | ementa, fecho, relatório e voto, pelo par processo + acórdão (é o link que o próprio Boletim publica) |

Daí o desenho: o Boletim vira um **índice local** (SQLite FTS5) e a busca não gasta rede; o inteiro teor é baixado
sob demanda e guardado como **recibo** (com sha256), de modo que conferir uma citação duas vezes não custa nada.

## Ferramentas

| Tool | O que faz | Rede |
|---|---|---|
| `importar_pacote_tjse` | monta o índice a partir de um pacote pronto de HTML bruto (na extensão, baixa-o do GitHub com hash conferido); zero requisição ao portal | GitHub |
| `sincronizar_boletim_tjse` | baixa edições recentes para o índice; retomável; até 14 requisições por chamada | sim |
| `buscar_jurisprudencia_tjse` | busca local: `grupos` de sinônimos (OU dentro, E entre), singular/plural automático, `$` radical, **busca por parte da ementa** (`em=questao,tese`), **filtro pelo que o acórdão cita** (`cita="Tema 1061"`), filtros por órgão, classe, relator, número e data, ordenação por relevância | não |
| `mapa_de_citacoes_tjse` | grafo: precedentes qualificados mais aplicados, acórdãos do TJSE que as câmaras mais reusam (inclusive **anteriores ao período sincronizado**) e quem cita o quê | não |
| `obter_inteiro_teor_tjse` | inteiro teor; órgão e data pelo **fecho**; aceita a URL do acórdão colada | 1ª vez |
| `verificar_citacao_tjse` | confere se o trecho está **literalmente** no acórdão e avisa **de quem é a frase**: transcrição de outro tribunal, voto divergente, alegação da parte, trecho entre aspas, negação logo antes | 1ª vez |
| `diagnostico_tjse` | disjuntor, consumo, cobertura do índice por órgão, modo | não |

## Duas coisas que a busca por palavra não faz sozinha

**A ementa do TJSE é estruturada** (padrão CNJ) em dois terços dos acórdãos: caso em exame, questão em discussão,
razões de decidir, dispositivo e tese. `em="questao,tese"` procura só onde o tribunal enuncia o que decidiu — é bem
mais preciso que varrer a ementa inteira (mais preciso, não mais abrangente: medido, não recupera acórdão perdido). Quem não segue o padrão tem tudo em `cabecalho`, então buscar por campo
não perde acórdão: apenas deixa de distingui-lo.

**O grafo de citações sai das próprias ementas**, do campo "Jurisprudência relevante citada" que o tribunal preenche
— sem baixar um único inteiro teor. Com ele dá para perguntar "quais acórdãos aplicam o Tema 1061" em vez de tentar
adivinhar as palavras que eles usaram, e para ver quais julgados do próprio TJSE as câmaras mais reusam. A maioria
desses é **anterior ao período sincronizado**: o grafo enxerga além da janela do índice, ainda que para ler cada um
seja preciso achar o nº do acórdão fora daqui.

Cada busca com 5 ou mais resultados abre com um **panorama** de todas as ementas que casam: resultado declarado,
órgão, classe, súmulas/temas/IRDR citados e o vocabulário que distingue o conjunto (pista para novos grupos de sinônimos).
É amostragem para decidir o que ler — "recurso provido" por outro fundamento também conta como provido.
Busca que zera diz qual grupo zera. Acórdãos do mesmo processo (embargos) são avisados.

**Como escrever a consulta.** Palavras soltas combinam por OU e o ranking ordena, então a pergunta em português
corrente funciona ("idoso analfabeto empréstimo consignado assinatura não comprovada"). O que estiver "entre aspas"
é obrigatório, e `grupos` exige um termo de cada grupo. A medição em `harness/` compara as duas formas.

Fluxo: `diagnostico` → `sincronizar` (se faltar período) → `buscar` → `obter_inteiro_teor` → `verificar_citacao` antes de qualquer aspas.

## Modo híbrido: sozinho ou com outras fontes

**Sozinho** (só este servidor): tudo acima funciona. Para o que o índice não cobre, a saída manda pesquisar à mão no
portal oficial e explica como trazer o achado de volta: qualquer acórdão do TJSE encontrado em outro lugar
(portal, Diário, outra peça, um agregador) se confere aqui por `obter_inteiro_teor_tjse(numero_acordao, numero_processo)`
ou colando a URL do inteiro teor.

**Com outras fontes** (um agregador de jurisprudência, outro servidor MCP, uma assinatura): declare-as e as saídas
passam a apontar para elas nos pontos cegos, mantendo este servidor como o lugar da conferência:

```json
"env": { "TJSE_COMPLEMENTOS": "Nome da base A; Nome da base B" }
```

Em `integracoes/` há material opcional para quem usa Claude Code: uma skill autônoma
(`integracoes/skill-jurisprudencia-tjse/SKILL.md`) e o trecho de roteamento para um agente de pesquisa
(`integracoes/agente-de-pesquisa.md`). Nada disso é necessário para o servidor funcionar.

## Limites, ditos sem rodeio

- **Só 2º grau publicado no Boletim.** Turmas Recursais, Turma de Uniformização e decisões monocráticas não estão aqui.
- **A busca só enxerga o que foi sincronizado.** Zero resultado significa "nada no índice local, no período coberto"
  (a saída diz qual é) — **nunca** "não existe no TJSE".
- A edição sai no fim do mês com os julgados do mês anterior; a data do Boletim é de **publicação**. Data de julgamento,
  só no inteiro teor.
- O TJSE numera por **processo (12 dígitos) + acórdão (9 dígitos)**; o inteiro teor não traz número CNJ.
- A ementa do Boletim vem em CAIXA ALTA e pode diferir da original: aspas só depois de `verificar_citacao_tjse`.
- O voto do TJSE costuma **transcrever ementas e até fechos de outros tribunais**. O alerta de transcrição pega a grande
  maioria desses casos (medição em `CHANGELOG.md`), mas não substitui ler o acórdão.
- O inteiro teor nomeia partes — às vezes menor de idade e seu representante. o recibo traz `id_documento`, `nr_processo`, `tribunal`, `texto` e ainda `texto_transcrito`/`texto_divergente` (o que NÃO é palavra do tribunal), para que um verificador de citação avise em vez de aprovar; `recibos/` e `base/` ficam com
  permissão 0700/0600 e fora do versionamento. **Não publique recibos.** Os fixtures deste repositório foram anonimizados.
- O disjuntor é compartilhado entre processos pelo disco. Se o disco não aceitar gravação, a pausa vale só para o processo
  que a sofreu, e sem a trava nenhum processo requisita (fail-closed).
- Os alertas de conferência são heurísticos: pegam o padrão comum, não tudo (doutrina transcrita sem aspas passa). Eles
  dizem "confira quem fala", não substituem ler o voto.
- Seção grande vem paginada pelo portal (1.000 linhas); só entra no índice quando todas as páginas chegaram.
- Layout só foi medido em edições de 2026; edição antiga pode variar. A sincronização denuncia anomalias em vez de
  indexar em silêncio.

## Ritmo e boa vizinhança

6 s entre requisições · 20 por 10 min · 150 por dia · 429/403 → pausa de 6 h sem retentativa · marca de verificação
anti-robô na resposta → pausa de 24 h, nunca contornar · outro erro → 30 min · estado do disjuntor ilegível → pausa (fail-closed).
Depois de uma recusa do portal o ritmo **aperta sozinho** (escada de 4 degraus) e só afrouxa depois de 100 consultas limpas.
Timeout ou queda de conexão **não** armam o disjuntor (seção de câmara cível passa de 2 MB; timeout é esperado). O estado
fica em disco, compartilhado entre processos (`flock` no Python; trava por diretório atômico no Node). O cliente se
identifica com User-Agent próprio (`tjse-jurisprudencia-mcp/<versão>`); `TJSE_USER_AGENT` troca, por conta e risco de quem
troca. Não rode scripts soltos contra o portal fora do disjuntor, e não suba os limites: o servidor do tribunal é pequeno e é de todos.

## Configuração avançada

Variáveis de ambiente (para quem roda o servidor Python ou lança a extensão à mão): `TJSE_DIR_DADOS` diz onde ficam índice,
recibos e disjuntor (padrão: `~/.tjse-jurisprudencia` na extensão; a pasta do script no Python) — prefira um lugar **fora de
pasta sincronizada em nuvem**. `TJSE_COMPLEMENTOS` declara outras bases que você assina. `TJSE_MCP_SEM_AVISO_ATUALIZACAO=1`
desliga a consulta de versão nova. `TJSE_ORCAMENTO_CHAMADA_S` (extensão) muda o limite de tempo por chamada (padrão 45 s).
Interromper a sincronização no meio não corrompe nada: o que entrou não é rebaixado, e seção incompleta não entra pela metade.

## Desenvolvimento

O projeto tem **duas implementações do mesmo comportamento**: o servidor Python (`servidor_tjse.py`, a **referência**) e a
extensão Node (`mcpb/`, o que vai no `.mcpb`). Elas guardam dados em pastas distintas e não devem ser apontadas para a mesma.

- **Python:** `python3 servidor_tjse.py --selftest` roda offline sobre fixtures reais anonimizados (blocos `R*`: regressões de
  uso real; `RT*`, `RTB*`, `RTC*`: red teams). `--selftest --online` faz uma requisição real. Parser corrigido? **Suba
  `PARSER_VERSAO`**: o índice é refeito do HTML bruto em `base/secoes/`, sem rede.
- **Node:** `cd mcpb && npm ci && npm test` (70 testes, incluindo portal simulado e cliente MCP de verdade). Empacotar:
  `npx @anthropic-ai/mcpb@latest pack . Jurisprudencia-TJSE.mcpb` a partir de uma cópia com `npm ci --omit=dev`.
- **Paridade:** `mcpb/test/paridade/rodar.sh` compara Python × Node sobre o corpus real — parsers acórdão por acórdão, o
  índice reconstruído tabela a tabela, uma bateria de buscas caractere a caractere e milhares de conferências de citação.
  Roda numa cópia, sem tocar o índice original. Qualquer mudança de comportamento tem de passar por aqui.

Protocolo medido do Boletim: `references/protocolo-boletim.md`. Relatórios de red team: `references/`. Histórico: `CHANGELOG.md`.

## Autor

**Roberto Grécia Bessa** — OAB/RO 7865-A
Instagram: [@robertogrecia](https://instagram.com/robertogrecia)

## Licença

MIT.
