# Paridade Python × Node

O servidor Python (`../../../servidor_tjse.py`) é a **referência**; a extensão Node tem de se comportar igual. Estes scripts
provam isso sobre o corpus real, e não sobre exemplos escolhidos a dedo.

```bash
./rodar.sh                       # precisa de Python 3, do índice em ../../../base e (opcional) dos recibos em ../../../recibos
TJSE_BASE_REAL=/outro/lugar ./rodar.sh
```

Quatro comparações, todas numa **cópia** (nada do original é tocado):

1. **Parsers** (`dump_py.py` × `dump_node.mjs` × `comparar.py`): para cada acórdão do HTML bruto, um hash de cada campo
   (processo, classe, recurso, relator, rótulo, ementa), de cada parte da ementa estruturada, das citações, das âncoras, do
   resultado declarado e da ementa normalizada. Em 21/09–23/09/2026: 38.283 acórdãos, zero diferença.
2. **Índice** (`indice_cmp.py`): o Node reconstrói o banco inteiro do HTML bruto; cada tabela é comparada com a do Python,
   inclusive o vocabulário do índice invertido (63.788 termos). A coluna `edicoes.rotulo` fica de fora de propósito: vem de
   fontes diferentes (listagem do portal × cabeçalho da página) e nunca aparece em saída.
3. **Busca** (`casos_busca.json`): ~40 consultas (grupos, texto livre, por campo, por citação, filtros, paginação, zero,
   erros) e o grafo de citações; a saída tem de ser idêntica **caractere a caractere**.
4. **Conferência de citação** (`confere_py.py` × `confere_node.mjs`): milhares de trechos sorteados dos recibos reais, com e
   sem `[...]`; veredito, alertas de atribuição e contexto têm de coincidir.

Controle negativo: se um hash for adulterado, `comparar.py` falha — o teste discrimina.
