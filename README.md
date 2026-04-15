# Foundry Agent Demo

A simple prompt agent deployed to Azure AI Foundry via GitHub Actions.

## Project Structure

```
foundry-agent-demo/
├── .github/
│   └── workflows/
│       └── deploy-prompt-agent.yml   # CI/CD pipeline
├── agents/
│   └── prompt.md                     # Agent instructions
├── scripts/
│   ├── deploy_prompt_agent.py        # Deploy script (SDK)
│   └── verify_deployment.py          # Post-deploy verification
├── tests/
│   ├── test_prompt.py                # Prompt validation tests
│   └── test_deploy_script.py         # Script validation tests
├── requirements.txt                  # Python dependencies
└── README.md
```

## Prerequisites

### 1. Azure AI Foundry
- A Foundry project with an endpoint
- A chat model deployment (e.g., `gpt-5.2`)
- An Azure AD app registration with OIDC federation for GitHub

### 2. GitHub Repository Setup

#### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | Azure AD app client ID |
| `AZURE_TENANT_ID` | Your Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Your Azure subscription ID |

#### Variables (Settings → Secrets and variables → Actions → Variables)

| Variable | Value |
|---|---|
| `FOUNDRY_PROJECT_ENDPOINT` | `https://{account}.services.ai.azure.com/api/projects/{project}` |
| `MODEL_DEPLOYMENT_NAME` | e.g., `gpt-5.2` |

#### Environment (Settings → Environments → New environment)
- Create an environment named `production`
- Add required reviewers (for deploy approval gate)

### 3. Azure OIDC Federation

Set up federated credentials so GitHub can authenticate without passwords:

```bash
# Create federated credential on your Azure AD app
az ad app federated-credential create \
  --id <APP_OBJECT_ID> \
  --parameters '{
    "name": "github-main-branch",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<OWNER>/<REPO>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Deploy locally (requires Azure login)
az login
export FOUNDRY_PROJECT_ENDPOINT="https://..."
python scripts/deploy_prompt_agent.py \
  --agent-name "demo-prompt-agent" \
  --model "gpt-5.2" \
  --prompt-file "agents/prompt.md"
```

## Pipeline Flow

```
Push to main
    ↓
┌── validate (GitHub-hosted Ubuntu runner) ──┐
│  ✅ Checkout → Install deps → Run tests    │
└────────────────────────────────────────────┘
    ↓ (passes)
┌── deploy (requires approval) ─────────────┐
│  🔐 Azure OIDC login                       │
│  🚀 create_version() → Foundry             │
│  ✅ Verify deployment                       │
└────────────────────────────────────────────┘
```
