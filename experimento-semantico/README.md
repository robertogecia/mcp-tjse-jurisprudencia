# Experimento: busca semântica, reranker e triagem (23/09/2026)

Pergunta: vale embutir busca por sentido (embeddings) ou um reranker na extensão?
20 perguntas em linguagem natural (`consultas.json`), 10 primeiros de cada método, relevância julgada às cegas
(`julgamento*.json`, nota 2 = trata diretamente do problema). Precisão@10: palavras 40,5% · semântica 34,5% · híbrida 38% ·
reranker 53,5% · **triagem (Claude reordena 30 candidatos) 59,5%**.

Scripts: `embed.py` (vetoriza as ementas; gera `vetores.npy`, 29 MB, não versionado), `comparar.py`, `rerank.py`.
Limites: 20 perguntas, um juiz (agente), julgamento pelo começo da ementa. Conclusão: semântica não compensa; o ganho vem de reordenar.
