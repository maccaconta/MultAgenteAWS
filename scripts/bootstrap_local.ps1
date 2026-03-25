# Ativa o ambiente virtual do projeto para isolar as dependencias Python.
.\.venv\Scripts\Activate.ps1

# Define uma chave local do Django para desenvolvimento.
$env:DJANGO_SECRET_KEY="dev-key"

# Mantem o modo debug ativo para facilitar logs e paginas de erro locais.
$env:DJANGO_DEBUG="true"

# Limita os hosts aceitos pelo servidor Django em ambiente local.
$env:DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost"

# Define a regiao onde sua Knowledge Base e os agentes do Bedrock existem.
$env:AWS_REGION="us-east-1"

# Informa o Access Key usado pelo boto3 e pela AWS CLI na sessao atual.
$env:AWS_ACCESS_KEY_ID="SEU_ACCESS_KEY"

# Informa o Secret Key correspondente ao Access Key acima.
$env:AWS_SECRET_ACCESS_KEY="SEU_SECRET_KEY"

# Informa o ID da Knowledge Base que sera associada ao agente de consulta.
$env:BEDROCK_KB_ID="SEU_KB_ID"

# Informa o ARN da role IAM exigida pelo create-agent para criar agentes Bedrock.
$env:BEDROCK_AGENT_ROLE_ARN="arn:aws:iam::123456789012:role/BedrockAgentExecutionRole"

# Define o modelo usado pelos agentes colaboradores de consulta e sintese.
$env:BEDROCK_TURN_MODEL_ID="amazon.nova-pro-v1:0"

# Define o modelo usado pelo agente avaliador.
$env:BEDROCK_EVALUATE_MODEL_ID="amazon.nova-pro-v1:0"

# Define o modelo usado pelo agente de compliance.
$env:BEDROCK_SUMMARIZE_MODEL_ID="amazon.nova-pro-v1:0"

# Define o modelo do supervisor multiagente.
$env:BEDROCK_SUPERVISOR_MODEL_ID="amazon.nova-pro-v1:0"

# Mantem os traces do InvokeAgent ligados para auditar a colaboracao entre agentes.
$env:BEDROCK_ENABLE_TRACE="true"

# Usa SQLite para o primeiro bootstrap local.
$env:DB_ENGINE="django.db.backends.sqlite3"
$env:DB_NAME="db.sqlite3"
