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

---

## Vision: Multi-Functional AI Systems Framework

This MVP provides the **orchestration foundation** for a comprehensive multi-agent system. The long-term vision extends this into a **multi-functional intelligent systems framework** supporting:

### Current Capabilities ✅
- **Fixed workflow orchestration**: Research → Writing → Review (optional)
- **Multi-role system**: Specialized workers with distinct responsibilities
- **Structured I/O schemas**: Type-safe task inputs and outputs via Pydantic
- **Model flexibility**: Switch between fake runners and local Ollama models
- **Audit & observability**: Full trace capture with task metadata and timing
- **Caching & retries**: Request-level caching with TTL, model-layer retries
- **Acceptance testing**: Regression detection across workflow runs

### Planned Enhancements (Phases 2-4)

#### Phase 2: Dynamic Workflows & Tool Integration
- 🔹 **Adaptive routing**: Route questions to different worker chains based on intent
- 🔹 **Tool management**: Integrate web scrapers, data analyzers, code executors, APIs
- 🔹 **NLP decomposition**: Break complex tasks into sub-workflows automatically
- 🔹 **Example use cases**:
  - Technical questions → Research + Code Analysis + Testing
  - Data questions → Fetch Data + Analyze + Visualize
  - Multi-step workflows → Decompose → Execute in parallel → Synthesize

#### Phase 3: Parallel Execution & Interactivity
- 🔹 **Concurrent workers**: Execute multiple workers in parallel with DAG scheduling
- 🔹 **Multi-agent collaboration**: Inter-worker communication and result aggregation
- 🔹 **Human-in-the-loop**: Approval checkpoints and mid-execution feedback
- 🔹 **Rich output formats**: Markdown reports, HTML dashboards, Jupyter notebooks, PDFs
- 🔹 **IDE automation**: VSCode project scaffolding, Jupyter notebook generation

#### Phase 4: Enterprise & Extensibility
- 🔹 **Multi-provider support**: OpenAI, Anthropic, HuggingFace alongside Ollama
- 🔹 **Enterprise observability**: OpenTelemetry, Prometheus metrics, audit trails
- 🔹 **Plugin marketplace**: Community-contributed workers and tools
- 🔹 **Advanced resource mgmt**: Cost optimization, rate limiting, resource pooling

For detailed roadmap, see [ROADMAP.md](ROADMAP.md) § 10 (Future Vision).

---

## Contributing

We welcome contributions aligned with the MVP scope. For larger features (Phases 2+), please open a discussion in Issues first.

See [ROADMAP.md](ROADMAP.md) for implementation phases and capability matrix.
```

Compare two explicit acceptance runs:

```bash
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance compare <current_run_id> --baseline-run-id <baseline_run_id>
```

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
