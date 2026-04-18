# agent-orchestrator
A supervisor-driven multi-agent system where a central orchestrator decomposes tasks, delegates to specialized worker agents, and synthesizes final outputs. Designed for controllability, observability, and production workflows.

## Status
This repository now contains a practical local-first orchestration framework with bounded workflow planning across research, analysis, comparison, and hybrid advisory/context paths, tool-backed local and HTTP context analysis, bounded dataset computation, structured outputs, audit persistence, and a guided Streamlit console.
The default runner is deterministic for tests and demos, and the same orchestration contract can be switched to Ollama for local model execution.
The repo now also includes a packaging-friendly desktop launcher entrypoint plus packaged first-run smoke tests for future installer builds, but true no-terminal installer distribution is still a separate milestone rather than a shipped surface today.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python main.py "How should I bootstrap a supervisor-worker system?" --runner fake
```

For scenario-based walkthroughs, see [docs/quickstart.md](docs/quickstart.md).
If you prefer a Chinese guide, see [docs/manual_zh.md](docs/manual_zh.md).
If you are evaluating the project for the first time, start with [docs/beta_quickstart.md](docs/beta_quickstart.md).
For the current beta support promise, see [docs/beta_support_matrix.md](docs/beta_support_matrix.md).
For the standard tester prompts and expected workflow paths, see [docs/beta_task_pack.md](docs/beta_task_pack.md).
For current beta support limits and common failure modes, see [docs/known_issues.md](docs/known_issues.md).

If you want the simplest local beta launcher:

```bash
bash scripts/start_beta.sh
```

If you want the UI through the packaging-friendly Python entrypoint after installing `.[ui]`:

```bash
agent-orchestrator-ui
```

## Streamlit UI

Run a minimal local UI that can accept input, preview the workflow plan, execute the orchestrator, and display traces plus outputs:

```bash
pip install -e '.[ui]'
streamlit run app.py
```

Or launch the same UI through the packaging-oriented entrypoint:

```bash
agent-orchestrator-ui
```

The UI also reads `docs/project_status.json` for a lightweight milestone snapshot, surfaces guided workflow warnings before execution, and shows recent persisted runs when an audit directory is configured.
Guided mode is enabled by default and now includes built-in starter tasks so first-time testers can run the main workflow families without hunting for sample files manually.
When you switch the runner to `ollama`, the UI now performs a local-model readiness check before execution and gives plain-language guidance if Ollama is offline or the configured model is not installed yet.
Completed runs now render through guided inspection tabs for overview, intermediates, tools, traces, exports, and raw JSON, and the operations panel can also inspect persisted acceptance reports plus local cache health when those directories are configured.
Those operational views now include drill-downs for individual acceptance cases and cache entries.
The `agent-orchestrator-ui` entrypoint is mainly there to give future installer packaging a stable launch target. It does not yet mean the repo ships a native desktop installer.

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

The bounded analysis toolchain currently understands local CSV and JSON snapshots especially well, including explicit numeric change computation. For example:

```bash
python main.py "Summarize the most important changes in this JSON snapshot." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.json \
  --output markdown
```

If you want a broader recommendation workflow instead of a narrow summary, attach explicit context and ask for a decision or prioritization recommendation:

```bash
python main.py "Analyze this dataset and recommend what we should prioritize next." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --output json
```

This routes to the bounded hybrid workflow `research_then_analysis_then_write`, so the final answer can combine high-level reasoning with tool-backed dataset findings.

When you want to compare multiple explicit contexts, attach both and ask for a comparison directly:

```bash
python main.py "Compare these datasets and summarize the most important differences." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --context-file docs/sample_data/quarterly_metrics_baseline.csv \
  --output json
```

This routes to `comparison_then_write`. If you ask which dataset or source you should prioritize next, the planner broadens that into `research_then_comparison_then_write`.

You can also attach URLs explicitly:

```bash
python main.py "Summarize the most important findings from this webpage." \
  --runner fake \
  --context-url https://example.com/report \
  --output markdown
```

Repeat `--context-url` to attach more than one URL. The Streamlit UI exposes the same capability through the sidebar URL input.

By default, file paths and URLs embedded directly in the question text are ignored. Re-enable inline discovery only when you want it:

```bash
python main.py "Analyze `docs/sample_data/quarterly_metrics.csv` and summarize the most important changes." \
  --runner fake \
  --allow-inline-context-files
```

```bash
python main.py "Summarize the most important findings from https://example.com/report." \
  --runner fake \
  --allow-inline-context-urls
