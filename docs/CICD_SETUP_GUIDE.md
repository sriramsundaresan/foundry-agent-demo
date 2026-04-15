# CI/CD Pipeline for Azure AI Foundry Agents using GitHub Actions

A step-by-step guide for setting up an automated deployment pipeline that deploys AI agents to Azure AI Foundry every time code is pushed to GitHub.

---

## Table of Contents

1. [What This Guide Covers](#1-what-this-guide-covers)
2. [Key Concepts (for Beginners)](#2-key-concepts-for-beginners)
3. [Prerequisites](#3-prerequisites)
4. [Architecture Overview](#4-architecture-overview)
5. [Step 1: Create a GitHub Repository](#step-1-create-a-github-repository)
6. [Step 2: Create an Azure AD App Registration](#step-2-create-an-azure-ad-app-registration)
7. [Step 3: Set Up OIDC Federation (Passwordless Auth)](#step-3-set-up-oidc-federation-passwordless-auth)
8. [Step 4: Assign Azure Permissions](#step-4-assign-azure-permissions)
9. [Step 5: Configure GitHub Secrets and Variables](#step-5-configure-github-secrets-and-variables)
10. [Step 6: Create a GitHub Environment](#step-6-create-a-github-environment)
11. [Step 7: Understand the Pipeline Files](#step-7-understand-the-pipeline-files)
12. [Step 8: Push Code and Trigger the Pipeline](#step-8-push-code-and-trigger-the-pipeline)
13. [Step 9: Monitor and Troubleshoot](#step-9-monitor-and-troubleshoot)
14. [Common Errors and Fixes](#common-errors-and-fixes)
15. [Security Best Practices](#security-best-practices)

---

## 1. What This Guide Covers

This guide walks you through building a CI/CD pipeline that:

- **Automatically tests** your agent prompt and scripts on every code change
- **Automatically deploys** a prompt agent to Azure AI Foundry when code is merged to the `main` branch
- **Uses passwordless authentication** (OIDC) — no passwords or secrets stored anywhere
- **Runs on GitHub-hosted runners** — free, managed VMs that GitHub spins up on demand (no infrastructure to maintain)

---

## 2. Key Concepts (for Beginners)

If you're new to GitHub, here are the core concepts you'll encounter:

| Concept | What It Is | Analogy |
|---------|------------|---------|
| **Repository (Repo)** | A folder that stores your code, tracked by Git version control | A shared network drive with full history of every change |
| **Branch** | A parallel version of your code. `main` is the primary branch | A draft copy of a document you can edit without affecting the original |
| **Push** | Uploading your local code changes to GitHub | Saving your local file to the shared drive |
| **Pull Request (PR)** | A request to merge changes from one branch into another | Asking a colleague to review and approve your document changes |
| **GitHub Actions** | GitHub's built-in CI/CD platform — runs automation when events happen (push, PR, etc.) | An automated script that runs when you save a file to the shared drive |
| **Workflow** | A YAML file that defines what GitHub Actions should do | A recipe with step-by-step instructions |
| **Job** | A group of steps that run on the same machine | A chapter in the recipe |
| **Step** | A single command or action within a job | A single instruction in the recipe |
| **Runner** | The machine (VM) that executes your workflow | The kitchen where the recipe is cooked |
| **GitHub-hosted Runner** | A free, temporary VM managed by GitHub (Ubuntu, Windows, or macOS) | A rental kitchen that's cleaned after every use |
| **Secret** | An encrypted value stored in GitHub (e.g., credentials) | A locked safe in the kitchen |
| **Variable** | A non-sensitive configuration value stored in GitHub | A label on a kitchen shelf |
| **Environment** | A deployment target (e.g., `production`) with optional approval gates | A quality checkpoint before serving the dish |
| **OIDC** | OpenID Connect — a protocol that lets GitHub prove its identity to Azure without passwords | Showing your employee badge instead of typing a password |

---

## 3. Prerequisites

Before you begin, ensure you have:

### Azure

- [ ] An Azure subscription with **Owner** permissions
- [ ] An Azure AI Foundry project with an endpoint URL
  - Format: `https://<resource-name>.services.ai.azure.com/api/projects/<project-name>`
- [ ] A model deployment in your Foundry project (e.g., `gpt-4o-mini`)
- [ ] Azure CLI installed (`az --version` to verify)

### GitHub

- [ ] A GitHub account (personal or organization)
- [ ] Git installed locally (`git --version` to verify)
- [ ] GitHub CLI installed (`gh --version` to verify) — [Install Guide](https://cli.github.com/)

### Local Machine

- [ ] Python 3.10+ installed
- [ ] The agent source code (this repository)

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR MACHINE                             │
│  1. Write code (agent prompt, deploy scripts)                   │
│  2. git push → sends code to GitHub                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         GITHUB                                  │
│                                                                 │
│  3. GitHub detects the push                                     │
│  4. Reads .github/workflows/deploy-prompt-agent.yml             │
│  5. Spins up a fresh Ubuntu VM (GitHub-hosted runner)           │
│                                                                 │
│  ┌─── Runner VM ──────────────────────────────────────────┐     │
│  │  6. Checks out your code                               │     │
│  │  7. Installs Python + dependencies                     │     │
│  │  8. Runs tests (pytest)                                │     │
│  │  9. Requests OIDC token from GitHub                    │     │
│  │ 10. Exchanges token with Azure AD → gets Azure token   │     │
│  │ 11. Calls Foundry SDK to deploy the agent              │     │
│  │ 12. Verifies the deployment                            │     │
│  └────────────────────────────────────────────────────────┘     │
│ 13. VM is destroyed (nothing persists)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AZURE AI FOUNDRY                              │
│                                                                 │
│  Agent is deployed/updated with the new prompt and settings     │
│  Agent is accessible via the Foundry project endpoint           │
└─────────────────────────────────────────────────────────────────┘
```

### How Authentication Works (OIDC Flow)

```
GitHub Runner                    Azure AD                      Azure AI Foundry
     │                              │                               │
     │  1. "I am repo X, branch Y"  │                               │
     │  ───────────────────────────► │                               │
     │                              │                               │
     │  2. "Here's a short-lived    │                               │
     │      Azure access token"     │                               │
     │  ◄─────────────────────────── │                               │
     │                              │                               │
     │  3. "Deploy this agent"      │                               │
     │      (with Azure token)      │                               │
     │  ────────────────────────────────────────────────────────────►│
     │                              │                               │
     │  4. "Agent deployed ✓"       │                               │
     │  ◄────────────────────────────────────────────────────────────│
```

No passwords are stored anywhere. Azure trusts GitHub because of the federated credential you configure.

---

## Step 1: Create a GitHub Repository

### Option A: Using GitHub CLI (recommended)

```bash
# Login to GitHub (opens browser for authentication)
gh auth login

# Navigate to your project folder
cd /path/to/foundry-agent-demo

# Initialize Git and make initial commit
git init
git add .
git commit -m "Initial commit: Foundry prompt agent with GitHub Actions"

# Create the repo on GitHub and push
gh repo create <your-username>/foundry-agent-demo --public --source=. --push

# Ensure the default branch is named 'main'
git branch -M main
git push -u origin main
gh repo edit --default-branch main
```

### Option B: Using GitHub Web UI

1. Go to [github.com/new](https://github.com/new)
2. Enter repository name: `foundry-agent-demo`
3. Choose **Public** or **Private**
4. Click **Create repository**
5. Follow the instructions to push your local code

### Verify

Visit `https://github.com/<your-username>/foundry-agent-demo` — you should see your files.

---

## Step 2: Create an Azure AD App Registration

This creates an identity that GitHub will use to authenticate with Azure.

```bash
# Login to Azure
az login

# Create the app registration
az ad app create --display-name "github-foundry-deploy"
```

**Save the `appId` from the output** — you'll need it in every subsequent step.

Example output:

```json
{
  "appId": "5a77ec6c-2d88-4359-ab5b-9cd93d270259",   ← SAVE THIS (Client ID)
  "id": "1160cc2a-73e8-4f68-b569-db1bad0c3506",       ← SAVE THIS (Object ID)
  ...
}
```

Now create a service principal for the app:

```bash
az ad sp create --id <APP_ID>
```

---

## Step 3: Set Up OIDC Federation (Passwordless Auth)

This tells Azure AD: *"Trust tokens that come from GitHub Actions for this specific repository."*

### Get the App Object ID

```bash
az ad app show --id <APP_ID> --query id -o tsv
```

### Create the Federated Credential

Create a JSON file named `oidc-production.json`:

```json
{
  "name": "github-production-env",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<YOUR_GITHUB_USER>/<REPO_NAME>:environment:production",
  "audiences": ["api://AzureADTokenExchange"]
}
```

Apply it:

```bash
az ad app federated-credential create \
  --id <APP_OBJECT_ID> \
  --parameters @oidc-production.json
```

> ⚠️ **Critical: The `subject` must exactly match how your workflow authenticates.**
>
> | Workflow Configuration | Required Subject |
> |------------------------|------------------|
> | `environment: production` | `repo:<owner>/<repo>:environment:production` |
> | No environment, push to `main` | `repo:<owner>/<repo>:ref:refs/heads/main` |
> | Pull request trigger | `repo:<owner>/<repo>:pull_request` |
>
> If your workflow has **both** an environment-based deploy job **and** a branch-based validate job, create **two** federated credentials (one for each subject).

### Optional: Add Credential for Branch-Based Triggers

```bash
# Create oidc-branch.json
cat > oidc-branch.json << 'EOF'
{
  "name": "github-main-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<YOUR_GITHUB_USER>/<REPO_NAME>:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF

az ad app federated-credential create \
  --id <APP_OBJECT_ID> \
  --parameters @oidc-branch.json
```

### Verify

```bash
az ad app federated-credential list \
  --id <APP_OBJECT_ID> \
  --query "[].{name:name, subject:subject}" -o table
```

Expected output:

```
Name                   Subject
---------------------  ----------------------------------------------------------
github-production-env  repo:your-user/foundry-agent-demo:environment:production
github-main-branch     repo:your-user/foundry-agent-demo:ref:refs/heads/main
```

---

## Step 4: Assign Azure Permissions

The service principal needs specific roles to deploy agents. **This is the most critical step** — incorrect permissions are the #1 cause of deployment failures.

### Required Roles

| Role | Scope | Purpose |
|------|-------|---------|
| **Azure AI User** | Foundry resource | Data-plane access: create, update, delete agents (`agents/write` action) |
| **Cognitive Services Contributor** | Foundry resource | Management-plane access to the Foundry resource |

### Find Your Foundry Resource ID

```bash
az cognitiveservices account list \
  --query "[].{name:name, id:id}" -o table
```

### Assign the Roles

```bash
# Set variables for readability
APP_ID="<your-app-id>"
RESOURCE_ID="/subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource-name>"

# Role 1: Azure AI User (REQUIRED — enables agent data-plane operations)
az role assignment create \
  --assignee $APP_ID \
  --role "Azure AI User" \
  --scope $RESOURCE_ID

# Role 2: Cognitive Services Contributor (enables management-plane access)
az role assignment create \
  --assignee $APP_ID \
  --role "Cognitive Services Contributor" \
  --scope $RESOURCE_ID
```

> ⚠️ **Important:** Role assignments take **1–5 minutes** to propagate. If you get permission errors immediately after assigning, wait and retry.

### Verify Role Assignments

```bash
az role assignment list \
  --assignee $APP_ID \
  --scope $RESOURCE_ID \
  --query "[].{role:roleDefinitionName}" -o table
```

### Common Mistake: Wrong Role

| Role | Has `agents/write`? | Notes |
|------|---------------------|-------|
| **Azure AI User** | ✅ Yes | **Use this one** for Foundry agent operations |
| Azure AI Developer | ❌ No | General AI development, does NOT include agent write |
| Cognitive Services User | ❌ No | Generic data-plane, does NOT include Foundry-specific actions |
| Cognitive Services Contributor | ❌ No | Management plane only, no data-plane actions |

---

## Step 5: Configure GitHub Secrets and Variables

### What's the Difference?

| Type | Encrypted? | Visible in Logs? | Use For |
|------|-----------|-------------------|---------|
| **Secrets** | ✅ Yes | ❌ Masked as `***` | Credentials, IDs |
| **Variables** | ❌ No | ✅ Yes | Configuration values |

### Using GitHub CLI

```bash
cd /path/to/foundry-agent-demo

# ── Secrets ──
gh secret set AZURE_CLIENT_ID --body "<your-app-id>"
gh secret set AZURE_TENANT_ID --body "<your-tenant-id>"
gh secret set AZURE_SUBSCRIPTION_ID --body "<your-subscription-id>"

# ── Variables ──
gh variable set FOUNDRY_PROJECT_ENDPOINT \
  --body "https://<resource>.services.ai.azure.com/api/projects/<project>"
gh variable set MODEL_DEPLOYMENT_NAME --body "gpt-4o-mini"
```

### Finding Your Azure Values

```bash
# Tenant ID
az account show --query tenantId -o tsv

# Subscription ID
az account show --query id -o tsv

# App (Client) ID — saved from Step 2
```

### Using GitHub Web UI (Alternative)

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each secret
3. Click the **Variables** tab → **New repository variable** for each variable

---

## Step 6: Create a GitHub Environment

Environments add an approval gate before deployment — someone must click "Approve" before code deploys to production.

### Using GitHub Web UI

1. Go to your repo → **Settings** → **Environments**
2. Click **New environment**
3. Name it exactly: `production`
4. Under **Environment protection rules**:
   - Check **Required reviewers**
   - Add yourself or your team lead as a reviewer
5. Click **Save protection rules**

> 💡 **For testing:** You can skip adding required reviewers. The environment will still work — it just won't have the approval gate.

---

## Step 7: Understand the Pipeline Files

### Project Structure

```
foundry-agent-demo/
├── .github/
│   └── workflows/
│       └── deploy-prompt-agent.yml   ← CI/CD pipeline definition
├── agents/
│   └── prompt.md                     ← Agent instructions (the prompt)
├── scripts/
│   ├── deploy_prompt_agent.py        ← Calls Foundry SDK to deploy
│   └── verify_deployment.py          ← Confirms deploy succeeded
├── tests/
│   ├── test_prompt.py                ← Validates the prompt file
│   └── test_deploy_script.py         ← Validates the deploy script
└── requirements.txt                  ← Python dependencies
```

### The Workflow File Explained

The file `.github/workflows/deploy-prompt-agent.yml` defines a two-stage pipeline:

**Stage 1 — Validate** (runs on every push and PR):

- Checks out the code
- Installs Python and dependencies
- Runs all tests with `pytest`
- If any test fails, the pipeline stops here

**Stage 2 — Deploy** (runs only on push to `main`, after Stage 1 passes):

- Requires manual approval (if environment reviewers are configured)
- Logs into Azure using OIDC (passwordless)
- Runs the deploy script to create/update the agent in Foundry
- Verifies the agent was deployed successfully

### Pipeline Flow Diagram

```
Push to main (or PR)
         │
         ▼
┌─── validate ──────────────────────────────┐
│  ✅ Checkout → Install deps → Run tests   │
└────────────────────────────────────────────┘
         │ (passes)
         ▼
┌─── deploy (main branch only) ─────────────┐
│  🔒 Wait for approval (if configured)     │
│  🔐 Azure OIDC login                      │
│  🚀 Deploy agent via Foundry SDK          │
│  ✅ Verify deployment                      │
└────────────────────────────────────────────┘
```

---

## Step 8: Push Code and Trigger the Pipeline

### Trigger a Deployment

```bash
# Make a change (e.g., update the agent prompt)
# Edit agents/prompt.md

# Commit and push
git add .
git commit -m "Update agent instructions"
git push origin main
```

The pipeline triggers automatically because the workflow watches for changes in `agents/`, `scripts/`, and `requirements.txt`.

### Watch It Run

**Option A — GitHub CLI:**

```bash
# List recent runs
gh run list

# Watch a run in real time
gh run watch
```

**Option B — Web UI:**

1. Go to `https://github.com/<your-username>/foundry-agent-demo/actions`
2. Click on the latest workflow run
3. Watch the jobs execute step by step

---

## Step 9: Monitor and Troubleshoot

### Useful CLI Commands

```bash
# List recent workflow runs
gh run list

# View details of a specific run
gh run view <RUN_ID>

# View logs of failed jobs only
gh run view <RUN_ID> --log-failed

# Re-run only the failed jobs (saves time)
gh run rerun <RUN_ID> --failed

# Re-run the entire workflow
gh run rerun <RUN_ID>
```

### Checking Azure-Side

```bash
# Verify the agent exists in Foundry
python scripts/verify_deployment.py "demo-prompt-agent"

# Check role assignments on the Foundry resource
az role assignment list \
  --assignee <APP_ID> \
  --scope <RESOURCE_ID> \
  --query "[].roleDefinitionName" -o tsv
```

---

## Common Errors and Fixes

### Error 1: "No matching federated identity record"

```
AADSTS700213: No matching federated identity record found for presented
assertion subject 'repo:user/repo:environment:production'
```

**Cause:** The `subject` in your federated credential doesn't match the workflow's actual subject claim.

**Fix:** Create a federated credential with the exact subject shown in the error message. See [Step 3](#step-3-set-up-oidc-federation-passwordless-auth).

---

### Error 2: "lacks the required data action agents/write"

```
PermissionDenied: The principal lacks the required data action
Microsoft.CognitiveServices/accounts/AIServices/agents/write
```

**Cause:** The service principal doesn't have the **Azure AI User** role.

**Fix:**

```bash
az role assignment create \
  --assignee <APP_ID> \
  --role "Azure AI User" \
  --scope <FOUNDRY_RESOURCE_ID>
```

Wait 1–5 minutes for propagation, then re-run: `gh run rerun <RUN_ID> --failed`

---

### Error 3: Workflow Doesn't Trigger

**Possible causes:**

- The changed file isn't in `agents/`, `scripts/`, or `requirements.txt` (check the `paths` filter in the workflow)
- You pushed to a branch other than `main`
- The workflow YAML file has a syntax error

**Fix:** Check the workflow `paths` filter, or temporarily remove it to trigger on all changes.

---

### Error 4: Deploy Works Locally but Fails in Pipeline

**Cause:** Your local `az login` uses your personal identity (which likely has Owner). The pipeline uses the service principal, which needs explicit role assignments.

**Fix:** Ensure the service principal has both `Azure AI User` and `Cognitive Services Contributor` roles on the Foundry resource (see [Step 4](#step-4-assign-azure-permissions)).

---

## Security Best Practices

1. **Never store passwords or keys** — Use OIDC federated credentials (as configured in this guide)
2. **Use GitHub Secrets for sensitive values** — Client IDs, tenant IDs, and subscription IDs should be secrets
3. **Use GitHub Environments with required reviewers** — Prevents accidental deployments to production
4. **Scope roles narrowly** — Assign roles to the specific Foundry resource, not the entire subscription
5. **Rotate nothing** — OIDC tokens are short-lived and auto-issued; there's nothing to rotate
6. **Audit role assignments periodically:**
   ```bash
   az role assignment list --scope <FOUNDRY_RESOURCE_ID> -o table
   ```

---

## Quick Reference Card

### Azure CLI Commands

| Task | Command |
|------|---------|
| Login to Azure | `az login` |
| Get Tenant ID | `az account show --query tenantId -o tsv` |
| Get Subscription ID | `az account show --query id -o tsv` |
| Create AD App | `az ad app create --display-name "github-foundry-deploy"` |
| Create Service Principal | `az ad sp create --id <APP_ID>` |
| Create Federated Credential | `az ad app federated-credential create --id <OBJ_ID> --parameters @params.json` |
| Assign Role | `az role assignment create --assignee <APP_ID> --role "<ROLE>" --scope "<SCOPE>"` |
| List Role Assignments | `az role assignment list --assignee <APP_ID> --scope "<SCOPE>" -o table` |

### GitHub CLI Commands

| Task | Command |
|------|---------|
| Login to GitHub | `gh auth login` |
| Create Repo | `gh repo create <owner>/<repo> --public --source=. --push` |
| Set Secret | `gh secret set <NAME> --body "<VALUE>"` |
| Set Variable | `gh variable set <NAME> --body "<VALUE>"` |
| View Workflow Runs | `gh run list` |
| Watch Run Live | `gh run watch` |
| View Run Details | `gh run view <RUN_ID>` |
| Re-run Failed Jobs | `gh run rerun <RUN_ID> --failed` |

### Required Permissions Summary

| Where | What | Why |
|-------|------|-----|
| **Azure AD** | App Registration + Service Principal | Identity for GitHub to authenticate as |
| **Azure AD** | Federated Credential (OIDC) | Trust GitHub tokens for passwordless auth |
| **Azure (Foundry resource)** | `Azure AI User` role | Data-plane: create/update/delete agents |
| **Azure (Foundry resource)** | `Cognitive Services Contributor` role | Management-plane: access the Foundry resource |
| **GitHub (repo)** | Secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | Authentication parameters |
| **GitHub (repo)** | Variables: `FOUNDRY_PROJECT_ENDPOINT`, `MODEL_DEPLOYMENT_NAME` | Deployment configuration |
| **GitHub (repo)** | Environment: `production` with reviewers | Approval gate for deployments |
