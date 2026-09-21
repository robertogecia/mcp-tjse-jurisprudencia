# Integração opcional: agente de pesquisa com vários tribunais

Para quem mantém, no Claude Code, um subagente de pesquisa jurídica com tabela de roteamento por tribunal.
Nada aqui é necessário para o servidor funcionar.

**Ferramentas a liberar no frontmatter do agente**

```
mcp__tjse_jurisprudencia__buscar_jurisprudencia_tjse, mcp__tjse_jurisprudencia__obter_inteiro_teor_tjse,
mcp__tjse_jurisprudencia__verificar_citacao_tjse, mcp__tjse_jurisprudencia__sincronizar_boletim_tjse,
mcp__tjse_jurisprudencia__diagnostico_tjse
```

**Linha de roteamento**

| Tribunal | Chave | Motor | Teto de verificação |
|---|---|---|---|
| TJSE, 2º grau | segmento `.8.25.` do nº CNJ ou tribunal nomeado; o TJSE numera por processo (12 dígitos) + acórdão (9) | `tjse_jurisprudencia` **mais** a base geral que você tiver, as duas: o índice é parcial por construção (só Boletim, só edições sincronizadas, sem juizados nem monocráticas). Julgado achado na base geral se confere no MCP pelo par processo + acórdão | `inteiro teor lido` após `obter_inteiro_teor_tjse`; antes, `só ementa/índice` |

**Regras que o agente precisa conhecer**: começar por `diagnostico_tjse`; nunca sincronizar em paralelo; zero resultado
nunca é "não localizado"; o formulário oficial tem verificação anti-robô e não se usa nem pelo navegador; aspas só
depois de `verificar_citacao_tjse`; alerta de TRANSCRIÇÃO significa que o trecho é de outro tribunal.

No servidor, declare a base geral para que as saídas apontem para ela: `TJSE_COMPLEMENTOS="Nome da sua base"`.