```

If a selected tool fails, the workflow exits non-zero instead of continuing with an ungrounded analysis result.

## Output Modes

- `--output pretty`: human-readable summary
- `--output json`: full structured `WorkflowResult`
- `--output markdown`: markdown report that is easy to save, share, or paste into docs

## Exit Codes

The CLIs use normalized non-zero exit codes for automation:

- `3`: configuration error
- `4`: model invocation error
- `5`: model response format error
- `6`: workflow execution error, including tool execution failures
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

Run the 10-question acceptance dataset with the fake runner:

```bash
python -m orchestrator.acceptance --runner fake
```

Run the same dataset against a local Ollama model:

```bash
python -m orchestrator.acceptance --runner ollama --model qwen2.5:14b
```

The dataset includes one tool-backed CSV analysis case, one tool-backed JSON analysis case, one comparison case over paired datasets, and hybrid advisory cases for both analysis and comparison. The structured-data cases all exercise bounded numeric computation in addition to schema inspection.
Use `--output json` if you want the full structured report.
Add `--with-review` to validate the optional review-augmented workflow.
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

- **Bounded workflow orchestration with five templates**: `research_then_write`, `analysis_then_write`, `research_then_analysis_then_write`, `comparison_then_write`, and `research_then_comparison_then_write`, with optional `review` appended to any of them.
- **Focused worker roles**: `ResearchWorker`, `AnalysisWorker`, `ComparisonWorker`, `WriterWorker`, and optional `ReviewWorker`.
- **Tool-backed analysis and comparison paths**: `ToolManager` currently integrates `local_file_context`, `csv_analysis`, `json_analysis`, `data_computation`, and `http_fetch`.
- **Explicit context attachments with opt-in inline discovery**: `--context-file` and `--context-url` are the default path for attached context, while `--allow-inline-context-files` and `--allow-inline-context-urls` re-enable question-text discovery only when you want it.
- **Structured outputs and traces**: each run returns a `WorkflowResult`, per-step traces, and structured tool invocation records.
- **Model flexibility**: fake and Ollama runners share the same orchestration contract.
- **Local observability**: audit persistence, run queries, acceptance persistence, and acceptance comparison all operate on local JSON artifacts.
- **Retry and cache controls**: request-level structured result caching, TTL expiry, and model-layer retry behavior are all built in.
- **Guided local UI**: the Streamlit console previews workflow selection, surfaces route warnings and inspection summaries, renders recent runs, and exposes acceptance/cache inspection with per-item drill-downs plus shareable JSON/Markdown export.

### Near-Term Priorities

- **More bounded workflow templates**: continue broadening the planner carefully beyond the current five-route baseline without moving to open-ended autonomous planning.
- **Stronger Ollama compatibility**: harden prompt constraints, JSON extraction, and local-model guidance so the same workflow contract behaves more consistently across supported models.
- **Better observability, regression comparison, and beta feedback loops**: improve persisted run summaries, acceptance diffing, and external trial feedback capture so regressions and onboarding friction are easier to spot.

### Beta Trial Docs

- **Recommended first-run guide**: [docs/beta_quickstart.md](docs/beta_quickstart.md)
- **Chinese usage manual**: [docs/manual_zh.md](docs/manual_zh.md)
- **One-command beta launcher**: [scripts/start_beta.sh](./scripts/start_beta.sh)
- **Support matrix**: [docs/beta_support_matrix.md](docs/beta_support_matrix.md)
- **Standard trial prompts**: [docs/beta_task_pack.md](docs/beta_task_pack.md)
- **Known issues and support scope**: [docs/known_issues.md](docs/known_issues.md)
- **macOS packaging preview**: [docs/macos_packaging.md](docs/macos_packaging.md)
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

- [.github/ISSUE_TEMPLATE/](./.github/ISSUE_TEMPLATE)
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
- [docs/beta_support_matrix.md](./docs/beta_support_matrix.md)
- [docs/beta_task_pack.md](./docs/beta_task_pack.md)
- [docs/known_issues.md](./docs/known_issues.md)
- [docs/macos_packaging.md](./docs/macos_packaging.md)
- [docs/manual_zh.md](./docs/manual_zh.md)
- [docs/quickstart.md](./docs/quickstart.md)
- [desktop_launcher.py](./desktop_launcher.py)
- [scripts/build_macos_app.sh](./scripts/build_macos_app.sh)
- [scripts/build_macos_dmg.sh](./scripts/build_macos_dmg.sh)
- [scripts/validate_macos_app.sh](./scripts/validate_macos_app.sh)
- [scripts/validate_macos_dmg.sh](./scripts/validate_macos_dmg.sh)
- [scripts/start_beta.sh](./scripts/start_beta.sh)
- [ROADMAP.md](./ROADMAP.md)
