#!/usr/bin/env node
/**
 * Servidor MCP — Jurisprudência do TJSE (Tribunal de Justiça de Sergipe)
 * Porte Node.js do servidor Python (../servidor_tjse.py — fonte de verdade) para empacotamento .mcpb
 * (um clique no Claude Desktop). Parsers, índice, busca e conferência de citação são conferidos contra o
 * Python sobre o corpus real em test/paridade/.
 *
 * Este arquivo só liga o protocolo MCP; a lógica está nos módulos ao lado.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { VERSAO, MAX_REQ_POR_SINCRONIZACAO, AmbienteIncompativel } from "./config.js";
import { buscar, mapaCitacoes } from "./busca.js";
import { sincronizar, obter, verificar, diagnostico, importarPacote } from "./ferramentas.js";
import { comAvisos, iniciarChecagemVersao, linkRelato } from "./avisos.js";

const server = new McpServer({ name: "Jurisprudência TJSE", version: VERSAO });
iniciarChecagemVersao();

// Orçamento de TEMPO por chamada: o cliente MCP costuma abortar respostas acima de ~60 s. Sincronização e importação
// são retomáveis, então parar cedo e pedir "chame de novo" é seguro. Ajustável para quem sabe que o cliente aguenta mais.
const orcamentoMs = () => Number(process.env.TJSE_ORCAMENTO_CHAMADA_S || 45) * 1000;
const texto = async (t) => ({ content: [{ type: "text", text: comAvisos(await t) }] });
const seguro = (nome, fn) => async (a) => {
  try { return await texto(fn(a)); } catch (ex) {
    if (ex instanceof AmbienteIncompativel) return texto(`PESQUISA NÃO REALIZADA — ${ex.message}`);
    return texto(`ERRO INTERNO em ${nome} (${ex.name}: ${ex.message}) — é defeito da ferramenta, não do portal nem da sua pesquisa. Isto NÃO é 'não localizado'.\nSe persistir, relate: ${linkRelato(nome)}`);
  }
};
const SO_LEITURA = { readOnlyHint: true, destructiveHint: false, openWorldHint: false };

server.registerTool("sincronizar_boletim_tjse", {
  title: "Sincronizar o Boletim Jurídico do TJSE",
  description: "Baixa para o índice local as edições do Boletim Jurídico do TJSE dos últimos `meses` (1-24), da mais recente para a mais antiga. " +
    "ÚNICA ferramenta de busca que gasta rede: 1 requisição pela lista de edições, 1 por menu de edição e 1 por seção (5 por edição; seção de câmara cível passa de 2 MB). " +
    "Teto de 14 requisições por chamada, 6 s entre elas, e um limite de tempo por chamada — chame de novo até dizer 'período completo'. Nada é rebaixado. " +
    "A edição mais antiga só entra se `meses` for grande o bastante para alcançá-la (o padrão é 3).",
  inputSchema: {
    meses: z.number().int().min(1).max(24).default(3).describe("Quantos meses para trás, contados de hoje (1-24). Para cobrir um ano, use 12."),
    max_requisicoes: z.number().int().min(2).max(MAX_REQ_POR_SINCRONIZACAO).default(MAX_REQ_POR_SINCRONIZACAO).describe("Teto de requisições ao portal nesta chamada."),
  },
}, seguro("sincronizacao", (a) => sincronizar(a.meses, a.max_requisicoes, { prazoMs: Date.now() + orcamentoMs() })));

server.registerTool("buscar_jurisprudencia_tjse", {
  title: "Buscar acórdãos do TJSE no índice local",
  description: "Busca acórdãos de 2º grau do TJSE no ÍNDICE LOCAL do Boletim Jurídico. Zero rede, zero custo de disjuntor. Consulta sem acento e sem caixa. " +
    "`grupos` (E entre grupos, OU dentro de cada um) é a forma mais precisa; `consulta` livre serve para explorar (palavras soltas combinam por OU e o ranking põe no topo quem casa mais). " +
    "`em` restringe a busca a uma parte da ementa estruturada (questao, tese, razoes, caso, dispositivo, cabecalho); `cita` filtra pelo que o acórdão CITA (Tema 1061, Súmula 479/STJ, IRDR 15, processo do TJSE). " +
    "Tudo é 'só ementa/índice': a ementa do Boletim vem em CAIXA ALTA e NÃO serve de fonte para aspas — antes de citar, obter_inteiro_teor_tjse e verificar_citacao_tjse. " +
    "Cobre apenas as edições sincronizadas (a saída diz quais) e NÃO cobre Turmas Recursais, monocráticas nem o período anterior ao Boletim indexado. " +
    "Zero resultado aqui nunca é 'não localizado no TJSE' — é 'não localizado nesta janela'.",
  inputSchema: {
    consulta: z.string().optional().describe("Texto livre. Palavras e \"frases entre aspas\"; operador em CAIXA ALTA é recusado (use `grupos`). Cada termo casa também no outro número (dano moral ↔ danos morais)."),
    grupos: z.array(z.array(z.string())).optional().describe("[[\"dano moral\"],[\"negativação\",\"inscrição indevida\"]] → E entre grupos, OU dentro de cada um. Termo com `$` no fim é radical (`consign$`)."),
    orgao: z.string().optional().describe("Seção do Boletim, ex. \"1ª Câmara Cível\". Vem do CADASTRO; o órgão que vale para citar é o do FECHO, que só obter_inteiro_teor_tjse lê."),
    classe: z.string().optional().describe("Classe processual, ex. \"Apelação Cível\"."),
    relator: z.string().optional().describe("Nome ou parte do nome do relator."),
    numero: z.string().optional().describe("Processo (12 dígitos) ou acórdão (ano + sequencial, 5 a 9 dígitos: 202561964, 20266743). Dispensa consulta/grupos."),
    por_pagina: z.number().int().min(1).max(50).default(10).describe("Resultados por página (arredonda para 5, 10 ou 20). Comece em 10."),
    pagina: z.number().int().min(1).default(1).describe("Página, de 1 em diante."),
    data_inicio: z.string().optional().describe("dd/mm/aaaa — data de PUBLICAÇÃO do Boletim. O julgamento é do MÊS ANTERIOR à publicação."),
    data_fim: z.string().optional().describe("dd/mm/aaaa — data de PUBLICAÇÃO do Boletim."),
    ordenacao: z.enum(["relevantes", "recentes", "antigos"]).default("relevantes").describe("relevantes (bm25, padrão) | recentes | antigos."),
    exato: z.boolean().default(false).describe("true desliga a variação singular/plural."),
    em: z.string().default("tudo").describe("tudo | questao | tese | razoes | caso | dispositivo | cabecalho — combináveis (\"questao,tese\"). O cabeçalho entra sempre, com peso baixo."),
    cita: z.string().optional().describe("\"Tema 1061\", \"Súmula 479/STJ\", \"IRDR 15\", \"SV 47\" ou nº de processo do TJSE (12 dígitos)."),
  },
  annotations: SO_LEITURA,
}, seguro("busca_indice_local", (a) => buscar({ ...a, _relato: linkRelato })));

server.registerTool("obter_inteiro_teor_tjse", {
  title: "Obter o inteiro teor de um acórdão do TJSE",
  description: "Inteiro teor (ementa em caixa normal, fecho, relatório, voto) pelo link oficial que o Boletim publica. 1 requisição na primeira vez; depois lê o recibo do disco (0). " +
    "Órgão julgador e data saem do FECHO ('ACORDAM… Tribunal de Justiça do Estado de Sergipe, nesta …'), não do cadastro; a saída traz `orgao_fonte`. " +
    "`numero_processo` só é necessário se o acórdão não estiver no índice local — ou cole em `numero_acordao` a URL do inteiro teor. Saída cortada = 'lido EM PARTE'.",
  inputSchema: {
    numero_acordao: z.string().describe("Nº do acórdão (ano + sequencial, 5 a 9 dígitos, como sai na busca) — ou a URL do inteiro teor colada."),
    numero_processo: z.string().optional().describe("Nº do processo (12 dígitos); só se o acórdão não estiver no índice local."),
    com_partes: z.boolean().default(false).describe("true inclui o bloco de qualificação das partes (nomes). Padrão: cortado."),
    max_caracteres: z.number().int().min(2000).default(60000).describe("Corta a saída neste tamanho (o recibo guarda tudo)."),
  },
}, seguro("inteiro_teor", (a) => obter(a.numero_acordao, a.numero_processo ?? null, a.com_partes, a.max_caracteres)));

server.registerTool("verificar_citacao_tjse", {
  title: "Verificar citação literal no TJSE",
  description: "Confere se `trecho` aparece LITERALMENTE no inteiro teor (palavra inteira, sem acento/caixa; `[...]` separa fragmentos que devem vir em ordem). " +
    "Obrigatório antes de qualquer aspas — a ementa do Boletim é caixa alta e não serve de fonte literal. Mínimo de 4 palavras. " +
    "✅ pode vir com alertas — TRANSCRIÇÃO (trecho de outro tribunal copiado no voto), VOTO DIVERGENTE (pode ser o voto vencido), ALEGAÇÃO DA PARTE (relatório narrando o que a parte sustenta), " +
    "ENTRE ASPAS (o tribunal citando alguém), NEGAÇÃO (recorte que inverte o julgado): cada um muda A QUEM a frase pode ser atribuída. Falha de rede = citação NÃO CONFERIDA, nunca ❌.",
  inputSchema: {
    numero_acordao: z.string().describe("Nº do acórdão (ano + sequencial, 5 a 9 dígitos) — ou a URL do inteiro teor."),
    trecho: z.string().describe("Texto que se pretende citar entre aspas (cortes marcados com [...])."),
    numero_processo: z.string().optional().describe("Nº do processo (12 dígitos); só se o acórdão não estiver no índice local."),
  },
}, seguro("verificar_citacao", (a) => verificar(a.numero_acordao, a.trecho, a.numero_processo ?? null)));

server.registerTool("mapa_de_citacoes_tjse", {
  title: "Grafo de citações do índice do TJSE",
  description: "Grafo de citações do índice, montado do campo \"Jurisprudência relevante citada\" das ementas (zero rede). Sem `referencia`: os precedentes qualificados mais citados e os acórdãos do próprio TJSE que as câmaras mais reusam — " +
    "inclusive ANTERIORES ao período sincronizado, que a busca não alcança. Com `referencia` (\"Tema 1061\", \"Súmula 479/STJ\", \"IRDR 15\" ou nº de processo do TJSE): quais acórdãos do índice citam aquilo.",
  inputSchema: {
    referencia: z.string().optional().describe("\"Tema 1061\", \"Súmula 479/STJ\", \"IRDR 15\", \"SV 47\" ou processo do TJSE (12 dígitos). Vazio = panorama geral."),
    limite: z.number().int().min(3).max(50).default(15).describe("Quantos itens mostrar."),
  },
  annotations: SO_LEITURA,
}, seguro("mapa_citacoes", (a) => mapaCitacoes(a.referencia ?? null, a.limite)));

server.registerTool("importar_pacote_tjse", {
  title: "Importar o pacote pronto de julgados do TJSE",
  description: "Monta o índice a partir do HTML bruto do Boletim SEM sincronizar do portal do tribunal: baixa o pacote pronto do GitHub deste projeto (URL fixa, hash conferido), " +
    "extrai em ~/.tjse-jurisprudencia e reconstrói o índice. É o caminho rápido para quem instalou agora e ainda não tem julgados. " +
    "Com o índice vazio, baixa sozinho; `baixar=false` só importa o que já estiver em disco. Seguro repetir: o que já entrou não se refaz. O pacote cobre só até a data do release — para o resto, use sincronizar_boletim_tjse.",
  inputSchema: {
    baixar: z.boolean().optional().describe("true = baixa o pacote do GitHub e importa; false = só importa o que já está em disco; omitido = baixa se não houver nada."),
  },
}, seguro("importar_pacote", (a) => importarPacote(a.baixar, { prazoMs: Date.now() + orcamentoMs() })));

server.registerTool("diagnostico_tjse", {
  title: "Diagnóstico do índice e do ritmo (TJSE)",
  description: "Estado do disjuntor, consumo de requisições, cobertura do índice local, onde ficam os dados e incidentes. USE antes de concluir que 'o portal está fora do ar' ou de confiar em zero resultado. Sempre 0 requisições.",
  inputSchema: {},
  annotations: SO_LEITURA,
}, seguro("diagnostico", () => diagnostico()));

await server.connect(new StdioServerTransport());
