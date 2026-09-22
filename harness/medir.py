#!/usr/bin/env python3
"""Harness de qualidade de busca do MCP tjse_jurisprudencia.

Mede recall@10, recall@50 e recall total dos itens ESSENCIAIS do gold.json,
rodando buscar() do servidor real contra uma CÓPIA do banco (/tmp/goldtjse).

Duas formas de busca por consulta:
  (a) consulta livre, a pergunta em português corrente
  (b) grupos de sinônimos, como um pesquisador experiente montaria

Uso:
    ~/MCP/tjse-jurisprudencia/.venv/bin/python harness/medir.py
"""
import os
import re
import sys
import json

# ANTES de importar servidor_tjse: aponta para a cópia do banco, nunca o original.
os.environ["TJSE_DIR_DADOS"] = "/tmp/goldtjse"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import servidor_tjse as srv  # noqa: E402

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
GOLD_PATH = os.path.join(HARNESS_DIR, "gold.json")

PADRAO_ACORDAO = re.compile(r"■\s*Acórdão\s+(\d+)")
POR_PAGINA_MAX = 20  # o servidor satura por_pagina em 20 (ver servidor_tjse._buscar)

# Grupos de sinônimos "de pesquisador experiente" para a forma (b) — um por consulta,
# na mesma ordem do gold.json.
GRUPOS_SINONIMOS = {
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


def extrair_acordaos(texto_resultado):
    return [m.group(1) for m in PADRAO_ACORDAO.finditer(texto_resultado)]


def paginar_tudo(**kwargs):
    """Roda buscar() paginando com por_pagina=20 até esgotar ou até 200 resultados (10 páginas),
    devolvendo a lista de acórdãos NA ORDEM DE RETORNO (ordem de relevância do servidor)."""
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
    if k is None:
        janela = ordem
    else:
        janela = ordem[:k]
    achados = essenciais & set(janela)
    return achados, (len(achados) / len(essenciais) if essenciais else float("nan"))


def main():
    gold = json.load(open(GOLD_PATH, encoding="utf-8"))
    db = json.load(open(os.path.join(HARNESS_DIR, "_db_index.json"), encoding="utf-8"))

    linhas_md = []
    linhas_md.append("# Medição de recall — TJSE jurisprudência (índice local)")
    linhas_md.append("")
    linhas_md.append(f"Banco medido: cópia em `/tmp/goldtjse/base/boletim.db` (TJSE_DIR_DADOS).")
    linhas_md.append("")
    linhas_md.append("## Tabela de recall por consulta e forma")
    linhas_md.append("")
    linhas_md.append("| Consulta | Forma | essenciais | recall@10 | recall@50 | recall total |")
    linhas_md.append("|---|---|---|---|---|---|")

    resultado_completo = {}

    for item in gold:
        qid = item["id"]
        pergunta = item["pergunta"]
        essenciais = {i["acordao"] for i in item["itens"] if i["nivel"] == "essencial"}
        itens_por_id = {i["acordao"]: i for i in item["itens"]}

        formas = {
            "consulta_livre": {"consulta": pergunta},
            "grupos_sinonimos": {"grupos": GRUPOS_SINONIMOS[qid]},
        }

        resultado_completo[qid] = {"pergunta": pergunta, "n_essenciais": len(essenciais), "formas": {}}

        for forma_nome, kwargs in formas.items():
            try:
                ordem = paginar_tudo(**kwargs)
                erro = None
            except Exception as e:
                ordem = []
                erro = repr(e)

            achados10, r10 = recall_em(ordem, essenciais, 10)
            achados50, r50 = recall_em(ordem, essenciais, 50)
            achadosT, rT = recall_em(ordem, essenciais, None)
            perdidos = essenciais - achadosT

            linhas_md.append(
                f"| {qid} | {forma_nome} | {len(essenciais)} | {r10:.0%} | {r50:.0%} | {rT:.0%} |"
            )

            resultado_completo[qid]["formas"][forma_nome] = {
                "total_retornado": len(ordem),
                "recall@10": r10,
                "recall@50": r50,
                "recall_total": rT,
                "perdidos": sorted(perdidos),
                "erro": erro,
            }

    with open(os.path.join(HARNESS_DIR, "_resultado_bruto.json"), "w", encoding="utf-8") as f:
        json.dump(resultado_completo, f, ensure_ascii=False, indent=2)

    # ---- lista nominal de perdidos, com trecho de ementa ----
    linhas_md.append("")
    linhas_md.append("## Essenciais NÃO encontrados (recall total), por consulta e forma")
    linhas_md.append("")

    for item in gold:
        qid = item["id"]
        itens_por_id = {i["acordao"]: i for i in item["itens"]}
        for forma_nome in ["consulta_livre", "grupos_sinonimos"]:
            perdidos = resultado_completo[qid]["formas"][forma_nome]["perdidos"]
            if not perdidos:
                continue
            linhas_md.append(f"### {qid} — {forma_nome} — {len(perdidos)} perdido(s)")
            linhas_md.append("")
            for a in perdidos:
                info = db.get(a, {})
                just = itens_por_id.get(a, {}).get("justificativa", "")
                ementa_trecho = (info.get("ementa", "") or "")[:200].replace("\n", " ")
                linhas_md.append(f"- **Acórdão {a}** ({info.get('classe','?')}, rel. {info.get('relator','?')}) "
                                  f"— por que é essencial: {just}")
                linhas_md.append(f"  - ementa (200c): {ementa_trecho}...")
            linhas_md.append("")

    out_md = os.path.join(HARNESS_DIR, "medicao-2026-09-21.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_md))

    print("\n".join(linhas_md[:40]))
    print(f"\n... escrito em {out_md} e _resultado_bruto.json")


if __name__ == "__main__":
    main()
