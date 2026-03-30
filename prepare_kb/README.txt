Scripts separados da aplicação, para rodar com Python e preparar documentos antes de subir no Bedrock via console da AWS.

Arquivos:
- common_utils.py
- transform_bula.py
- transform_article.py
- transform_price_table.py

Exemplos de uso

1) Bula
python generate_bula_md.py Somalgin-Cardio.txt --drug-name "Somalgin Cardio" --outdir ./saida
2) Artigo ou tese
python transform_article.py tese.txt --outdir ./saida --title "Impacto Clinico do Tema X"

3) Tabela de preços
python transform_price_table.py precos.csv --outdir ./saida --table-name "Tabela EMS Abril 2026"

Saída de cada script
- arquivo markdown estruturado
- arquivo json estruturado

Fluxo recomendado
1. preparar o documento com o script adequado
2. revisar rapidamente o markdown/json gerado
3. subir o arquivo estruturado no S3/Bedrock via console
4. sincronizar a Knowledge Base
5. validar retrieval com perguntas de teste

Recomendação prática
- para bulas e textos longos: prefira subir o markdown estruturado
- para dados tabulares: json costuma funcionar melhor
