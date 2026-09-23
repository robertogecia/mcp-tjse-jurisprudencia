# Jurisprudência do TJSE no Claude — instalação pelo Terminal (Python)

> **Este é o guia para quem usa o Claude Code ou prefere o servidor Python.** Se você usa o **Claude Desktop** e não quer abrir o Terminal, use o **[guia de um clique (INSTALAR.md)](INSTALAR.md)**: é a extensão `.mcpb`, sem instalar nada além do arquivo.
> As duas versões têm o mesmo comportamento (conferido contra o mesmo corpus), mas guardam os dados em pastas **diferentes**: a extensão em `~/.tjse-jurisprudencia`, o servidor Python na pasta do projeto (ou em `TJSE_DIR_DADOS`).

Este projeto dá ao **Claude** a capacidade de pesquisar **acórdãos de 2º grau do Tribunal de
Justiça de Sergipe**, conferir citação palavra por palavra contra o inteiro teor e ler o órgão
julgador no fecho do acórdão — sem login e sem resolver captcha.

## O que ele faz, em termos simples

Ele **baixa julgados de verdade** para o seu computador e guarda uma cópia local pesquisável —
não é uma busca "ao vivo" que consulta a internet toda vez. Funciona assim:

1. O Tribunal de Justiça de Sergipe publica, todo mês, um **Boletim Jurídico** com o texto de
   todos os acórdãos daquele período (isso é público, qualquer pessoa pode consultar).
2. Este projeto baixa esse Boletim, edição por edição, e guarda **duas cópias na sua máquina**:
   o texto original bruto (como veio do tribunal) e um índice organizado para busca rápida.
3. Quando você pede ao Claude para pesquisar, ele procura **no que já está no seu disco** — não
   sai buscando na internet a cada pergunta. Só acessa a internet quando falta alguma edição e
   você pede para sincronizar.

Ou seja: **o "peso" deste projeto no seu computador cresce conforme você baixa mais meses de
julgados.** Quanto mais tempo de Boletim você sincronizar, mais espaço em disco ele ocupa —
veja os números abaixo antes de decidir quantos meses baixar.

> **Sobre o formulário oficial do tribunal:** ele exige verificação anti-robô (Cloudflare
> Turnstile) a cada consulta. **Este projeto não usa esse formulário e não contorna a
> verificação** de forma alguma. Por isso ele lê o Boletim Jurídico (que é público e não tem
> esse bloqueio) em vez do formulário de busca — e por isso a cobertura é "o que foi baixado do
> Boletim", não "tudo que existe no TJSE". Isso é explicado com mais detalhe em
> "O que ele NÃO cobre", mais abaixo.

## Antes de instalar: quanto espaço em disco reservar

**Este é o ponto mais fácil de subestimar.** O projeto baixa julgados de verdade para o seu
computador — quanto mais meses de Boletim você trouxer, mais espaço ele ocupa.

Medido no uso real deste projeto (11 edições do Boletim, de outubro/2025 a agosto/2026,
38.283 acórdãos):

| O que | Tamanho medido | Regra prática |
|---|---|---|
| **Cada edição/mês do Boletim** | ~80 MB (índice + texto bruto guardado) | multiplique pelos meses que você pretende cobrir |
| **1 ano completo de julgados** | ~1 GB | é o caso mais comum: quem cita jurisprudência recente |
| Programa em si (sem julgados) | ~65 MB | fixo, não cresce |
| **Recomendação de folga livre** | **2 GB** | cobre 1 ano de julgados + o programa + margem de segurança |

Se você planeja baixar **vários anos** de histórico, multiplique: ~1 GB a cada 12 meses de
Boletim. O espaço não é gasto de uma vez — cresce aos poucos, conforme você manda sincronizar
mais períodos (passo 7 abaixo). Você pode parar de sincronizar quando o período já te atender.

## Antes de começar: dois programas que faltam no computador

Este guia assume que você **nunca usou o Terminal** e não sabe o que é "instalar por linha de
comando". Vamos com calma, passo a passo — cada comando abaixo você **copia e cola**, não
precisa entender o que ele faz para que funcione (mas eu explico mesmo assim).

