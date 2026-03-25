import boto3
import json

client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

response = client.invoke_agent(
    agentId="MLP8GVTSYX",
    agentAliasId="OKCD2OFZBR",
    sessionId="teste-consulta-direta-001",
    inputText="No documento sobre Somalgin Cardio, quem e o farmaceutico responsavel?",
    enableTrace=True,
)

chunks = []
for event in response["completion"]:
    if "chunk" in event:
        data = event["chunk"]["bytes"]
        if isinstance(data, bytes):
            chunks.append(data.decode("utf-8", errors="ignore"))
        else:
            chunks.append(str(data))

print("".join(chunks))