# Medição de vocabulário — antes/depois do dicionário de sinônimos (TJSE)

Banco medido: cópia isolada em `/tmp/vocab/base/boletim.db` (TJSE_DIR_DADOS).
Gabarito: `harness/gold.json` (não alterado). Grupos originais: `harness/medir.py` (reproduzidos aqui, não importados, porque harness/ não pode ser editado nem importado como dependência do vocabulário).

## Tabela antes/depois

| Consulta | Forma | essenciais | recall@10 | recall@50 | recall total |
|---|---|---|---|---|---|
| t1_bancario_idoso_analfabeto | original | 18 | 6% | 33% | 44% |
| t1_bancario_idoso_analfabeto | enriquecido | 18 | 6% | 28% | 56% |
| t2_plano_saude_autismo | original | 15 | 7% | 40% | 80% |
| t2_plano_saude_autismo | enriquecido | 15 | 20% | 47% | 80% |
| t3_cartao_consignado_rmc | original | 18 | 0% | 11% | 39% |
| t3_cartao_consignado_rmc | enriquecido | 18 | 6% | 11% | 33% |
| t4_negativacao_dano_moral | original | 18 | 6% | 11% | 50% |
| t4_negativacao_dano_moral | enriquecido | 18 | 0% | 28% | 56% |
| t5_responsabilidade_civil_estado | original | 14 | 36% | 79% | 79% |
| t5_responsabilidade_civil_estado | enriquecido | 14 | 29% | 86% | 86% |
| t6_usucapiao | original | 15 | 27% | 53% | 53% |
| t6_usucapiao | enriquecido | 15 | 27% | 53% | 53% |

## Delta por consulta (enriquecido − original)

| Consulta | Δ recall@10 | Δ recall@50 | Δ recall total |
|---|---|---|---|
| t1_bancario_idoso_analfabeto | +0pp | -6pp | +11pp |
| t2_plano_saude_autismo | +13pp | +7pp | +0pp |
| t3_cartao_consignado_rmc | +6pp | +0pp | -6pp |
| t4_negativacao_dano_moral | -6pp | +17pp | +6pp |
| t5_responsabilidade_civil_estado | -7pp | +7pp | +7pp |
| t6_usucapiao | +0pp | +0pp | +0pp |

## Essenciais ainda perdidos depois do enriquecimento, por consulta

### t1_bancario_idoso_analfabeto — 8 ainda perdido(s) após enriquecimento

- Acórdão 202620093 (Apelação Cível) — hipervulnerabilidade do consumidor idoso citada na ementa
- Acórdão 202627962 (Apelação Cível) — tarifas bancárias em conta de idoso analfabeto
- Acórdão 202628034 (Apelação Cível) — avalista com alegação de analfabetismo e vício de consentimento — vocabulário 'avalista', fato societário diferente (cédula bancária)
- Acórdão 202630290 (Apelação Cível) — desconto indevido em benefício de idoso, ausência de autorização expressa
- Acórdão 202630444 (Apelação Cível) — responsabilidade civil de instituição financeira por desconto indevido a idoso
- Acórdão 202631590 (Apelação Cível) — beneficiário do INSS em condição de analfabetismo
- Acórdão 202631649 (Apelação Cível) — consumidor analfabeto em hipervulnerabilidade, tarifas bancárias
- Acórdão 202640450 (Apelação Cível) — consumidor analfabeto e hipervulnerável — termo 'hipervulnerável'

### t2_plano_saude_autismo — 3 ainda perdido(s) após enriquecimento

- Acórdão 202627175 (Apelação Cível) — cerceamento de defesa, TEA, indeferimento de instrução probatória
- Acórdão 202630202 (Apelação Cível) — contrato coletivo empresarial, nulidade de reajustes — mesma arena (plano de saúde) mas ângulo de reajuste, não de autismo: mantido como essencial por tocar diretamente cobertura/plano de saúde do mesmo núcleo de casos
- Acórdão 202630316 (Agravo de Instrumento) — cancelamento unilateral pelo plano de saúde de menor em tratamento de autismo

