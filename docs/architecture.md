# Architecture Note

This repository implements one narrow orchestration contract on purpose.

## Responsibility Boundaries

- `Supervisor` owns workflow execution, worker lookup, sequencing, and trace collection.
- `TaskRouter` owns the fixed plan and task-input construction.
- `TaskManager` owns task identifiers and task envelope creation.
- `ResearchWorker` owns only the research summary contract.
- `WriterWorker` owns only final-answer generation from research output.
- `ReviewWorker` owns only consistency checking between research output and final answer.
- `PromptManager` owns prompt wording and prompt payload construction.
- `ModelRunner` implementations own model invocation and structured parsing.
- `AuditLogger` owns JSON persistence for completed or failed workflow runs.
- `AuditStore` owns read-only inspection of persisted workflow runs.
- `AcceptanceLogger` owns JSON persistence for completed acceptance reports.
- `AcceptanceStore` owns read-only inspection of persisted acceptance reports.
- `RetryPolicy` owns model-layer retry behavior and backoff configuration.
- `StructuredResultCache` owns exact request-level structured result reuse and opt-in TTL expiry.
- `orchestrator.cache` owns local cache inspection and maintenance commands.
- `AgentOrchestratorError` and CLI wrappers own error classification and exit-code normalization.

## Why The Workflow Is Fixed

The project is proving orchestration mechanics first, not agent autonomy. A fixed `research -> writing` path prevents scope creep and makes schema regressions obvious. The optional `review` stage is constrained to validation, not autonomous replanning.

## Why Two Runners Exist

- `FakeModelRunner` gives deterministic output for local demos and tests.
- `OllamaModelRunner` validates that the architecture can switch to a real local model without changing supervisor or worker code.

## Why Review Is Optional

The review stage adds useful signal, but it also adds latency and another structured-output dependency. Keeping it behind a flag allows the base workflow to stay fast while the project hardens the consistency-check contract.

## Why Audit Logging Is Optional

Audit persistence is useful for debugging local-model behavior and preserving traces from real runs, but it should not be forced on every invocation. Making it opt-in keeps the default workflow clean while preserving a stable path for investigation.

## Why Status Query Reads Audit Artifacts

The current status layer is intentionally read-only. It reads persisted audit JSON files instead of introducing a database, daemon, or mutable runtime registry. That keeps the implementation simple and aligned with the local-first workflow.

## Why Acceptance Reports Persist Separately

Acceptance runs answer a different question than workflow audit artifacts. Audit records preserve one workflow execution at a time, while acceptance records preserve one validation session across the fixed question set. Keeping them separate avoids mixing per-question traces with higher-level pass/fail history.

## Why Exit Codes Are Normalized

This project is increasingly scriptable. Once audit, cache, retries, and acceptance flows exist, shell automation needs something more precise than a generic non-zero exit. Typed exit codes let callers distinguish configuration mistakes from model failures and validation failures without parsing human-readable output.

## Why Retries Are Limited To The Model Layer

Retrying the whole workflow would create duplicated worker executions and make trace reasoning harder. The current system only retries the Ollama invocation and structured parsing step, which improves resilience without changing orchestration semantics.

## Why Cache TTL Is Opt-In

The current cache is intentionally narrow. It reuses exact structured results for identical requests, and TTL expiry is optional because some local workflows prefer deterministic reuse over freshness heuristics. The implementation now handles simple staleness control, but it still avoids broader eviction and compatibility policy.

## Why Cache Observability Lives In Task Traces

Cache behavior affects each worker step, not just the overall run. Surfacing `cache_hit`, `cache_status`, `cache_key`, and attempt metadata on `TaskTrace` keeps the signal close to the execution step that used it and automatically carries the same information into audit records.

## What Is Deliberately Missing

- retries
- advanced cache invalidation and eviction policies
- streaming
- human approval
- persistence

In this list, "retries" now specifically means workflow-level retry and recovery policies. Lightweight model-layer retries are already implemented, and caching now specifically means broader cache lifecycle policy beyond exact request reuse and optional TTL expiry.

Those features are useful only after the base contract is stable.