### O que é o "Terminal"

É um aplicativo que já vem no seu Mac, para digitar (ou colar) comandos de texto em vez de clicar
em ícones. Você vai usá-lo só nesta instalação — depois disso, o dia a dia é 100% dentro do
Claude, em linguagem normal.

**Para abrir o Terminal:** pressione `Cmd` + `Espaço` (abre a busca do Spotlight), digite
`Terminal` e pressione `Enter`. Vai abrir uma janela preta ou branca com um cursor piscando.
É nela que você vai colar os comandos das próximas seções.

> **Como colar um comando:** copie o texto do bloco cinza (clique e arraste para selecionar, ou
> use o botão de copiar se seu leitor mostrar um), clique dentro da janela do Terminal, pressione
> `Cmd` + `V` para colar, e por fim `Enter` para executar. Espere terminar antes de colar o
> próximo — alguns comandos demoram alguns segundos.

### 1. Instale o Python (se ainda não tiver)

O Python é a linguagem em que este projeto foi escrito; sem ele, nada roda. Cole no Terminal:

```bash
python3 --version
```

- **Se aparecer algo como `Python 3.11.x` ou mais novo:** ótimo, já tem. Pule para o passo 2.
- **Se der erro, ou mostrar uma versão menor que 3.11:** baixe o instalador oficial em
  **[python.org/downloads](https://www.python.org/downloads/)** — o site já detecta que você
  está no Mac e oferece o botão certo. Baixe, dê dois cliques no arquivo baixado e siga a
  instalação normal (Continuar → Continuar → Instalar), como qualquer programa de Mac. Depois,
  feche e abra o Terminal de novo e repita o comando acima para confirmar.

### 2. Instale o Git (se ainda não tiver)

O Git é o programa que baixa o projeto do GitHub para o seu computador. Cole:

```bash
git --version
```

- **Se aparecer um número de versão:** já tem, pule para o passo 3.
- **Se o Mac perguntar "Instalar as ferramentas de linha de comando do Xcode?":** clique em
  **Instalar** e aguarde (pode levar alguns minutos, dependendo da internet). Quando terminar,
  repita o comando acima para confirmar.

## Instalar o projeto (10 a 15 minutos, a maior parte esperando)

### 3. Baixe o projeto para o seu computador

Cole, um comando por vez, esperando cada um terminar:

```bash
git clone https://github.com/robertogecia/mcp-tjse-jurisprudencia.git ~/MCP/tjse-jurisprudencia
cd ~/MCP/tjse-jurisprudencia
```

O primeiro comando copia o projeto para uma pasta chamada `MCP/tjse-jurisprudencia` dentro da
sua pasta de usuário (o "Home" — o mesmo lugar de Documentos, Downloads etc.). O segundo entra
nessa pasta, para os próximos comandos saberem onde procurar os arquivos.

### 4. Instale as peças que o projeto precisa para funcionar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

O primeiro comando cria uma "caixa isolada" (chamada `.venv`) só para este projeto, para não
bagunçar nada que você já tenha instalado. O segundo baixa, dentro dessa caixa, as três
bibliotecas de que o projeto precisa. Pode levar um minuto; é normal aparecer texto passando.

> **Por que a versão importa aqui:** dentro de `requirements.txt` está escrito `mcp<2` — isso é
> proposital, não erro de digitação. Se alguém no futuro trocar por uma versão 2.x mais nova, o
> projeto conecta ao Claude só na aparência, e nenhuma ferramenta funciona, sem aviso nenhum.

### 5. Confira que deu tudo certo

```bash
.venv/bin/python servidor_tjse.py --selftest
```

Isso roda 222 verificações internas, sem acessar a internet. Espere aparecer, na última linha:

```
222 verificações OK, 0 falha(s)
```

Se aparecer isso, está tudo certo — pode seguir. Se aparecer qualquer "FALHOU", pare aqui e peça
ajuda antes de usar em um caso real (veja "Autor", no fim deste guia, para contato).

### 6. Ligue o projeto ao Claude

**Se você usa o Claude Code** (a versão de terminal/linha de comando do Claude), cole:

```bash
claude mcp add tjse_jurisprudencia -- ~/MCP/tjse-jurisprudencia/.venv/bin/python ~/MCP/tjse-jurisprudencia/servidor_tjse.py
```

**Se você usa o Claude Desktop** (o aplicativo com janela, ícone na barra de menu/Dock):

1. Abra o Claude Desktop.
2. No menu superior, clique em **Configurações** (ou o ícone de engrenagem).
3. Procure **Desenvolvedor** e clique em **Editar configuração** (isso abre um arquivo de texto
   chamado `claude_desktop_config.json`).
4. Dentro dele, dentro da parte que começa com `"mcpServers"`, acrescente o trecho abaixo. Troque
   `SEU-USUARIO` pelo nome da sua conta no Mac (é o mesmo nome que aparece na sua pasta Home —
   se não souber qual é, cole `whoami` no Terminal e o nome aparece):

```json
{
  "mcpServers": {
    "tjse_jurisprudencia": {
      "command": "/Users/SEU-USUARIO/MCP/tjse-jurisprudencia/.venv/bin/python",
      "args": ["/Users/SEU-USUARIO/MCP/tjse-jurisprudencia/servidor_tjse.py"]
    }
  }
}
```

5. Salve o arquivo e **feche e abra o Claude Desktop de novo** (isso é obrigatório — ele só lê
   essa configuração ao iniciar).

### 7. Baixe os julgados (a etapa que usa o espaço de disco da tabela acima)

Até aqui, o projeto está instalado mas **vazio** — sem nenhum julgado ainda. Agora é a hora de
baixar. Duas formas, escolha uma:

**Forma A — mais rápida, um arquivo pronto para baixar.** Alguém (ou você mesmo, depois) já
baixou um conjunto de julgados e deixou pronto para reaproveitar, sem precisar esperar o
tribunal responder devagar. Cole no Terminal, ainda dentro da pasta do projeto:

```bash
curl -LO https://github.com/robertogecia/mcp-tjse-jurisprudencia/releases/latest/download/base-secoes-tjse.tar.gz
curl -LO https://github.com/robertogecia/mcp-tjse-jurisprudencia/releases/latest/download/SHA256SUMS.txt
shasum -a 256 -c SHA256SUMS.txt
tar -xzf base-secoes-tjse.tar.gz -C base/
```

O terceiro comando (`shasum`) confere se o arquivo baixado não foi corrompido ou alterado no
caminho — deve responder `OK`. Se responder outra coisa, apague os dois arquivos baixados e
tente de novo. O arquivo tem sempre o mesmo nome (`base-secoes-tjse.tar.gz`) e o link `latest` aponta
para a versão mais recente do pacote; a lista completa está em
**[Releases](https://github.com/robertogecia/mcp-tjse-jurisprudencia/releases)**.

Depois, abra uma conversa nova no Claude e escreva, em português normal: **"importe o pacote do
TJSE"**. Isso organiza o que você acabou de baixar, sem acessar a internet de novo.

**Forma B — mais lenta, direto do tribunal.** Se preferir não baixar o arquivo pronto (ou quiser
um período diferente), abra uma conversa nova no Claude e escreva:

> "Sincronize o Boletim do TJSE dos últimos 12 meses."

O tribunal responde devagar de propósito (este projeto respeita isso), então **repita o mesmo
pedido várias vezes** — algo como 10 vezes para cobrir um ano inteiro — até a resposta dizer que
o período está completo.

Depois de qualquer uma das duas formas, confira perguntando ao Claude: **"Rode o diagnóstico do
TJSE"**. Se aparecer `⚠ EDIÇÕES INCOMPLETAS`, ainda falta alguma coisa — peça para sincronizar
de novo, com um período mais longo.

## Como usar (aqui não tem mais Terminal — é tudo dentro do Claude)

A partir de agora, esqueça o Terminal: você conversa normalmente com o Claude, em português,
como sempre fez. Exemplos do que pedir:

> "O que o TJSE entende sobre desconto indevido em benefício previdenciário de idoso analfabeto?"
>
> "Acórdãos da 2ª Câmara Cível sobre astreintes contra banco, mais recentes primeiro."
>
> "Traga o inteiro teor do acórdão 202561964."
>
> "Confira se esta frase está literalmente no acórdão 202561964: «a multa se justifica pela sua
> natureza inibitória»."

São seis ferramentas. A que mais importa e quase ninguém tem é a **conferência literal**
(`verificar_citacao_tjse`): ela responde se o trecho aparece palavra por palavra no inteiro teor
**e de quem é a frase** — porque um ✅ pode estar apontando para uma ementa do STJ transcrita
dentro do voto, para o voto vencido ou para o relatório narrando o que a parte alegou. Os alertas
`TRANSCRIÇÃO`, `VOTO DIVERGENTE`, `ALEGAÇÃO DA PARTE`, `ENTRE ASPAS` e `NEGAÇÃO` existem para isso.

**Nunca cite entre aspas sem passar por ela.** A ementa do Boletim vem em CAIXA ALTA e não serve
de fonte literal.

## O que ele NÃO cobre

- **Só 2º grau**, e só as edições que você sincronizou. Não tem Turma Recursal nem decisão
  monocrática.
- **Zero resultado aqui nunca é "não existe no TJSE"** — é "não existe nesta janela". O servidor
  diz isso na própria resposta, e é para levar a sério antes de escrever "não localizado" numa peça.
- Não substitui base paga. Se você tem JusRatio ou equivalente, use os dois: o julgado achado lá
  se confere aqui pelo par processo (12 dígitos) + acórdão (9 dígitos).

## Avisos

- **Projeto não-oficial.** Os dados vêm de publicação oficial e aberta do TJSE, mas o projeto não
  é do tribunal. Se o Boletim mudar de formato, pode parar até ser atualizado.
- **Toda saída é rascunho.** Quem assina a peça confere. Vale para qualquer ferramenta de IA
  jurídica, e vale em dobro para citação.
- **Ritmo.** Teto de 20 requisições por 10 minutos e 150 por dia, com 6 segundos entre elas, e o
  ritmo aperta sozinho se o portal recusar. Não contorne por navegador ou proxy: o limite existe
  para o portal do tribunal continuar de pé, e para você não ser bloqueado.
- **Aviso de atualização.** Na subida, o servidor consulta uma vez a página de releases deste
  repositório, em segundo plano, para avisar se há versão mais nova. Nada da sua pesquisa ou do
  seu caso sai daqui — só o GitHub vê que alguém consultou. Para desligar, defina
  `TJSE_MCP_SEM_AVISO_ATUALIZACAO=1`.

## Atualizar

```bash
cd ~/MCP/tjse-jurisprudencia && git pull && .venv/bin/python servidor_tjse.py --selftest
```

Depois reinicie o Claude. **O índice em `base/` não se perde**: se o parser tiver mudado, ele é
reconstruído do HTML bruto já guardado em disco, sem rede.

> **Ao copiar o índice para outra máquina, leve `base/` inteiro** — o `.db` sozinho não basta.
> Sem `base/secoes/`, a primeira reindexação apaga as seções que não têm HTML bruto.

## Desinstalar

1. Se você usa o **Claude Desktop**: volte em Configurações → Desenvolvedor → Editar
   configuração, e apague o trecho `"tjse_jurisprudencia": { ... }` que você colou no passo 6.
   Se usa o **Claude Code**: cole `claude mcp remove tjse_jurisprudencia` no Terminal.
2. Apague a pasta do projeto: no Finder, vá em `Ir` → `Ir para a Pasta...`, digite `~/MCP` e
   apague a pasta `tjse-jurisprudencia` (ou cole `rm -rf ~/MCP/tjse-jurisprudencia` no Terminal,
   com cuidado: isso apaga tudo, inclusive os julgados já baixados).

## Autor

**Roberto Grécia Bessa** — OAB/RO 7865-A
Instagram: [@robertogrecia](https://instagram.com/robertogrecia)
