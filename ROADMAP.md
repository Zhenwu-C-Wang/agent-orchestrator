# ROADMAP: Executable MVP for a Supervisor / Worker Orchestrator

This repository now targets a narrow, buildable first milestone instead of a broad multi-agent platform. The immediate goal is to ship a runnable closed loop that proves the orchestration shape before adding parallelism, advanced cache policy, or human review.

## 1. MVP Decision

### Problem We Are Solving

Build a supervisor-driven workflow that takes one user question, delegates it to focused workers, and returns one final answer with structured intermediate output.

### In Scope

- Python implementation
- One fixed workflow: `ResearchWorker -> WriterWorker`
- One optional validation stage: `ReviewWorker`
- One `Supervisor`
- One `TaskRouter`
- One structured `ModelRunner` interface
- One local-model adapter for Ollama
- One deterministic fake runner for tests and demos
- One optional JSON audit logger for run persistence
- One read-only local run status query over audit artifacts
- One optional acceptance report logger for validation persistence
- One read-only acceptance report query over local JSON artifacts
- One model-layer retry policy for Ollama calls and JSON parsing
- One optional request-level structured result cache
- One optional TTL-based cache expiry policy
- One local cache inspection and maintenance CLI
- One normalized CLI error taxonomy with stable exit codes
- CLI entrypoint for local execution

### Out Of Scope For This Milestone

- Parallel task execution
- Dynamic tool selection
- Additional review or audit workers
- Advanced cache invalidation/eviction policy and workflow-level retries
- Human approval nodes
- Streaming responses
- External search, RAG, SQL, code execution
- Durable storage beyond local JSON audit artifacts

The rule for this milestone is simple: if a feature is not required to prove the end-to-end orchestration contract, defer it.

## 2. Locked Technical Choices

These choices are intentionally fixed so implementation can start immediately.

| Topic | Decision |
| --- | --- |
| Language | Python 3.11+ |
| Schema validation | `pydantic` |
| Local model provider | Ollama via HTTP API |
| Test runner | `pytest` |
| CLI entrypoint | `python main.py "question"` |
| Default demo runner | `fake` |
| Local model runner | `ollama` |

## 3. MVP Workflow Contract

### Workflow

1. User submits a question.
2. `Supervisor` asks `TaskRouter` for the workflow plan.
3. `ResearchWorker` returns a `ResearchResult`.
4. `WriterWorker` consumes that `ResearchResult` and returns a `FinalAnswer`.
5. `Supervisor` returns the final answer plus task traces.

### Required Schemas

- `TaskEnvelope`
- `ResearchTaskInput`
- `WriterTaskInput`
- `ResearchResult`
- `FinalAnswer`
- `TaskTrace`
- `WorkflowResult`

### Required Runtime Components

- `Supervisor`
- `TaskRouter`
- `TaskManager`
- `PromptManager`
- `ModelRunner` protocol
- `FakeModelRunner`
- `OllamaClient`
- `OllamaModelRunner`
- `AuditLogger`
- `AuditStore`
- `RetryPolicy`
- `StructuredResultCache`
- `AgentOrchestratorError`
- `ResearchWorker`
- `WriterWorker`
- `ReviewWorker` behind a feature flag

## 4. Definition Of Done

The MVP is done only when all of the following are true:

- The command `python main.py "How should I bootstrap a supervisor-worker system?" --runner fake --output json` succeeds.
- The output contains a structured `research` block, a structured `final_answer` block, and `traces`.
- `Supervisor` does not handcraft answers; it only coordinates the workflow.
- Each worker validates input and output against explicit schemas.
- A local Ollama runner exists behind the same `ModelRunner` interface.
- Audit logging can persist a run as one JSON artifact when requested.
- Local runs can be listed and inspected through a read-only audit query CLI.
- Acceptance runs can optionally persist one report artifact and query it later.
- The Ollama runner can retry model invocation or JSON parsing failures without replaying the whole workflow.
- Exact repeated requests can reuse cached structured results when cache is enabled.
- Cache TTL can expire older entries when configured.
- Cache hit, miss, or expiry status is visible in task-level trace metadata and audit artifacts.
- Local cache entries can be listed, pruned, or cleared through a dedicated CLI.
- CLI failures are classified into stable exit codes for automation.
- Automated tests cover the fixed workflow and CLI JSON output.

## 5. Executable Work Breakdown

### M0: Project Bootstrap

Deliverables:

- `pyproject.toml`
- package directories and `__init__.py` files
- CLI entrypoint
- `README.md` install and run instructions

Acceptance:

- A new contributor can create a virtualenv, install dependencies, and run tests using only the README.

### M1: Closed-Loop Orchestration

Deliverables:

- `Supervisor`
- `TaskRouter`
- `TaskManager`
- `ResearchWorker`
- `WriterWorker`
- `ReviewWorker`
- schemas for task input, worker output, and traces

