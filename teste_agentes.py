import boto3
import uuid

client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

response = client.invoke_agent(
    agentId="JO0SG5Z8EI",
    agentAliasId="TSTALIASID",  # use o draft para testar as mudancas novas
    sessionId=str(uuid.uuid4()),
    inputText=(
        "Voce e um medico psiquiatra especialista em TDAH adulto. "
        "Simule uma conversa com um propagandista da EMS sobre Lyberdia. "
        "Comece com uma objeção inicial curta e plausivel."
    ),
    enableTrace=True,
)

parts = []
for event in response["completion"]:
    chunk = event.get("chunk")
    if chunk and "bytes" in chunk:
        parts.append(chunk["bytes"].decode("utf-8", errors="replace"))

print("".join(parts))