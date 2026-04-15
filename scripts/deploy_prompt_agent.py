"""Deploy a prompt agent to Azure AI Foundry."""

import argparse
import os
import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential


def deploy(agent_name: str, model: str, prompt_file: str, version: str) -> None:
    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint:
        print("ERROR: FOUNDRY_PROJECT_ENDPOINT environment variable not set")
        sys.exit(1)

    client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    instructions = Path(prompt_file).read_text(encoding="utf-8")

    definition = PromptAgentDefinition(
        model=model,
        instructions=instructions,
    )

    agent = client.agents.create_version(
        agent_name=agent_name,
        definition=definition,
        description=f"Deployed from commit {version}",
    )

    print(f"Deployed: {agent.name} v{agent.version} (id: {agent.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy prompt agent to Foundry")
    parser.add_argument("--agent-name", required=True, help="Name of the agent")
    parser.add_argument("--model", required=True, help="Model deployment name")
    parser.add_argument("--prompt-file", required=True, help="Path to prompt.md")
    parser.add_argument("--version", default="local", help="Version tag (e.g., git SHA)")
    args = parser.parse_args()

    deploy(args.agent_name, args.model, args.prompt_file, args.version)


if __name__ == "__main__":
    main()
