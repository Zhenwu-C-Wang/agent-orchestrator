# agent-orchestrator
A supervisor-driven multi-agent system where a central orchestrator decomposes tasks, delegates to specialized worker agents, and synthesizes final outputs. Designed for controllability, observability, and production workflows.

## Status
This repository now contains a practical local-first orchestration framework with bounded workflow planning, research and analysis paths, tool-backed local and HTTP context analysis, structured outputs, audit persistence, and a minimal Streamlit console.
The default runner is deterministic for tests and demos, and the same orchestration contract can be switched to Ollama for local model execution.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python main.py "How should I bootstrap a supervisor-worker system?" --runner fake
```

For scenario-based walkthroughs, see [docs/quickstart.md](docs/quickstart.md).
If you are evaluating the project for the first time, start with [docs/beta_quickstart.md](docs/beta_quickstart.md).
For current beta support limits and common failure modes, see [docs/known_issues.md](docs/known_issues.md).

## Streamlit UI

Run a minimal local UI that can accept input, preview the workflow plan, execute the orchestrator, and display traces plus outputs:

```bash
pip install -e '.[ui]'
streamlit run app.py
```

The UI also reads `docs/project_status.json` for a lightweight milestone snapshot and will show recent persisted runs when an audit directory is configured.

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

## Explicit Context Inputs

You can attach local files explicitly instead of embedding paths in the question:

```bash
python main.py "Summarize the most important changes in this data." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --output markdown
```

Repeat `--context-file` to attach more than one local file. The Streamlit UI exposes the same capability through the sidebar file uploader.

You can also attach URLs explicitly:

```bash
python main.py "Summarize the most important findings from this webpage." \
  --runner fake \
  --context-url https://example.com/report \
  --output markdown
```

Repeat `--context-url` to attach more than one URL. The Streamlit UI exposes the same capability through the sidebar URL input.

## Output Modes

- `--output pretty`: human-readable summary
- `--output json`: full structured `WorkflowResult`
- `--output markdown`: markdown report that is easy to save, share, or paste into docs

## Exit Codes

The CLIs use normalized non-zero exit codes for automation:

- `3`: configuration error
- `4`: model invocation error
- `5`: model response format error
- `6`: unclassified workflow execution error
- `7`: audit query error
- `8`: acceptance run finished with failed cases
- `9`: cache query or cache management error
- `10`: acceptance report query error

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

Optionally apply a TTL to treat older entries as expired on lookup:

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner ollama \
  --model qwen2.5:14b \
  --cache-dir artifacts/cache \
  --cache-max-age-seconds 3600
```

This cache remains request-level and local-disk only. It now supports opt-in TTL expiry, but it still does not implement size-based eviction or cross-version invalidation.
When caching is enabled, each `TaskTrace` also carries `cache_hit`, `cache_status`, `cache_key`, and related metadata, and the same fields are preserved in audit records.

## Cache Query

List recent cache entries:

```bash
python -m orchestrator.cache --cache-dir artifacts/cache list
```

Show cache summary stats:

```bash
python -m orchestrator.cache --cache-dir artifacts/cache stats
```

Prune expired cache entries using a TTL:

```bash
python -m orchestrator.cache --cache-dir artifacts/cache --max-age-seconds 3600 prune
```

Clear the cache directory:

```bash
python -m orchestrator.cache --cache-dir artifacts/cache clear
```

## Acceptance Run

Run the 6-question acceptance dataset with the fake runner:

```bash
python -m orchestrator.acceptance --runner fake
```

Run the same dataset against a local Ollama model:

```bash
python -m orchestrator.acceptance --runner ollama --model qwen2.5:14b
```

The dataset includes one tool-backed CSV analysis case that references `docs/sample_data/quarterly_metrics.csv`.
Use `--output json` if you want the full structured report.
Add `--with-review` to validate the optional three-stage workflow.
Add `--report-dir artifacts/acceptance` if you want one persisted acceptance record per run.

## Acceptance Report Query

List recent acceptance runs:

```bash
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance list
```

Show one acceptance run in detail:

```bash
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance show <run_id>
```

Show the latest acceptance run:

```bash
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance latest
```

Compare the latest acceptance run against the previous one:

```bash
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance compare
```

Compare two explicit acceptance runs:

```bash
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance compare <current_run_id> --baseline-run-id <baseline_run_id>
```

---

## Current Baseline

This repository should now be understood as a maintained V1 baseline rather than a greenfield MVP.

### Current Capabilities

- **Bounded workflow orchestration with two templates**: `research_then_write` and `analysis_then_write`, with optional `review` appended to either path.
- **Focused worker roles**: `ResearchWorker`, `AnalysisWorker`, `WriterWorker`, and optional `ReviewWorker`.
- **Tool-backed analysis path**: `ToolManager` currently integrates `local_file_context`, `csv_analysis`, and `http_fetch`.
- **Explicit context attachments**: `--context-file` and `--context-url` route local files and webpages into the analysis path without embedding everything into the prompt.
- **Structured outputs and traces**: each run returns a `WorkflowResult`, per-step traces, and structured tool invocation records.
- **Model flexibility**: fake and Ollama runners share the same orchestration contract.
- **Local observability**: audit persistence, run queries, acceptance persistence, and acceptance comparison all operate on local JSON artifacts.
- **Retry and cache controls**: request-level structured result caching, TTL expiry, and model-layer retry behavior are all built in.
- **Minimal local UI**: the Streamlit console previews workflow selection, executes runs, surfaces traces and tool invocations, and exposes recent persisted runs.

### Near-Term Priorities

- **More bounded workflow templates**: expand the planner with a small number of clearly testable templates for common task classes without moving to open-ended autonomous planning.
- **Stronger Ollama compatibility**: harden prompt constraints, JSON extraction, and local-model guidance so the same workflow contract behaves more consistently across supported models.
- **Better observability and regression comparison**: improve persisted run summaries and acceptance diffing so regressions are easier to spot during local iteration.

### Beta Trial Docs

- **Recommended first-run guide**: [docs/beta_quickstart.md](docs/beta_quickstart.md)
- **Known issues and support scope**: [docs/known_issues.md](docs/known_issues.md)
- **Structured feedback template**: [.github/ISSUE_TEMPLATE/beta_feedback.md](.github/ISSUE_TEMPLATE/beta_feedback.md)

### Long-Term Directions

- Parallel branches and richer human-in-the-loop execution.
- Broader tool families such as databases, notebooks, and IDE automation.
- Multi-provider model routing and third-party extensibility surfaces.

For current architecture details, see [docs/architecture.md](docs/architecture.md).
For the living roadmap, see [ROADMAP.md](ROADMAP.md).

---

## Contributing

We welcome contributions aligned with the current bounded, local-first scope. For larger long-term roadmap ideas, please open a discussion in Issues first.

See [ROADMAP.md](ROADMAP.md) for the current baseline, near-term priorities, and long-term directions.

## Project Layout

- [app.py](./app.py)
- [main.py](./main.py)
- [orchestrator/](./orchestrator)
- [workers/](./workers)
- [models/](./models)
- [schemas/](./schemas)
- [tools/](./tools)
- [tests/](./tests)
- [docs/architecture.md](./docs/architecture.md)
- [docs/beta_quickstart.md](./docs/beta_quickstart.md)
- [docs/known_issues.md](./docs/known_issues.md)
- [docs/quickstart.md](./docs/quickstart.md)
- [ROADMAP.md](./ROADMAP.md)
