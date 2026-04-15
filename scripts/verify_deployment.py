"""Verify that a prompt agent was deployed successfully."""

import os
import sys

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def verify(agent_name: str) -> None:
    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint:
        print("ERROR: FOUNDRY_PROJECT_ENDPOINT environment variable not set")
        sys.exit(1)

    client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    agent = client.agents.get_latest_version(agent_name)
    print(f"Agent: {agent.name}")
    print(f"Version: {agent.version}")
    print(f"ID: {agent.id}")
    print(f"Model: {agent.definition.model}")
    print("Status: DEPLOYED")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "demo-prompt-agent"
    verify(name)
