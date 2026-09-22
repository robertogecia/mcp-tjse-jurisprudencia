# tjse-jurisprudencia — servidor MCP de jurisprudência do TJSE

Pesquisa de acórdãos do **Tribunal de Justiça de Sergipe** para quem vai **citar em peça**: índice local pesquisável,
inteiro teor com recibo, conferência literal de citação, órgão julgador e data lidos do fecho do acórdão.
Funciona com qualquer cliente MCP (Claude Desktop, Claude Code e outros).

Não é produto oficial do TJSE. Toda saída é rascunho: quem assina a peça confere.

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
O estado fica em disco sob `flock`, compartilhado entre processos. O cliente se identifica com User-Agent próprio
(`tjse-jurisprudencia-mcp/<versão>`); `TJSE_USER_AGENT` troca, por conta e risco de quem troca. Não rode scripts soltos
contra o portal fora do disjuntor, e não suba os limites: o servidor do tribunal é pequeno e é de todos.

## Instalação

```bash
git clone <este repositório> tjse-jurisprudencia && cd tjse-jurisprudencia
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python servidor_tjse.py --selftest        # offline, sobre os fixtures
```

`mcp<2` é proposital: a série 2.x renomeou `FastMCP` e o registro das tools falha em silêncio.

Claude Code:

```bash
claude mcp add tjse_jurisprudencia -- /caminho/tjse-jurisprudencia/.venv/bin/python /caminho/tjse-jurisprudencia/servidor_tjse.py
```

Claude Desktop (`claude_desktop_config.json`):

```json
{ "mcpServers": { "tjse_jurisprudencia": {
    "command": "/caminho/tjse-jurisprudencia/.venv/bin/python",
    "args": ["/caminho/tjse-jurisprudencia/servidor_tjse.py"],
    "env": { "TJSE_DIR_DADOS": "/caminho/para/dados-fora-de-nuvem" } } } }
```

`TJSE_DIR_DADOS` (opcional) diz onde ficam índice, recibos e disjuntor; o padrão é a pasta do script. Prefira um lugar
fora de pasta sincronizada em nuvem. Interromper a sincronização no meio não corrompe nada — o que entrou não é rebaixado e seção incompleta não entra pela metade. Primeira vez: peça ao assistente `sincronizar_boletim_tjse(meses=6)` e repita até
"período completo" (cerca de 6 a 8 requisições por mês de Boletim; ~40 MB de índice e ~5 MB de HTML bruto compactado por edição).

## Desenvolvimento

`--selftest` roda offline sobre fixtures reais (anonimizados), com estado em pasta temporária; blocos `R*` são regressões de
uso real, `RT*` e `RTB*` dos dois red teams. `--selftest --online` faz uma requisição real. Parser corrigido? **Suba `PARSER_VERSAO`**:
o índice é refeito do HTML bruto guardado em `base/secoes/`, sem rede. Protocolo medido: `references/protocolo-boletim.md`.
Relatórios de red team: `references/`. Histórico: `CHANGELOG.md`.

## Licença

MIT.
