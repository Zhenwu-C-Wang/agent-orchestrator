# Architecture Note

This repository now implements a practical local-first orchestration framework rather than a single fixed MVP demo.

## Current Shape

The runtime is intentionally bounded:

- `TaskPlanner` classifies a request into one of five workflow templates.
- `TaskRouter` turns that plan into task inputs.
- `Supervisor` executes the selected worker chain, collects traces, and aggregates tool invocation records.
- `ResearchWorker`, `AnalysisWorker`, `ComparisonWorker`, `WriterWorker`, and optional `ReviewWorker` stay focused on one contract each.
- `ToolManager` owns bounded tool execution for the analysis and comparison paths.
- `ModelRunner` implementations own structured model calls, retries, and cache integration.

The current workflow templates are:

1. `research_then_write`
2. `analysis_then_write`
3. `research_then_analysis_then_write`
4. `comparison_then_write`
5. `research_then_comparison_then_write`
6. optional `review` appended to any of the bounded paths

## Responsibility Boundaries

- `Supervisor` owns workflow execution, worker lookup, sequencing, trace collection, and result aggregation.
- `TaskPlanner` owns bounded workflow selection from the user request, including hybrid analysis and hybrid comparison routes.
- `TaskRouter` owns task-input construction from workflow steps and intermediate context.
- `TaskManager` owns task identifiers and task envelope creation.
- `ResearchWorker` owns research-summary generation only.
- `AnalysisWorker` owns tool-backed analysis preparation plus structured analysis generation.
- `ComparisonWorker` owns tool-backed comparison preparation plus structured comparison generation.
- `WriterWorker` owns final-answer generation from one or more intermediate worker results.
- `ReviewWorker` owns consistency checking between the intermediate worker results and the final answer.
- `PromptManager` owns prompt wording and prompt payload construction.
- `ToolManager` owns tool selection and structured invocation recording for supported tasks.
- local tool adapters own one narrow execution behavior each, such as file preview or CSV summarization.
- `ModelRunner` implementations own model invocation and structured parsing.
- `AuditLogger` owns JSON persistence for completed or failed workflow runs.
- `AuditStore` owns read-only inspection of persisted workflow runs.
- `AcceptanceLogger` owns JSON persistence for completed acceptance reports.
- `AcceptanceStore` owns read-only inspection of persisted acceptance reports.
- `RetryPolicy` owns model-layer retry behavior and backoff configuration.
- `StructuredResultCache` owns exact request-level structured result reuse and opt-in TTL expiry.
- `orchestrator.cache` owns local cache inspection and maintenance commands.
- `AgentOrchestratorError` and CLI wrappers own error classification and exit-code normalization.

## Why Planning Is Bounded

The project now supports multiple workflow templates, but it still avoids open-ended autonomous planning. Bounded planning gives us:

- predictable trace order
- testable workflow selection
- stable schemas across fake and Ollama runners
- room to add more templates later without losing control of the first release

## Why Tools Live Behind `ToolManager`

Tool execution is intentionally isolated from worker orchestration and model invocation.

That split keeps several things clean:

- `AnalysisWorker` and `ComparisonWorker` can request tool context without knowing how file inspection or CSV summarization are implemented.
- tool invocations are recorded in one structured format and can surface in workflow results, audit records, CLI output, and the UI.
- adding a new tool does not require rewriting supervisor logic.

The current tool path is still bounded and guarded:

- `local_file_context` reads a bounded preview of explicitly attached local files, or inline file paths only when that opt-in switch is enabled
- `csv_analysis` computes lightweight CSV structure and numeric summaries
- `json_analysis` computes lightweight JSON structure, key-path, and numeric-field summaries
- `data_computation` computes bounded first/last deltas and aggregate metrics for explicit CSV and JSON datasets
- `http_fetch` fetches a small text preview from explicitly attached URLs, or inline URLs only when that opt-in switch is enabled
- tool failures stop the workflow instead of silently degrading into an ungrounded analysis

## Why Two Runners Exist

- `FakeModelRunner` gives deterministic output for local demos, acceptance validation, and regression tests.
- `OllamaModelRunner` validates that the same orchestration contract can run against a real local model.

The key design constraint is that switching runners should not require changing planner, router, supervisor, or worker sequencing.

## Why Review Is Optional

The review stage adds useful validation but also adds latency and another structured-output dependency. Keeping it behind a flag allows the base workflow to stay fast while preserving a stable path for stricter checks.

## Why Audit And Acceptance Persistence Stay File-Based

The current runtime is intentionally local-first. Audit and acceptance data are stored as JSON artifacts instead of introducing a database or daemon.

That gives us:

- easy inspection
- easy cleanup
- deterministic local testing
- a simple persistence model for the Streamlit UI and CLI query commands

## Why Output Exists In Three Modes

The project now supports:

- `pretty` for terminal-first reading
- `json` for automation and debugging
- `markdown` for reports, docs, and sharing

Each mode is produced from the same structured workflow result so presentation changes do not require re-running the orchestration.

## Why Acceptance Now Covers Tool-Backed Cases

The acceptance dataset includes one CSV-backed analysis case, one JSON-backed analysis case, one paired-dataset comparison case, and hybrid advisory cases for both analysis and comparison, all attached explicitly.

That matters because we no longer only validate:

- workflow routing
- structured output
- review behavior

We also validate:

- local file detection
- tool invocation recording
- tool-backed analysis synthesis
- tool-backed comparison synthesis across paired explicit contexts
- bounded numeric computation over explicit structured datasets
- hybrid routing that carries research context into tool-backed analysis and final synthesis
- hybrid routing that carries research context into tool-backed comparison and final synthesis
- bounded HTTP-backed context analysis through local integration tests

## User-Facing Surfaces

The current system is usable through:

- `main.py` for one-off workflow execution
- `orchestrator.runs` for audit inspection
- `orchestrator.acceptance` and `orchestrator.acceptance_runs` for validation workflows
- `orchestrator.cache` for cache inspection and maintenance
- `app.py` for a guided Streamlit console with workflow preview, route warnings, run history, acceptance and cache inspection, per-case/per-entry drill-downs, and result export

## What Is Deliberately Missing

- parallel execution
- workflow-level retry and recovery
- broad external API or web tool families
- database-backed persistence
- streaming UI updates
- human approval checkpoints
- multi-provider model routing

Those are all reasonable future directions, but the current version is intentionally optimizing for:

- local usability
- inspectability
- bounded orchestration
- testability
