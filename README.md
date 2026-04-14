# agent-orchestrator
A supervisor-driven multi-agent system where a central orchestrator decomposes tasks, delegates to specialized worker agents, and synthesizes final outputs. Designed for controllability, observability, and production workflows.

## Status
This repository now contains an executable MVP skeleton for a fixed `ResearchWorker -> WriterWorker` workflow. The default runner is deterministic for tests and demos, and the same flow can be switched to Ollama for local model execution.
An optional `ReviewWorker` can be enabled to check whether the final answer remains consistent with the research result.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python main.py "How should I bootstrap a supervisor-worker system?" --runner fake
```

Enable the optional review stage:

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner fake \
  --with-review
```

## Run With Ollama

Start Ollama locally, then run:

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner ollama \
  --model llama3.1
```

By default the Ollama client calls `http://localhost:11434`.
By default the Ollama runner uses `--max-retries 1 --retry-backoff-seconds 0.25` for model-layer retries only.

## Output Modes

- `--output pretty`: human-readable summary
- `--output json`: full structured `WorkflowResult`

## Exit Codes

The CLIs use normalized non-zero exit codes for automation:

- `3`: configuration error
- `4`: model invocation error
- `5`: model response format error
- `6`: unclassified workflow execution error
- `7`: audit query error
- `8`: acceptance run finished with failed cases

## Audit Logs

Write one JSON audit record for a single run:

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner fake \
  --audit-dir artifacts/runs
```

Write one JSON audit record per acceptance question:

```bash
python -m orchestrator.acceptance --runner fake --audit-dir artifacts/runs
```

Each record contains run metadata, traces, final structured output, and failure details when a run crashes.

## Run Status Query

List recent persisted runs:

```bash
python -m orchestrator.runs --audit-dir artifacts/runs list
```

Show one run in detail:

```bash
python -m orchestrator.runs --audit-dir artifacts/runs show <run_id>
```

Show the latest run:

```bash
python -m orchestrator.runs --audit-dir artifacts/runs latest
```

## Model Retry

The Ollama runner can retry model calls or JSON-parse failures without replaying the whole workflow:

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner ollama \
  --model qwen2.5:14b \
  --max-retries 2 \
  --retry-backoff-seconds 0.5
```

This retry logic is limited to the model layer. It does not replay completed workflow steps.

## Request Cache

The system can reuse structured model results when the runner, model, prompts, payload, and response schema are identical:

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner ollama \
  --model qwen2.5:14b \
  --cache-dir artifacts/cache
```

This cache is request-level and local-disk only. It does not implement TTL, eviction, or cross-version invalidation.
When caching is enabled, each `TaskTrace` also carries `cache_hit`, `cache_key`, and related metadata, and the same fields are preserved in audit records.

## Acceptance Run

Run the fixed 5-question acceptance dataset with the fake runner:

```bash
python -m orchestrator.acceptance --runner fake
```

Run the same dataset against a local Ollama model:

```bash
python -m orchestrator.acceptance --runner ollama --model qwen2.5:14b
```

Use `--output json` if you want the full structured report.
Add `--with-review` to validate the optional three-stage workflow.

## Project Layout

- [main.py](./main.py)
- [orchestrator/](./orchestrator)
- [workers/](./workers)
- [models/](./models)
- [schemas/](./schemas)
- [tools/](./tools)
- [tests/](./tests)
- [docs/architecture.md](./docs/architecture.md)
- [ROADMAP.md](./ROADMAP.md)
