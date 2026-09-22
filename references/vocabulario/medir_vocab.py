#!/usr/bin/env python3
"""Mede o ganho do dicionário de sinônimos (sinonimos.json) sobre a busca do TJSE.

Compara, para cada consulta do gold.json:
  (a) os grupos de sinônimos ORIGINAIS do harness (harness/medir.py, GRUPOS_SINONIMOS)
  (b) os MESMOS grupos ENRIQUECIDOS com termos do dicionário (só acrescenta, nunca remove)

NÃO altera harness/gold.json nem harness/medir.py — apenas os lê (gabarito).
NÃO toca em servidor_tjse.py nem no banco original.

Roda contra a cópia isolada do banco em /tmp/vocab (TJSE_DIR_DADOS), zero rede.

Uso:
    TJSE_DIR_DADOS=/tmp/vocab ~/MCP/tjse-jurisprudencia/.venv/bin/python \
        references/vocabulario/medir_vocab.py
"""
import os
import re
import sys
import json

os.environ.setdefault("TJSE_DIR_DADOS", "/tmp/vocab")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ~/MCP/tjse-jurisprudencia
sys.path.insert(0, BASE)
import servidor_tjse as srv  # noqa: E402

HARNESS_DIR = os.path.join(BASE, "harness")
VOCAB_DIR = os.path.dirname(os.path.abspath(__file__))

GOLD_PATH = os.path.join(HARNESS_DIR, "gold.json")
DB_INDEX_PATH = os.path.join(HARNESS_DIR, "_db_index.json")
SINONIMOS_PATH = os.path.join(VOCAB_DIR, "sinonimos.json")

PADRAO_ACORDAO = re.compile(r"■\s*Acórdão\s+(\d+)")
POR_PAGINA_MAX = 20

# Grupos de sinônimos originais do harness — reproduzidos aqui em vez de importados
# porque harness/medir.py não expõe o dict como módulo público reutilizável e a
# regra do exercício proíbe editar harness/. Mantidos EXATAMENTE como no gabarito.
GRUPOS_SINONIMOS_ORIGINAIS = {
    "t1_bancario_idoso_analfabeto": [
        ["idoso", "analfabeto", "analfabetismo", "hipervulnerável", "iletrado"],
        ["empréstimo consignado", "cartão consignado", "contrato bancário", "cartão de crédito consignado"],
        ["impugnação", "fraude", "inexistência de débito", "assinatura a rogo", "não contratação"],
    ],
    "t2_plano_saude_autismo": [
        ["plano de saúde", "saúde suplementar"],
        ["autismo", "transtorno do espectro autista", "TEA"],
        ["tratamento multidisciplinar", "terapia", "método ABA", "cobertura"],
    ],
    "t3_cartao_consignado_rmc": [
        ["cartão de crédito consignado", "cartão consignado", "RMC", "RCC", "reserva de margem consignável"],
        ["contratação impugnada", "fraude", "inexistência de débito", "não reconhecimento"],
        ["INSS", "benefício previdenciário", "aposentado"],
    ],
    "t4_negativacao_dano_moral": [
        ["negativação", "inscrição indevida", "cadastro de inadimplentes", "SPC", "Serasa", "protesto"],
        ["dano moral", "indenização", "quantum indenizatório"],
        ["débito não reconhecido", "inexistência de débito", "fraude"],
    ],
    "t5_responsabilidade_civil_estado": [
        ["responsabilidade civil do Estado", "responsabilidade civil objetiva do Estado"],
        ["omissão", "falha na prestação do serviço público", "art. 37 §6º"],
        ["hospital público", "SUS", "erro médico", "acidente", "detento", "abordagem policial"],
    ],
    "t6_usucapiao": [
        ["usucapião", "prescrição aquisitiva"],
        ["posse mansa e pacífica", "animus domini", "posse ininterrupta"],
        ["usucapião extraordinária", "usucapião ordinária", "usucapião especial urbana", "usucapião especial rural"],
    ],
}

# Mapeia qid do gold -> conceitos do dicionário cujos termos entram nos grupos daquela
# consulta (um conceito pode alimentar mais de um grupo/consulta).
CONCEITOS_POR_CONSULTA = {
    "t1_bancario_idoso_analfabeto": ["idoso_analfabeto_bancario"],
    "t2_plano_saude_autismo": ["plano_saude_autismo"],
    "t3_cartao_consignado_rmc": ["cartao_consignado_rmc"],
    "t4_negativacao_dano_moral": ["negativacao_dano_moral"],
    "t5_responsabilidade_civil_estado": ["responsabilidade_civil_estado"],
    "t6_usucapiao": ["usucapiao"],
}

# Para cada consulta, a qual GRUPO (índice, 0-based, na lista de grupos original)
# os termos do conceito devem ser ACRESCENTADOS. Feito manualmente porque o dicionário
# não sabe a que "papel" sintático (sujeito/objeto/qualificador) cada termo pertence
# dentro da consulta — essa é a única curadoria humana desta etapa, o resto é dado.
GRUPO_DESTINO = {
    "t1_bancario_idoso_analfabeto": 0,   # grupo do "idoso/analfabeto"
    "t2_plano_saude_autismo": 1,          # grupo do "autismo/TEA"
    "t3_cartao_consignado_rmc": 0,        # grupo do "cartão/RMC/RCC"
    "t4_negativacao_dano_moral": 0,       # grupo da "negativação/inscrição indevida"
    "t5_responsabilidade_civil_estado": 2,  # grupo do "hospital/erro médico/detento/..."
    "t6_usucapiao": 0,                    # grupo do "usucapião"
}