### t3_cartao_consignado_rmc — 12 ainda perdido(s) após enriquecimento

- Acórdão 202626590 (Apelação Cível) — RMC, não comprovação da contratação pela instituição financeira
- Acórdão 202626737 (Apelação Cível) — comprovação de contratação por via digital, exercício regular de direito
- Acórdão 202627006 (Apelação Cível) — ausência de desbloqueio do cartão, falha na prestação do serviço, dano moral por 'quantum'
- Acórdão 202627682 (Apelação Cível) — RMC, ação declaratória de inexistência de débito
- Acórdão 202627718 (Apelação / Remessa Necessária) — nulidade de contrato de cartão de crédito com RMC — usa 'numerário'/'pactuação' no corpo
- Acórdão 202627809 (Apelação Cível) — preclusão temporal por juntada de documentos em fase recursal — ângulo processual do mesmo tema
- Acórdão 202628695 (Apelação Cível) — 'cartão benefício consignado (RCC)' — sigla RCC em vez de RMC
- Acórdão 202629208 (Apelação Cível) — comportamento processual contraditório do autor (venire contra factum proprium)
- Acórdão 202629275 (Apelação Cível) — negativa de contratação via RMC
- Acórdão 202629277 (Apelação Cível) — BPC/LOAS, menor absolutamente incapaz — vocabulário 'LOAS'/'incapaz' em vez de 'consumidor'
- Acórdão 202641877 (Apelação Cível) — obrigação de fazer c/c indenização, RMC
- Acórdão 202642176 (Apelação Cível) — RMC, termo de consentimento eletrônico

### t4_negativacao_dano_moral — 8 ainda perdido(s) após enriquecimento

- Acórdão 202626707 (Apelação Cível) — anotação no Sistema de Informações de Crédito do Banco Central (SCR) — vocabulário 'SCR' em vez de 'negativação'
- Acórdão 202627052 (Apelação Cível) — inscrições preexistentes legítimas, Súmula 385 do STJ afastando indenização
- Acórdão 202627708 (Apelação Cível) — falha na prestação do serviço, inscrição indevida em cadastro de inadimplentes
- Acórdão 202628613 (Apelação Cível) — inscrição do nome da autora em cadastros de restrição ao crédito
- Acórdão 202629205 (Apelação Cível) — negativação em cadastro de inadimplentes por cartão de crédito, desconhecimento da relação jurídica
- Acórdão 202630098 (Apelação Cível) — inscrição indevida do nome do autor
- Acórdão 202639992 (Embargos de Declaração Cível) — negativação indevida, dano moral, embargos sobre o 'quantum'
- Acórdão 202640407 (Apelação Cível) — ausência de comprovação da contratação, negativação indevida, preexistência de outras inscrições (Súmula 385)

### t5_responsabilidade_civil_estado — 2 ainda perdido(s) após enriquecimento

- Acórdão 202623326 (Apelação Cível) — ilegitimidade passiva do Estado de Sergipe em ação de indenização
- Acórdão 202627081 (Apelação Cível) — lixão a céu aberto instalado por Município, dano ambiental/vizinhança — vocabulário fora do padrão médico/policial

### t6_usucapiao — 7 ainda perdido(s) após enriquecimento

- Acórdão 202627260 (Apelação Cível) — usucapião extraordinário urbano sobre imóvel objeto de herança
- Acórdão 202627723 (Apelação Cível) — ação de usucapião, honorários de defensor dativo
- Acórdão 202628302 (Apelação Cível) — usucapião de terreno de marinha com aforamento, competência da Justiça Federal
- Acórdão 202628894 (Apelação Cível) — usucapião extraordinário, inclusão de área pública no imóvel usucapiendo
- Acórdão 202639016 (Embargos de Declaração Cível) — usucapião extraordinária, embargos de declaração sobre os requisitos
- Acórdão 202640644 (Apelação Cível) — usucapião extraordinária, extinção por abandono da causa
- Acórdão 202642126 (Apelação Cível) — usucapião ordinário procedente, art. 1.242 do Código Civil
