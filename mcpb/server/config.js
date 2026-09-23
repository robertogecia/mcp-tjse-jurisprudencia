// Configuração e constantes — porte de `servidor_tjse.py` (topo do arquivo).
// Caminhos são getters: o ambiente é lido na hora do uso, o que deixa os testes apontarem para pasta temporária.
import os from "node:os";
import path from "node:path";

export const VERSAO = "1.1.0";
export const BOLETIM = "https://diario.tjse.jus.br/revista/internet";
export const URL_TEOR = "https://www.tjse.jus.br/tjnet/jurisprudencia/relatorio.wsp";
export const URL_FORM_TURNSTILE = "https://www.tjse.jus.br/portal/consultas/jurisprudencia/judicial";

// Pasta de dados FORA da pasta da extensão: atualizar a extensão troca a pasta dela, e o índice (centenas de MB) não pode ir junto.
export const dirDados = () => process.env.TJSE_DIR_DADOS || path.join(os.homedir(), ".tjse-jurisprudencia");
export const dirBase = () => path.join(dirDados(), "base");
export const arqDb = () => path.join(dirBase(), "boletim.db");
export const dirSecoes = () => path.join(dirBase(), "secoes");   // HTML bruto de cada seção: reparse sem rede
export const dirRecibos = () => process.env.TJSE_DIR_RECIBOS || path.join(dirDados(), "recibos");
export const arqEstado = () => path.join(dirDados(), ".disjuntor_estado_tjse.json");

// User-Agent HONESTO por padrão: o cliente se identifica como o que é.
export const userAgent = () => process.env.TJSE_USER_AGENT || `tjse-jurisprudencia-mcp/${VERSAO} (pesquisa juridica; cliente MCP; ritmo limitado)`;
export const complementos = () => (process.env.TJSE_COMPLEMENTOS || "").split(";").map((c) => c.trim()).filter(Boolean);

// Ritmo. Portal pequeno (Apache 2.4.6), seção de câmara cível passa de 2 MB: devagar.
export const JANELA_S = 600;
export const DIA_MAX = 150;
export const MAX_REQ_POR_SINCRONIZACAO = 14;
export const PAUSA_BLOQUEIO_S = 6 * 3600;
export const PAUSA_DESAFIO_S = 24 * 3600;
export const PAUSA_ERRO_S = 30 * 60;
export const PAUSA_ILEGIVEL_S = 3600;
// Escada de ritmo: recusa do portal aperta um degrau; SUCESSOS_PARA_RELAXAR consultas limpas descem um.
export const ESCADA = [[6.0, 20], [12.0, 10], [30.0, 6], [60.0, 3]];   // [espaçamento em s, teto por janela de 10 min]
export const SUCESSOS_PARA_RELAXAR = 100;

// Só marcas inequívocas, e só ANTES do miolo: a ementa pode conter a palavra "captcha".
export const MARCAS_DESAFIO = ["cf-turnstile", "challenges.cloudflare.com", "just a moment", "código de segurança",
  "codigo de seguranca", "g-recaptcha", "h-captcha"];

export const REPO_GITHUB = "robertogecia/mcp-tjse-jurisprudencia";

export function ondeMaisProcurar() {
  const ponte = "Julgado do TJSE achado fora daqui se confere AQUI: `obter_inteiro_teor_tjse(numero_acordao, numero_processo)` " +
    "— ou cole a URL do inteiro teor em `numero_acordao` — e depois `verificar_citacao_tjse`.";
  const c = complementos();
  if (c.length) return `Para o que falta, consulte também: ${c.join(", ")} (declarado em TJSE_COMPLEMENTOS). ` + ponte;
  return `Para o que falta: pesquisa manual no portal oficial (${URL_FORM_TURNSTILE}), que exige verificação humana — este ` +
    "servidor não a usa nem contorna — ou qualquer base de jurisprudência que você assine. " + ponte;
}

/** Falha de rede/ritmo/bloqueio. NUNCA equivale a 'não localizado'. */
export class PesquisaNaoRealizada extends Error {
  constructor(msg) { super(msg); this.name = "PesquisaNaoRealizada"; }
}
/** Argumento inválido: vira "Pedido recusado", não erro interno (o ValueError do Python). */
export class PedidoRecusado extends Error {
  constructor(msg) { super(msg); this.name = "PedidoRecusado"; }
}
/** O ambiente não tem o que o servidor exige (SQLite embutido no Node, com FTS5). Mensagem própria: sem ela o usuário veria um erro críptico. */
export class AmbienteIncompativel extends Error {
  constructor(msg) { super(msg); this.name = "AmbienteIncompativel"; }
}