Acceptance:

- The fixed `research -> writing` workflow runs end-to-end with the fake runner.
- `WorkflowResult` includes both intermediate and final structured outputs.

### M2: Local Model Adapter

Deliverables:

- `OllamaClient`
- `OllamaModelRunner`
- prompt templates for both workers
- optional JSON audit persistence
- read-only audit query CLI
- optional acceptance report persistence
- read-only acceptance report query CLI
- model-layer retry policy
- request-level structured result cache
- TTL-based cache expiry and local cache management CLI
- normalized CLI exit codes

Acceptance:

- The same workflow can be executed with `--runner ollama --model <model-name>`.
- Local-model calls are isolated behind the `ModelRunner` contract.
- Audit artifacts can be written without changing worker logic.
- Run inspection reads persisted artifacts instead of requiring a live process registry.
- Acceptance history is preserved separately from per-question workflow audit records.
- Retry logic is isolated to model execution and parse recovery.
- Cache reuse is isolated to exact request matches and does not affect workflow order.
- Cache expiry remains local, opt-in, and request-level.
- CLI automation can rely on stable exit codes instead of parsing free-form error text.

### M3: Verification Baseline

Deliverables:

- workflow unit tests
- CLI integration test
- JSON extraction/parser test for model output normalization
- architecture note

Acceptance:

- `pytest` passes locally.
- The repo contains one document that explains responsibility boundaries.

## 6. Task List For Immediate Execution

These are the first engineering tasks to create as issues or work items.

1. Create the Python package and dependency manifest.
2. Define the core schemas in `schemas/`.
3. Implement the `ModelRunner` protocol and fake runner.
4. Implement the Ollama client and runner.
5. Implement the prompt manager.
6. Implement `ResearchWorker`, `WriterWorker`, and the optional `ReviewWorker`.
7. Implement `TaskRouter`, `TaskManager`, and `Supervisor`.
8. Add `main.py` and JSON/pretty output modes.
9. Add optional JSON audit logging.
10. Add read-only run status query over persisted audit artifacts.
11. Add optional acceptance report persistence and read-only acceptance query.
12. Add model-layer retries for Ollama execution and parse recovery.
13. Add request-level structured result caching.
14. Add TTL-based cache expiry and a local cache management CLI.
15. Add normalized CLI failure classification and exit codes.
16. Add tests for workflow, CLI, audit persistence, acceptance persistence, status query, retry behavior, caching, cache expiry, cache management, exit codes, and JSON extraction.
17. Add architecture and usage documentation.

## 7. File Layout For This Milestone

```text
.
├── docs/
│   └── architecture.md
├── models/
│   ├── cached_runner.py
│   ├── fake_runner.py
│   ├── model_runner.py
│   ├── ollama_client.py
│   ├── ollama_runner.py
│   └── prompt_manager.py
├── orchestrator/
│   ├── cache.py
│   ├── acceptance.py
│   ├── acceptance_runs.py
│   ├── runs.py
│   ├── router.py
│   ├── supervisor.py
│   └── task_manager.py
├── schemas/
│   ├── acceptance_schema.py
│   ├── audit_schema.py
│   ├── cache_schema.py
│   ├── result_schema.py
│   ├── task_schema.py
│   └── worker_schema.py
├── tools/
│   ├── acceptance.py
│   ├── audit.py
│   ├── cache.py
│   ├── errors.py
│   └── retry.py
├── tests/
│   ├── test_acceptance.py
│   ├── test_acceptance_query.py
│   ├── test_audit_logging.py
│   ├── test_cache.py
│   ├── test_cache_query.py
│   ├── test_cli.py
│   ├── test_exit_codes.py
│   ├── test_ollama_runner.py
│   ├── test_run_query.py
│   ├── test_review_workflow.py
│   └── test_supervisor.py
├── workers/
│   ├── base.py
│   ├── research_worker.py
│   ├── review_worker.py
│   └── writer_worker.py
├── main.py
├── pyproject.toml
├── README.md
└── ROADMAP.md
```

## 8. Acceptance Dataset

Use at least these five questions to validate the fake or local runner workflow:

1. How should I bootstrap a supervisor-worker agent system?
2. What are the tradeoffs of fake runners versus local models in an MVP?
3. How should I define worker schemas before adding more workers?
4. What risks appear when a supervisor directly writes the final answer?
5. When should I add retry, cache, and audit layers to this system?

The pass condition is not “the wording looks nice.” The pass condition is:

- no runtime crash
- valid schema output
- correct workflow order
- final answer references the research summary instead of inventing a separate path

## 9. Next Milestone After This One

Only after the MVP above is stable should the project add:

- workflow-level retry policy
- advanced cache invalidation and eviction policy
- richer status/query APIs beyond audit-backed local inspection
- parallel branches
- human-in-the-loop checkpoints

That sequence matters because observability and control are only useful once the smallest orchestration loop already works.
