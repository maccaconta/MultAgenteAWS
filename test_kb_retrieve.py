#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

import boto3


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa retrieval direto da Knowledge Base do Bedrock.")
    parser.add_argument("--kb-id", required=True, help="Knowledge Base ID")
    parser.add_argument("--query", required=True, help="Pergunta para testar")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--top-k", type=int, default=5, help="Quantidade de chunks retornados")
    args = parser.parse_args()

    client = boto3.client("bedrock-agent-runtime", region_name=args.region)

    response = client.retrieve(
        knowledgeBaseId=args.kb_id,
        retrievalQuery={"text": args.query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": args.top_k
            }
        },
    )

    results = response.get("retrievalResults", [])
    print(f"\nKB: {args.kb_id}")
    print(f"Pergunta: {args.query}")
    print(f"Resultados: {len(results)}\n")

    for i, item in enumerate(results, start=1):
        content = (item.get("content") or {}).get("text", "")
        score = item.get("score")
        location = item.get("location", {})
        metadata = item.get("metadata", {})

        print("=" * 90)
        print(f"RESULTADO #{i}")
        print(f"score: {score}")
        print(f"location: {json.dumps(location, ensure_ascii=False, indent=2)}")
        if metadata:
            print(f"metadata: {json.dumps(metadata, ensure_ascii=False, indent=2)}")
        print("-" * 90)
        print(content[:4000].strip() or "[sem texto]")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())