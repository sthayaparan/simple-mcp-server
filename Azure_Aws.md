# Azure and AWS AI Platforms

## What is Azure AI Foundry

**Azure AI Foundry** is Microsoft's cloud platform for building, deploying and managing AI applications and agents on Azure. In late 2025 Microsoft renamed it **Microsoft Foundry**, so both names appear in docs and the portal (https://ai.azure.com).

### What it provides

| Area | What it is |
|---|---|
| **Model catalog** | Access to thousands of models behind one Azure endpoint: OpenAI (GPT), Anthropic Claude, Meta Llama, Mistral, DeepSeek, Microsoft Phi, and more |
| **Agent Service** | A managed runtime for AI agents. It hosts the agent loop, conversation threads, tool calling and state, so you do not run that yourself |
| **Tools** | Built-in tools (file search, code interpreter, Bing grounding, Azure AI Search) plus **MCP servers** and OpenAPI tools |
| **Evaluation and safety** | Evaluations, tracing and monitoring, and content safety filters |
| **Enterprise features** | Azure identity (Entra ID), private networking, RBAC, quotas, billing on your Azure subscription |
| **SDKs** | Python, C# and JS SDKs, plus the Azure AI Foundry VS Code extension |

### How it relates to this project

It is similar to the agent side of `agent/`, but managed by Azure:

| This project | Foundry equivalent |
|---|---|
| `agent/` console that runs the agent loop | Foundry Agent Service |
| OpenRouter calling `openai/gpt-oss-120b` | Foundry model deployment (a GPT model, Claude, etc.) |
| member-mcp at `127.0.0.1:8000/mcp` | An MCP tool added to the Foundry agent |

**The localhost limitation applies here too.** The Foundry Agent Service runs in Azure's cloud, so, like claude.ai connectors, it cannot reach `127.0.0.1` on your PC. To use member-mcp from a Foundry agent, deploy it with a public HTTPS URL (e.g. Azure Container Apps or App Service) and add authentication.

### When to use it

- **Use Foundry** if your organization is on Azure and needs enterprise controls: identity, private networking, compliance, and consolidated billing.
- **Stay with the current setup** (FastMCP + a simple agent + OpenRouter) for learning, prototypes, or when you want to switch providers freely.

## The AWS equivalent

The closest AWS equivalent is **Amazon Bedrock**, together with **Amazon Bedrock AgentCore** for running agents. **Amazon SageMaker AI** covers custom model training and hosting.

### Side-by-side mapping

| Microsoft Foundry (Azure) | AWS equivalent |
|---|---|
| Foundry (the overall platform) | **Amazon Bedrock** |
| Model catalog (GPT, Claude, Llama, Mistral...) | **Bedrock models** (Anthropic Claude, Amazon Nova, Llama, Mistral, DeepSeek, OpenAI gpt-oss, and others) |
| Foundry Agent Service | **Bedrock AgentCore** (Runtime, Memory, Identity, Gateway, Observability); the older managed **Bedrock Agents** also still exists |
| MCP / OpenAPI tools on agents | **AgentCore Gateway**, which turns REST APIs (OpenAPI), Lambda functions and existing MCP servers into MCP tools |
| File search / Azure AI Search grounding | **Bedrock Knowledge Bases** (managed RAG) |
| Content safety filters | **Bedrock Guardrails** |
| Evaluations | **Bedrock Evaluations** |
| Agent SDKs | **Strands Agents** (AWS's open-source agent SDK); AgentCore also runs LangGraph, CrewAI and similar frameworks |
| Custom model training / Azure ML | **Amazon SageMaker AI** |
| Entra ID, RBAC, VNet | IAM, VPC / PrivateLink |

### How it relates to this project

- **AgentCore Gateway** is the AWS managed version of what `REST_API_to_MCP_Tool.md` describes: you give it an OpenAPI spec or a Lambda function and it exposes MCP tools. With FastMCP you do the same thing yourself in code.
- **AgentCore Runtime** can host MCP servers, so member-mcp could be deployed there. AWS Lambda, ECS/Fargate and App Runner also work.
- **The localhost rule still applies.** An agent running in AWS cannot reach `127.0.0.1:8000` on your PC. The MCP server must be deployed somewhere reachable from AWS, with authentication.
- **Claude on Bedrock**: Claude models are available on Bedrock, so OpenRouter could be swapped for Bedrock in `agent/` while keeping the same MCP tool-calling loop.

## Quick comparison of the three clouds

| | Azure | AWS | Google Cloud |
|---|---|---|---|
| AI platform | Microsoft Foundry | Amazon Bedrock | Vertex AI |
| Managed agent runtime | Foundry Agent Service | Bedrock AgentCore | Vertex AI Agent Engine |
| Custom ML training | Azure Machine Learning | SageMaker AI | Vertex AI Training |

These services change quickly. Check the current docs before building on them:

- Azure: https://learn.microsoft.com/azure/ai-foundry
- AWS: https://docs.aws.amazon.com/bedrock/