def enriquecer(qid):
    """Devolve uma cópia dos grupos originais com os termos do dicionário ACRESCENTADOS
    (nunca removidos) no grupo destino."""
    grupos = json.loads(json.dumps(GRUPOS_SINONIMOS_ORIGINAIS[qid]))  # deep copy
    sinonimos = json.load(open(SINONIMOS_PATH, encoding="utf-8"))
    by_conceito = {c["conceito"]: c for c in sinonimos["conceitos"]}
    idx_destino = GRUPO_DESTINO[qid]
    existentes = {t.lower() for t in grupos[idx_destino]}
    for nome_conceito in CONCEITOS_POR_CONSULTA[qid]:
        conceito = by_conceito[nome_conceito]
        for t in conceito["termos"]:
            termo = t["termo"]
            if termo.lower() not in existentes:
                grupos[idx_destino].append(termo)
                existentes.add(termo.lower())
    return grupos


def extrair_acordaos(texto_resultado):
    return [m.group(1) for m in PADRAO_ACORDAO.finditer(texto_resultado)]


def paginar_tudo(**kwargs):
    todos = []
    pagina = 1
    while pagina <= 10:
        texto = srv.buscar(por_pagina=POR_PAGINA_MAX, pagina=pagina, **kwargs)
        ids_pagina = extrair_acordaos(texto)
        if not ids_pagina:
            break
        todos.extend(ids_pagina)
        if len(ids_pagina) < POR_PAGINA_MAX:
            break
        pagina += 1
    return todos


def recall_em(ordem, essenciais, k):
    janela = ordem if k is None else ordem[:k]
    achados = essenciais & set(janela)
    return achados, (len(achados) / len(essenciais) if essenciais else float("nan"))


def main():
    gold = json.load(open(GOLD_PATH, encoding="utf-8"))
    db = json.load(open(DB_INDEX_PATH, encoding="utf-8"))

    linhas = []
    linhas.append("# Medição de vocabulário — antes/depois do dicionário de sinônimos (TJSE)")
    linhas.append("")
    linhas.append("Banco medido: cópia isolada em `/tmp/vocab/base/boletim.db` (TJSE_DIR_DADOS).")
    linhas.append("Gabarito: `harness/gold.json` (não alterado). Grupos originais: `harness/medir.py` "
                   "(reproduzidos aqui, não importados, porque harness/ não pode ser editado nem importado "
                   "como dependência do vocabulário).")
    linhas.append("")
    linhas.append("## Tabela antes/depois")
    linhas.append("")
    linhas.append("| Consulta | Forma | essenciais | recall@10 | recall@50 | recall total |")
    linhas.append("|---|---|---|---|---|---|")

    resultado = {}
    for item in gold:
        qid = item["id"]
        essenciais = {i["acordao"] for i in item["itens"] if i["nivel"] == "essencial"}

        grupos_originais = GRUPOS_SINONIMOS_ORIGINAIS[qid]
        grupos_enriquecidos = enriquecer(qid)

        resultado[qid] = {}
        for forma_nome, grupos in [("original", grupos_originais), ("enriquecido", grupos_enriquecidos)]:
            try:
                ordem = paginar_tudo(grupos=grupos)
                erro = None
            except Exception as e:
                ordem = []
                erro = repr(e)

            _, r10 = recall_em(ordem, essenciais, 10)
            _, r50 = recall_em(ordem, essenciais, 50)
            achadosT, rT = recall_em(ordem, essenciais, None)
            perdidos = sorted(essenciais - achadosT)

            linhas.append(f"| {qid} | {forma_nome} | {len(essenciais)} | {r10:.0%} | {r50:.0%} | {rT:.0%} |")
            resultado[qid][forma_nome] = {
                "total_retornado": len(ordem),
                "recall@10": r10, "recall@50": r50, "recall_total": rT,
                "perdidos": perdidos, "erro": erro,
                "n_termos_grupo_destino": len(grupos[GRUPO_DESTINO[qid]]),
            }

    linhas.append("")
    linhas.append("## Delta por consulta (enriquecido − original)")
    linhas.append("")
    linhas.append("| Consulta | Δ recall@10 | Δ recall@50 | Δ recall total |")
    linhas.append("|---|---|---|---|")
    for qid in resultado:
        o, e = resultado[qid]["original"], resultado[qid]["enriquecido"]
        linhas.append(f"| {qid} | {(e['recall@10']-o['recall@10'])*100:+.0f}pp "
                       f"| {(e['recall@50']-o['recall@50'])*100:+.0f}pp "
                       f"| {(e['recall_total']-o['recall_total'])*100:+.0f}pp |")

    linhas.append("")
    linhas.append("## Essenciais ainda perdidos depois do enriquecimento, por consulta")
    linhas.append("")
    for item in gold:
        qid = item["id"]
        perdidos = resultado[qid]["enriquecido"]["perdidos"]
        itens_por_id = {i["acordao"]: i for i in item["itens"]}
        linhas.append(f"### {qid} — {len(perdidos)} ainda perdido(s) após enriquecimento")
        linhas.append("")
        if not perdidos:
            linhas.append("(nenhum)")
        for a in perdidos:
            info = db.get(a, {})
            just = itens_por_id.get(a, {}).get("justificativa", "")
            linhas.append(f"- Acórdão {a} ({info.get('classe','?')}) — {just}")
        linhas.append("")

    out_path = os.path.join(VOCAB_DIR, "medicao-vocabulario.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    with open(os.path.join(VOCAB_DIR, "_resultado_vocab.json"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("\n".join(linhas))
    print(f"\n... escrito em {out_path}")


if __name__ == "__main__":
    main()
