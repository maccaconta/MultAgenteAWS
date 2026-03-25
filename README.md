# EMS Django + Amazon Bedrock Agents

Esta versao do projeto foi refatorada para que a **execucao agentica ocorra nos agentes nativos do Amazon Bedrock**. O Django permanece como camada de sustentacao da aplicacao: interface, banco, persistencia da conversa, catalogo de templates, WebSocket/Socket.IO, endpoints e auditoria.

## Arquitetura de alto nivel

- **Django**: UI, admin, persistencia e mensageria da aplicacao.
- **Amazon Bedrock Agents**: supervisor + colaboradores nativos.
- **Knowledge Base**: associada ao agente de consulta.
- **Templates no banco**: continuam sendo a fonte da verdade para persona, cenario, especialidade, politicas, contrato de saida e rubrica.
- **Manifesto local**: guarda os `agent_id` e `alias_id` criados para cada blueprint, para que novas sessoes reutilizem o mesmo time.

## Time de agentes Bedrock usado

- `consultation`: busca evidencias e fatos na Knowledge Base.
- `synthesis`: responde como o medico simulado.
- `compliance`: valida claims, limites promocionais e reescritas seguras.
- `evaluation`: pontua o propagandista e gera coaching.
- `supervisor`: coordena os colaboradores e devolve um JSON final ao Django.

## Fluxo de execucao

1. O usuario escolhe blueprint, persona, cenario e especialidade na UI.
2. O Django cria a sessao e carrega o time Bedrock vinculado ao blueprint.
3. A tela envia a mensagem via WebSocket.
4. O backend chama `InvokeAgent` no supervisor Bedrock.
5. O supervisor usa os colaboradores Bedrock nativos quando necessario.
6. O Django persiste a resposta final, traces e avaliacao.

## Estrutura relevante

- `core/config.py`: leitura central das variaveis de ambiente.
- `apps/agents/provisioning.py`: cria o time Bedrock nativo.
- `apps/agents/services.py`: invoca o supervisor no runtime.
- `apps/agents/bedrock.py`: clientes de control plane e runtime.
- `apps/agents/team_registry.py`: manifesto local dos agentes por blueprint.
- `apps/realtime/consumers.py`: integra WebSocket e `InvokeAgent`.

## Passo a passo local no PowerShell

```powershell
# Entra na pasta do projeto para que os comandos usem o manage.py correto.
cd .\ems_django_multiagent

# Cria o ambiente virtual Python para isolar dependencias do projeto.
python -m venv .venv

# Ativa o ambiente virtual no PowerShell atual.
.\.venv\Scripts\Activate.ps1

# Instala Django, Channels, boto3 e demais dependencias declaradas no projeto.
pip install -r requirements.txt

# Copia o arquivo de exemplo de variaveis para um .env local que voce pode editar.
Copy-Item .env.example .env

# Abre o .env no Bloco de Notas para preencher credenciais, KB ID e role ARN.
notepad .env

# Executa as migrations do Django para criar as tabelas da aplicacao.
python manage.py migrate

# Cria um usuario administrador para acessar o Django Admin.
python manage.py createsuperuser

# Carrega o catalogo inicial de templates, personas, cenarios e blueprints.
python manage.py shell -c "from apps.catalog.seed_data import seed_default_catalog; seed_default_catalog()"

# Cria o time de agentes Bedrock nativos para o blueprint informado.
python manage.py provision_bedrock_team --blueprint turno_padrao_telemedicina

# Sobe a aplicacao em modo de desenvolvimento com suporte ASGI/Channels.
python manage.py runserver
```

## Como descobrir a role ARN para `BEDROCK_AGENT_ROLE_ARN`

A criacao de agentes pelo comando `create-agent` exige uma IAM role com permissao para o agente acessar os recursos necessarios. O comando de AWS CLI para criar agente pede `agentResourceRoleArn`. citeturn944307search3

No console da AWS, a role pode ser encontrada em **IAM > Roles**. Em CLI, voce pode listar roles e localizar a que foi preparada para Bedrock Agents.

```powershell
# Lista as roles da conta para voce localizar a role de execucao dos agentes Bedrock.
aws iam list-roles --query "Roles[].[RoleName,Arn]" --output table
```

## Como os agentes Bedrock entram em operacao

Para usar um agente na aplicacao, voce precisa prepara-lo e criar um alias; depois a aplicacao usa `InvokeAgent` com `agentId` e `agentAliasId`. Isso e o fluxo oficial do Bedrock Agents. citeturn944307search7turn545637search8

O projeto faz isso automaticamente no comando `provision_bedrock_team`.

## Observacoes importantes

- O Bedrock suporta colaboracao multiagente com um supervisor e colaboradores associados. O limite documentado atual para colaboradores associados ao supervisor e 10. citeturn944307search1turn944307search8
- O `InvokeAgent` pode receber `sessionState` com `sessionAttributes` e `promptSessionAttributes`, o que o projeto usa para injetar o contexto da sessao vindo do Django. citeturn545637search1turn545637search5turn545637search6
- A response do `InvokeAgent` pode incluir `chunk` e `trace`; o projeto persiste ambos no banco para auditoria. citeturn545637search0turn545637search2

## O que ainda falta antes de producao

- autenticar o usuario final e proteger o acesso por tenant;
- trocar `InMemoryChannelLayer` por Redis;
- definir uma role IAM dedicada para os agentes Bedrock;
- endurecer as politicas de compliance por produto e indicacao;
- adicionar testes de contrato para o JSON final do supervisor.


# Guarda na sessão atual o ARN da IAM Role que será usada pelos agentes Bedrock.
# Essa role é passada no create-agent como agentResourceRoleArn.
$env:BEDROCK_AGENT_ROLE_ARN="arn:aws:iam::746443183845:role/BedrockAgentsServiceRole"

# Confere se a variável ficou carregada corretamente.
$env:BEDROCK_AGENT_ROLE_ARN

# Define a região usada pelos comandos Bedrock nesta sessão do PowerShell.
$env:AWS_REGION="us-east-1"

# Mostra a região atualmente carregada.
$env:AWS_REGION