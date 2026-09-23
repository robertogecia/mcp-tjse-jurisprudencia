# Jurisprudência do TJSE no Claude — instalação em 1 clique

Este guia é para **quem nunca instalou uma extensão** e não quer abrir o Terminal. Você vai baixar **um arquivo**, dar
**dois cliques** e pedir ao Claude, em português, que baixe os julgados. Não precisa instalar Python, Node nem mais nada.

> **O que esta extensão faz, em uma frase:** ela **baixa julgados de verdade** do Tribunal de Justiça de Sergipe para o seu
> computador e deixa o Claude pesquisar nessa cópia — e, antes de você citar uma frase em peça, confere se ela está
> literalmente no acórdão e avisa **de quem é a frase** (do TJSE, de outro tribunal transcrito no voto, do voto vencido...).

## Antes de começar: quanto espaço em disco reservar

**Este é o ponto mais fácil de subestimar.** Como os julgados ficam guardados no seu computador, quanto mais meses você
baixar, mais espaço ocupa. Medido no uso real (11 edições do Boletim, de outubro/2025 a agosto/2026, 38.283 acórdãos):

| O que | Tamanho | Regra prática |
|---|---|---|
| **A extensão em si** | ~3 MB | fixo |
| **Cada mês de Boletim** | ~80 MB | multiplique pelos meses que você quer cobrir |
| **1 ano de julgados** | ~1 GB | o caso mais comum |
| **Recomendação de folga livre** | **2 GB** | cobre 1 ano, mais margem |

Durante o download do pacote pronto o computador usa uns **80 MB a mais** por alguns instantes (o arquivo baixado). Se
você planeja vários anos de histórico, conte ~1 GB a cada 12 meses. O espaço não é gasto de uma vez: cresce conforme você
baixa mais períodos, e você para quando o período já te atender.

## Passo 1 — Baixe o arquivo

