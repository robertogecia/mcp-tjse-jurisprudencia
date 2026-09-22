# Jurisprudência do TJSE no Claude — instalação

Este projeto dá ao **Claude** a capacidade de pesquisar **acórdãos de 2º grau do Tribunal de
Justiça de Sergipe**, conferir citação palavra por palavra contra o inteiro teor e ler o órgão
julgador no fecho do acórdão — sem login e sem resolver captcha.

> **Antes de tudo:** o formulário oficial de pesquisa do TJSE exige verificação anti-robô
> (Cloudflare Turnstile). **Este projeto não usa esse formulário e não contorna a verificação.**
> Ele indexa o **Boletim Jurídico de Sergipe**, que o tribunal publica aberto. É por isso que a
> cobertura é a das edições sincronizadas, e não "todo o TJSE" — leia "O que ele NÃO cobre".

## Requisitos

- **Python 3.11 ou mais novo** (`python3 --version`)
- Claude Desktop, Claude Code ou qualquer cliente MCP
- ~1 GB livre em disco para o índice local, depois de sincronizado

## Instalar (5 minutos)

### 1. Baixe o projeto

```bash
git clone https://github.com/robertogecia/mcp-tjse-jurisprudencia.git ~/MCP/tjse-jurisprudencia
cd ~/MCP/tjse-jurisprudencia
```

### 2. Instale a única dependência de rede

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

O ambiente isolado (`.venv`) evita conflito com outros projetos Python da máquina. Se preferir
instalar no Python do sistema, troque por `python3 -m pip install -r requirements.txt` e use
`python3` no lugar de `.venv/bin/python` nos passos seguintes.

> **O `<2` não é capricho.** Na versão 2.x a biblioteca renomeou `FastMCP` para `MCPServer`, e o
> registro das ferramentas **falha em silêncio**: o servidor sobe, aparece conectado e não expõe
> ferramenta nenhuma. Se as tools sumirem, confira a versão antes de procurar qualquer outra coisa.

### 3. Confira que está tudo de pé

```bash
.venv/bin/python servidor_tjse.py --selftest
```

Deve terminar em `216 verificações OK, 0 falha(s)`. Qualquer falha aqui é para resolver antes
de usar em caso real.

### 4. Ligue ao Claude

**Claude Code** (um comando):

```bash
claude mcp add tjse_jurisprudencia -- ~/MCP/tjse-jurisprudencia/.venv/bin/python ~/MCP/tjse-jurisprudencia/servidor_tjse.py
```

**Claude Desktop**: Configurações → Desenvolvedor → Editar configuração, e acrescente dentro de
`mcpServers` (troque `SEU-USUARIO` pelo seu usuário do sistema):

```json
{
  "mcpServers": {
    "tjse_jurisprudencia": {
      "command": "/Users/SEU-USUARIO/MCP/tjse-jurisprudencia/.venv/bin/python",
      "args": ["/Users/SEU-USUARIO/MCP/tjse-jurisprudencia/servidor_tjse.py"],
      "env": { "TJSE_DIR_DADOS": "/Users/SEU-USUARIO/dados-tjse" }
    }
  }
}
```

`TJSE_DIR_DADOS` é opcional e diz onde ficam índice, recibos e disjuntor; sem ele, é a pasta do
projeto. **Aponte para fora de pasta sincronizada em nuvem** (OneDrive, Dropbox, iCloud): são
centenas de MB que mudam a cada sincronização, e nuvem no meio do caminho já corrompeu índice.

Reinicie o Claude.

### 5. Monte o índice (a parte que leva tempo)

O projeto vem **sem índice**: ele é montado na sua máquina, a partir do Boletim oficial. Peça ao
Claude:

> "Sincronize o Boletim do TJSE dos últimos 12 meses."

Cada chamada baixa no máximo 14 requisições, com 6 segundos entre elas — o portal é pequeno e o
projeto anda devagar de propósito. **Repita o pedido até a resposta dizer que o período está
completo**; são cerca de 10 chamadas para um ano. O resultado fica em `base/`, e nada disso
precisa ser refeito depois.

Confira com:

> "Rode o diagnóstico do TJSE."

Se aparecer `⚠ EDIÇÕES INCOMPLETAS`, ainda falta sincronizar. **Uma edição antiga pode ficar
eternamente marcada como incompleta se estiver fora da janela pedida** — o parâmetro é `meses`,
contado para trás a partir de hoje; peça uma janela maior que o intervalo que você quer cobrir.

## Como usar

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

Remova a entrada do arquivo de configuração do Claude e apague a pasta do projeto.
