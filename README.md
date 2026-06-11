# Gradr-Agent

An AI-powered grading agent built with Google's Agent Development Kit (ADK) and optimized for automated evaluation of handwritten and typed student submissions. This project extends the base ReAct agent from [googleCloudPlatform/agent-starter-pack](https://github.com/GoogleCloudPlatform/agent-starter-pack) (v0.21.0) and integrates tightly with Google Cloud (Vertex AI, BigQuery, Cloud Storage) to deliver high-accuracy automated grading.

Gradr-Agent is part of the broader GradrAI system — a platform for automating grading of paper-based tests using advanced LLMs, prompt orchestration, evaluators, domain expert feedback, and custom MCP tools.

## Table of Contents

- [System Architecture](#system-architecture)
- [Overview](#overview)
- [Agent Pipelines](#agent-pipelines)
- [Features](#features)
- [Project Structure](#project-structure)
- [Deployed Endpoints](#deployed-endpoints)
- [Local Setup (for Hackathon Judges)](#local-setup-for-hackathon-judges)
- [Running Locally](#running-locally)
- [Deployment](#deployment)
- [Evaluation & Quality Assurance](#evaluation--quality-assurance)
- [Monitoring & Observability](#monitoring--observability)

## System Architecture

The full GradrAI platform consists of four services. The frontend and backend are closed-source, but the agent and MCP server repos are provided for review.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         GradrAI Platform                                │
│                                                                         │
│  ┌───────────────┐       ┌───────────────────┐                          │
│  │   Frontend     │──────▶│     Backend        │                         │
│  │  (React/Vite)  │ REST  │  (Node.js/Express) │                         │
│  │  gradrai.com   │◀──────│  Cloud Run         │                         │
│  └───────────────┘       └────────┬──────────┘                          │
│                                   │                                      │
│                    Vertex AI Reasoning Engine API                        │
│                    (authenticated via Google Auth)                       │
│                                   │                                      │
│                                   ▼                                      │
│                   ┌───────────────────────────┐                          │
│                   │     Gradr-Agent (ADK)      │  ◀── This repo          │
│                   │  Deployed on Vertex AI     │                         │
│                   │  Reasoning Engine          │                         │
│                   └─────┬──────┬──────┬───────┘                          │
│                         │      │      │                                  │
│              ┌──────────┘      │      └──────────┐                      │
│              ▼                 ▼                  ▼                      │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐             │
│  │  Gradr MCP     │  │  MongoDB MCP │  │  GCS MCP         │             │
│  │  (Cloud Run)   │  │  (npx stdio) │  │  (npx stdio)     │             │
│  │  Custom tools  │  │  DB read/    │  │  Cloud Storage   │             │
│  │                │  │  write       │  │  access          │             │
│  └────────────────┘  └──────────────┘  └──────────────────┘             │
│                                                                         │
│  Supporting Infrastructure:                                             │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐    │
│  │ BigQuery │  │ Cloud Trace  │  │ Cloud       │  │ Redis (BullMQ)│    │
│  │Telemetry │  │ (Waterfall)  │  │ Logging     │  │ Job Queues    │    │
│  └──────────┘  └──────────────┘  └─────────────┘  └───────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Request Flow (Paper-Based Test Grading)

1. **Educator** uploads question paper, marking guide, and student scripts via the **frontend** (`gradrai.com`).
2. **Backend** enqueues a grading job via BullMQ (Redis) and calls the **Vertex AI Reasoning Engine** API to invoke the agent.
3. **Gradr-Agent** orchestrates a sequential pipeline of specialized sub-agents (see [Agent Pipelines](#agent-pipelines)).
4. Each agent in the pipeline may call **MCP tools** (custom Gradr MCP, MongoDB MCP, GCS MCP) to read/write data.
5. Results are persisted to **MongoDB** and the educator is notified.

> **Backend ↔ Agent integration**: The backend calls the deployed agent via the Vertex AI Reasoning Engine `:query` API, authenticated with Google service account credentials. See the [agentRuntime.js gist](https://gist.github.com/Fiewor/29d17b6ad354cfdf63c25a01082064c3) for the full implementation.

## Overview

Gradr-Agent acts as the AI reasoning layer for automated grading. It processes marking guides, student answers, and grading rules to generate reliable scoring decisions. The agent uses:

- Gemini 2.5 Flash / Flash-Lite via Vertex AI
- ReAct prompting for reasoning and tool use
- Custom MCP tools for rubric parsing, answer normalization, and ALOC cache triggers
- MongoDB MCP for database read/write operations
- GCS MCP for Cloud Storage access (student scripts, marking guides)
- BigQuery telemetry for post-hoc evaluation
- OpenTelemetry GenAI instrumentation for distributed tracing

## Agent Pipelines

### PBT (Paper-Based Test) Grading Pipeline

A `SequentialAgent` that orchestrates six specialized agents in order:

| Step | Agent | Model | Role |
|------|-------|-------|------|
| 1 | `PreprocessingAgent` | gemini-2.5-flash | Parses questions, marking guide, and student answers using MCP tools |
| 2 | `GradingAgent` | gemini-2.5-flash | Evaluates answers against the rubric. Delegates to `OnlineAnswersAgent` (Google Search) and `SummarizerAgent` as sub-agents |
| 3 | `RefereeAgent` | gemini-2.5-flash | Cross-checks grades for consistency. Flags low-confidence results for teacher review (HITL) |
| 4 | `WeaknessDetectionAgent` | gemini-2.5-flash-lite | Identifies weak topics from graded results |
| 5 | `SmartPrepAgent` | gemini-2.5-flash-lite | Auto-generates personalized practice sessions based on weaknesses |
| 6 | `FinalAggregator` | gemini-2.5-flash-lite | Persists final results and generates the grading payload |

### CBT (Computer-Based Test) Grading Pipeline

A `SequentialAgent` for auto-grading online exam submissions:

| Step | Agent | Model | Role |
|------|-------|-------|------|
| 1 | `AttemptRetrievalAgent` | gemini-2.5-flash-lite | Fetches the student's exam attempt from MongoDB |
| 2 | `MCQGradingAgent` | gemini-2.5-flash-lite | Grades multiple-choice questions |
| 3 | `EssayGradingAgent` | gemini-2.5-flash | Grades essay/free-response questions against rubrics |
| 4 | `FeedbackNarrationAgent` | gemini-2.5-flash-lite | Generates human-readable feedback narratives |
| 5 | `WeaknessDetectionAgent` | gemini-2.5-flash-lite | Identifies weak topics |
| 6 | `SmartPrepAgent` | gemini-2.5-flash-lite | Auto-generates practice sessions |
| 7 | `ResultPersistenceAgent` | gemini-2.5-flash-lite | Persists results to MongoDB |

### CBT Exam Generation Pipeline

A `SequentialAgent` that generates exam questions from uploaded course materials:

| Step | Agent | Model | Role |
|------|-------|-------|------|
| 1 | `TopicExtractionAgent` | gemini-2.5-flash-lite | Analyzes documents and extracts the top 5–10 academic topics with concentration weights |
| 2 | `QuestionGenerationAgent` | gemini-2.5-flash | Generates curriculum-aligned MCQ, essay, or hybrid questions based on extracted topics. Skipped if the request is extract-only |

### MCP Toolsets

The agent connects to three MCP servers:

| Toolset | Connection | Tools |
|---------|-----------|-------|
| **Gradr MCP** (custom) | Streamable HTTP → Cloud Run | `parse_questions`, `parse_marking_guide`, `normalize_answers`, `trigger_aloc_cache` |
| **MongoDB MCP** | stdio (npx) | Full MongoDB CRUD operations |
| **GCS MCP** | stdio (npx) | Google Cloud Storage read/write |

## Features

- Automated grading using structured rubrics
- Support for multiple grading modes (exact match, partial credit, rubric scoring)
- Customizable evaluation workflows
- ReAct-based multi-step reasoning with inter-agent callbacks
- Human-in-the-loop (HITL) flagging via the RefereeAgent
- Automatic weakness detection and personalized practice generation (SmartPrep)
- Cloud-first observability with BigQuery + OpenTelemetry
- Fully reproducible dev environment
- CI/CD-ready with Terraform + Cloud Build

## Project Structure

```
gradr-agent/
├── app/
│   ├── agents/
│   │   ├── pbt_grading_pipeline.py    # PBT sequential pipeline
│   │   ├── cbt_grading_pipeline.py    # CBT sequential pipeline
│   │   ├── shared_agents.py           # WeaknessDetection + SmartPrep factories
│   │   └── cbt_exam_pipeline.py          # CBT exam generation pipeline
│   ├── agent_engine_app.py            # AgentEngineApp (Vertex AI deployment wrapper)
│   ├── callbacks.py                   # Inter-agent state management & logging
│   ├── prompts.py                     # All agent prompts
│   ├── toolsets.py                    # MCP toolset configuration
│   └── app_utils/                     # Deploy scripts, telemetry, typing
├── .cloudbuild/                       # Cloud Build CI/CD pipelines
├── deployment/                        # Terraform IaC
├── local_playground/                  # ADK local dev playground config
├── notebooks/                         # Prototyping, evals, grading experiments
├── tests/                             # Unit + integration tests
├── Makefile                           # Dev automation
└── pyproject.toml                     # Python dependencies (managed by uv)
```

## Deployed Endpoints

### Agent (Vertex AI Reasoning Engine)

The agents are deployed to Vertex AI Reasoning Engine and invoked via the `:query` API. They are not publicly accessible — the backend authenticates using Google Cloud service account credentials.

| Agent | Reasoning Engine ID | API Endpoint |
|-------|-------------------|--------------|
| **PBT Grading Pipeline** | `3347285579636146176` | `https://us-central1-aiplatform.googleapis.com/v1beta1/projects/gradr-421618/locations/us-central1/reasoningEngines/3347285579636146176:query` |
| **CBT Grading Pipeline** | `1085942005021802496` | `https://us-central1-aiplatform.googleapis.com/v1beta1/projects/gradr-421618/locations/us-central1/reasoningEngines/1085942005021802496:query` |
| **CBT Exam Generation** | `1085942005021802496` | `https://us-central1-aiplatform.googleapis.com/v1beta1/projects/gradr-421618/locations/us-central1/reasoningEngines/1085942005021802496:query` |

### MCP Server (Cloud Run)

| Service | URL |
|---------|-----|
| **Gradr MCP** | `https://gradrmcp-943768265988.us-central1.run.app` |

### Backend (Cloud Run) — closed source

| Service | URL |
|---------|-----|
| **Gradr Backend** | `https://gradr-backend-943768265988.us-central1.run.app` |

> **How the backend calls the agent**: See the [agentRuntime.js gist](https://gist.github.com/Fiewor/29d17b6ad354cfdf63c25a01082064c3) for the full Node.js integration code that routes requests to the correct Reasoning Engine based on pipeline name.

## Local Setup (for Hackathon Judges)

These instructions reproduce the agent environment locally.

### Prerequisites

| Tool | Purpose | Link |
|------|---------|------|
| `uv` | Python package manager | [astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| Google Cloud SDK | Access to GCP resources | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| `make` | Automation (usually preinstalled) | [gnu.org/software/make](https://www.gnu.org/software/make/) |
| Node.js 18+ | Required for MongoDB MCP and GCS MCP (npx) | [nodejs.org](https://nodejs.org/) |

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

Create a `.env` file (see `.env.example`) with the following:

```bash
GOOGLE_CLOUD_PROJECT=gradr-421618
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=True
MDB_MCP_CONNECTION_STRING=<your-mongodb-connection-string>
```

You must also authenticate with GCP:

```bash
gcloud auth application-default login
gcloud config set project gradr-421618
```

### Run the Playground

This starts a local ADK playground UI with auto-reload at `http://localhost:8501`:

```bash
make playground
```

From the playground dropdown, select the agent pipeline you want to test (PBT Grading, CBT Grading, or CBT Exam Generation).

## Running Locally

### Run tests

```bash
make test
```

### Lint & type checks

```bash
make lint
```

## Deployment

### Deploy individual agents

```bash
make deploy-pbt           # PBT Grading Agent
make deploy-cbt-grading   # CBT Grading Agent
make deploy-cbt-exam      # CBT Exam Generation Agent
make deploy-all           # All agents
```

### Infrastructure (Terraform)

```bash
make setup-dev-env
```

See [deployment/](deployment/) for full Terraform configuration.

## Evaluation & Quality Assurance

Gradr-Agent uses a multi-layered evaluation strategy:

- Notebook-based eval suites
- Rubric consistency tests
- Automated comparison against gold-standard sample answers
- Confidence + chain-of-thought quality checks (via structured CoT)
- RefereeAgent cross-validation with HITL flagging

## Monitoring & Observability

The project integrates OpenTelemetry GenAI instrumentation with:

### Cloud Logging

- All agent operation logs including inter-agent handoff messages
- Viewable at: **GCP Console → Logging → Logs Explorer**

### BigQuery Telemetry

Fast SQL queries over model calls, tool traces, latency profiles, token usage, and error analysis:

```sql
SELECT * FROM `gradr-agent_telemetry.completions` LIMIT 10
```

### Cloud Trace

- Distributed waterfall traces for multi-step agent pipelines
- Viewable at: **GCP Console → Trace → Trace Explorer**
- Each trace shows the full timeline of a grading request across all agents
