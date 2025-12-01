# gradr-agent

An AI-powered grading agent built with Google's Agent Development Kit (ADK) and optimized for automated evaluation of handwritten and typed student submissions. This project extends the base ReAct agent from googleCloudPlatform/agent-starter-pack (v0.21.0) and integrates tightly with Google Cloud (Vertex AI, BigQuery, Cloud Storage) to deliver high-accuracy automated grading.

Gradr-Agent is part of the broader GradrAI system—a platform for automating grading of paper-based tests using advanced LLMs, prompt orchestration, evaluators, domain expert feedback, and custom MCP tools.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Local Setup (for Hackathon Judges)](#local-setup-for-hackathon-judges)
- [Running Locally](#running-locally)
- [Deployment](#deployment)
- [Evaluation & Quality Assurance](#evaluation--quality-assurance)
- [Monitoring & Observability](#monitoring--observability)
- [Roadmap](#roadmap)

## Overview

Gradr-Agent acts as the AI reasoning layer for automated grading. It processes marking guides, student answers, and grading rules to generate reliable scoring decisions. The agent uses:

- Gemini 2.0 Flash / Pro via Vertex AI
- ReAct prompting for reasoning and tool use
- Custom MCP tools for dataset loading, scoring rubrics, answer extraction, rubric enforcement, and structured output
- Cloud Storage for resource access
- BigQuery telemetry for post-hoc evaluation
- Built-in eval flows with plans for expansion using human domain experts

The project supports school-level, department-level, and individual lecturer workflows for grading handwritten or typed scripts.

## Architecture

### High-Level Components

- **ADK ReAct Agent** (core reasoning + tool orchestration)
- **Custom MCP Tools**, e.g.:
  - `load_marking_scheme`
  - `extract_student_answers`
  - `grade_response`
  - `apply_rubric_policy`
  - `format_grade_output`
- **Evaluation Pipelines**
  - Notebook-driven evals
  - Automated rubric consistency checks
  - Human expert validation (future work)
- **Cloud Infrastructure**
  - Vertex AI grounding + inference
  - Cloud Storage (rubrics, student files, knowledge base)
  - BigQuery (telemetry + analytics)
  - Cloud Trace + Logging

## Features

- Automated grading using structured rubrics
- Support for multiple grading modes (exact match, partial credit, rubric scoring)
- Customizable evaluation workflows
- ReAct-based multi-step reasoning
- Cloud-first observability with BigQuery + OpenTelemetry
- Fully reproducible dev environment
- CI/CD-ready with Terraform + Cloud Build

## Project Structure

```
gradr-agent/
├── app/
│   ├── agent.py                    # Main agent logic
│   ├── agent_engine_app.py         # Agent Engine integration
│   └── app_utils/                  # Tooling helpers
├── .cloudbuild/                    # Cloud Build CI/CD pipelines
├── deployment/                     # Terraform IaC
├── notebooks/                      # Prototyping, evals, grading experiments
├── tests/                          # Unit + integration tests
├── Makefile                        # Dev automation
├── GEMINI.md                       # AI-assisted dev guide
└── pyproject.toml                  # Python dependencies
```

## Local Setup (for Hackathon Judges)

These instructions reproduce the entire environment locally.

### Prerequisites

Install the following:

| Tool | Purpose | Link |
|------|---------|------|
| `uv` | Python package manager | [astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| Google Cloud SDK | Access to GCP resources | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| Terraform | Infrastructure deployment | [terraform.io](https://developer.hashicorp.com/terraform/downloads) |
| `make` | Automation (usually preinstalled) | [gnu.org/software/make](https://www.gnu.org/software/make/) |

### Clone the Repo

```bash
git clone <repo-url>
cd gradr-agent
```

### Install Dependencies

```bash
make install
```

### Environment Variables

You must export the following:

```bash
export GOOGLE_PROJECT_ID=<your-project-id>
export GOOGLE_SERVICE_KEY=<base64-encoded-key>
export GOOGLE_APPLICATION_CREDENTIALS=./service_account.json
```

To generate a valid base64 key:

```bash
gcloud iam service-accounts keys create key.json \
 --iam-account=<service-account>@<project>.iam.gserviceaccount.com

base64 key.json > encoded.txt
```

Then paste the encoded content into `GOOGLE_SERVICE_KEY`.

### Run the Playground

This starts a local agent runtime with auto-reload.

```bash
make playground
```

## Running Locally

### Run tests

```bash
make test
```

### Lint & type checks

```bash
make lint
```

### Manual agent invocation

From Python:

```python
from app.agent import create_agent

agent = create_agent()
response = agent.run({"query": "Grade this answer..."})
print(response)
```

## Deployment

You may use either one-command CI/CD bootstrap or manual deployment.

### One-Command Setup

The starter pack provides a full CI/CD pipeline generator:

```bash
uvx agent-starter-pack setup-cicd
```

This initializes:

- Terraform infra
- Cloud Build pipelines
- GitHub Actions integration
- Agent Engine deployment

### Manual Dev Deployment

```bash
gcloud config set project <your-dev-project-id>
make deploy
```

### Register with Gemini Enterprise

```bash
make register-gemini-enterprise
```

### Production Infra

See [deployment/README.md](deployment/README.md) for full production setup instructions.

## Evaluation & Quality Assurance

Gradr-Agent uses a multi-layered evaluation strategy:

### Current evaluation stack

- Notebook-based eval suites
- Rubric consistency tests
- Automated comparison against gold-standard sample answers
- Confidence + chain-of-thought quality checks (via structured CoT)

### Planned improvements

- Expanded evaluator coverage (completeness, correctness, rubric alignment)
- Expert-in-the-loop validation using lecturers and grading specialists
- Benchmarking across different subjects
- Misgrade detection heuristics

## Monitoring & Observability

The project integrates OpenTelemetry GenAI instrumentation with:

### Cloud Logging

- 10-year retention for all agent operation logs

### BigQuery Telemetry

Fast SQL queries over:

- Model calls
- Tool traces
- Latency profiles
- Token usage
- Error analysis

Example:

```bash
bq query --use_legacy_sql=false \
"SELECT * FROM \`gradr-agent_telemetry.completions\` LIMIT 10"
```

### Cloud Trace

- Distributed traces for multi-step ReAct flows

## Roadmap

- Add more rubric evaluators and grading validators
- Expand MCP tools (PDF parsing, math reasoning, knowledge-base retrieval)
- Add multimodal evaluation capabilities
- Introduce real-time dashboards for grading analytics
- Improve failure recovery and retry logic
- Add offline/batch grading mode