Clique aqui: **[Jurisprudencia-TJSE.mcpb](https://github.com/robertogecia/mcp-tjse-jurisprudencia/releases/latest/download/Jurisprudencia-TJSE.mcpb)**

O arquivo tem uns 3 MB e vai para a sua pasta **Downloads**.

> **Não use o botão verde "Code → Download ZIP" desta página.** Aquele ZIP é o código-fonte e **não instala**. O que
> instala é só o arquivo `.mcpb` do link acima.

## Passo 2 — Instale no Claude Desktop

1. Abra a pasta **Downloads** e **dê dois cliques** em `Jurisprudencia-TJSE.mcpb`.
2. O **Claude Desktop** abre sozinho numa tela de instalação. Clique em **Instalar** (*Install*).
3. Se o Claude pedir para reiniciar, reinicie.

**Se nada acontecer ao dar dois cliques:** abra o Claude Desktop → **Configurações** (*Settings*) → **Extensões**
(*Extensions*) e **arraste o arquivo** para essa janela.

> Precisa do **Claude Desktop atualizado**, no **Mac ou Windows**. A extensão usa o Node.js que já vem dentro do
> Claude Desktop, por isso não há mais nada para instalar.

## Passo 3 — Baixe os julgados (a parte que usa o disco)

Abra uma **conversa nova** no Claude e escreva, em português normal:

> **Importe o pacote do TJSE.**

O Claude vai pedir permissão para usar a ferramenta `importar_pacote_tjse` — clique em **Permitir**. Ela baixa um pacote
pronto de uns **80 MB** (com conferência de integridade) e monta o índice em poucos segundos. **Não acessa o site do
tribunal**, por isso é rápido e não pesa no servidor dele.

Se a conexão for lenta, o Claude responde "Baixando… X de Y MB, chame de novo": **é só repetir o pedido** — o download
continua sozinho em segundo plano.

Para conferir que deu certo, escreva:

> **Rode o diagnóstico do TJSE.**

Deve aparecer algo como *"38283 acórdãos de 11 edição(ões) do Boletim"*.

## Passo 4 — Use

Peça em linguagem natural, por exemplo:

> "O que o TJSE entende sobre desconto indevido em benefício previdenciário de idoso analfabeto?"
>
> "Acórdãos da 2ª Câmara Cível sobre astreintes contra banco, mais recentes primeiro."
>
> "Traga o inteiro teor do acórdão 202561964."
>
> "Confira se esta frase está literalmente no acórdão 202561964: «…»"

**Nunca cite entre aspas sem passar pela conferência** (*"Confira se esta frase está no acórdão…"*): a ementa do Boletim
vem em CAIXA ALTA e não serve de fonte literal, e um voto do TJSE costuma transcrever ementas de outros tribunais.

## Manter atualizado (julgados novos)

O pacote pronto vai até **31/08/2026**. Para trazer os meses seguintes, peça:

> **Sincronize o Boletim do TJSE dos últimos 3 meses.**

Essa parte baixa direto do site do tribunal, **de propósito devagar** (o servidor deles é pequeno e é de todos). Cada
chamada faz só algumas requisições: **repita o pedido** até o Claude dizer *"Todas as edições listadas estão completas"*.

## Onde ficam os dados, e como liberar espaço

Tudo fica numa pasta na sua área de usuário, **fora da extensão** (assim atualizar a extensão não apaga o que você baixou):

- **Mac:** `~/.tjse-jurisprudencia` — no Finder, menu **Ir → Ir para a Pasta…** e digite `~/.tjse-jurisprudencia`
- **Windows:** `%USERPROFILE%\.tjse-jurisprudencia` — cole isso na barra de endereço do Explorador de Arquivos

Apagar essa pasta libera todo o espaço; para voltar a usar, é só repetir o Passo 3.

## Atualizar a extensão

Quando houver versão nova, o Claude avisa no fim da primeira resposta da conversa. Baixe o novo arquivo `.mcpb` (Passo 1)
e dê dois cliques. **Os julgados baixados são mantidos.**

## Desinstalar

Claude Desktop → **Configurações → Extensões** → remova **Jurisprudência TJSE**. Depois, apague a pasta de dados
(acima) se quiser recuperar o espaço.

## Se não funcionar

| Sintoma | O que é |
|---|---|
| Arrastei o ZIP do GitHub e não instalou | Era o código-fonte. Baixe o `.mcpb` no Passo 1. |
| O Claude diz que não tem a ferramenta | Abra uma **conversa nova** (conversa antiga não enxerga extensão instalada depois) e confira, em Configurações → Extensões, se está **ativada**. |
| A busca responde **"índice local VAZIO"** | Você ainda não fez o Passo 3. Peça: *"Importe o pacote do TJSE."* |
| Aparece **"este ambiente não tem o SQLite…"** | O Claude Desktop está antigo. Atualize-o para a versão mais recente e abra de novo. |
| A importação dá erro de rede | Tente de novo. Em rede de escritório com proxy que intercepta HTTPS, fale com o suporte de TI; enquanto isso, *"Sincronize o Boletim do TJSE dos últimos 12 meses"* também funciona (repita o pedido várias vezes). |
| Aparece **"⚠ EDIÇÕES INCOMPLETAS"** que não some | Peça uma sincronização com janela maior (*"…dos últimos 12 meses"*): a janela conta para trás a partir de hoje. |
| **Zero resultado** numa busca | **Nunca** significa que o TJSE não julgou — só que não há no que você baixou. Rode o diagnóstico antes de concluir qualquer coisa. |

## Avisos

- **Projeto não-oficial.** Os dados vêm de publicação oficial e aberta do TJSE (o Boletim Jurídico de Sergipe), mas a
  extensão não é do tribunal. Se o Boletim mudar de formato, pode parar até ser atualizada.
- **Cobre só o 2º grau** e só o que você baixou. Não tem Turma Recursal nem decisão monocrática.
- **O formulário oficial de pesquisa do TJSE exige verificação anti-robô** (Cloudflare Turnstile) e **não é usado nem
  contornado** — é por isso que a fonte é o Boletim.
- **Toda saída é rascunho.** Quem assina a peça confere. Vale para qualquer ferramenta de IA jurídica, e vale em dobro
  para citação.
- **Aviso de atualização.** Ao iniciar, a extensão consulta uma vez a página de versões deste repositório, em segundo
  plano, para avisar se há versão nova. Nada da sua pesquisa ou do seu caso sai do seu computador nessa consulta.

Prefere usar pelo Terminal, com o Claude Code? Veja **[INSTALAR-PYTHON.md](INSTALAR-PYTHON.md)**.

## Autor

**Roberto Grécia Bessa** — OAB/RO 7865-A
Instagram: [@robertogrecia](https://instagram.com/robertogrecia)
