# agent-orchestrator
A supervisor-driven multi-agent system where a central orchestrator decomposes tasks, delegates to specialized worker agents, and synthesizes final outputs. Designed for controllability, observability, and production workflows.

## Status
This repository now contains an executable MVP skeleton for a fixed `ResearchWorker -> WriterWorker` workflow. The default runner is deterministic for tests and demos, and the same flow can be switched to Ollama for local model execution.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python main.py "How should I bootstrap a supervisor-worker system?" --runner fake
```

## Run With Ollama

Start Ollama locally, then run:

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner ollama \
  --model llama3.1
```

By default the Ollama client calls `http://localhost:11434`.

## Output Modes

- `--output pretty`: human-readable summary
- `--output json`: full structured `WorkflowResult`

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

## Project Layout

- [main.py](./main.py)
- [orchestrator/](./orchestrator)
- [workers/](./workers)
- [models/](./models)
- [schemas/](./schemas)
- [tests/](./tests)
- [docs/architecture.md](./docs/architecture.md)
- [ROADMAP.md](./ROADMAP.md)
