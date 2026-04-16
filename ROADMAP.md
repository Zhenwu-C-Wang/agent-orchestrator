# ROADMAP: Stabilize The Current V1 And Extend It Carefully

This repository is no longer best described as a greenfield MVP plan. The practical V1 baseline is largely in place. The roadmap now exists to document what is already true, what the next disciplined improvements should be, and which ideas remain intentionally deferred to the long term.

## 1. Product Positioning

The current project target is:

- keep the orchestrator immediately usable for local work
- preserve bounded planning, inspectability, and schema stability
- make incremental improvements without reopening the architecture every week

The repository should be treated as a maintained local-first orchestration baseline, not as a blank-slate platform build.

## 2. Current Baseline

### What Exists Today

- Python 3.11+ implementation with `pydantic` schemas and `pytest` coverage
- one `Supervisor` coordinating bounded workflow execution
- one `TaskPlanner` choosing between five workflow templates:
  - `research_then_write`
  - `analysis_then_write`
  - `research_then_analysis_then_write`
  - `comparison_then_write`
  - `research_then_comparison_then_write`
- one `TaskRouter` that converts workflow steps plus intermediate context into worker inputs
- one `TaskManager` for task envelope creation and traceable task IDs
- focused worker roles:
  - `ResearchWorker`
  - `AnalysisWorker`
  - `ComparisonWorker`
  - `WriterWorker`
  - optional `ReviewWorker`
- a shared `ModelRunner` contract with:
  - deterministic `FakeModelRunner`
  - local `OllamaModelRunner`
- a bounded `ToolManager` with current tool adapters:
  - `local_file_context`
  - `csv_analysis`
  - `json_analysis`
  - `data_computation`
  - `http_fetch`
- explicit context attachment through `--context-file` and `--context-url`
- opt-in inline context discovery through `--allow-inline-context-files` and `--allow-inline-context-urls`
- output modes for `pretty`, `json`, and `markdown`
- local JSON audit persistence plus read-only run inspection CLI
- local JSON acceptance persistence plus read-only acceptance query and comparison CLI
- model-layer retry and parse recovery for Ollama calls
- request-level structured result caching with optional TTL expiry
- local cache inspection and maintenance CLI
- normalized CLI exit codes for automation
- a guided Streamlit console for plan preview, route warnings, result inspection, recent-run visibility, acceptance inspection, cache inspection, and export
- beta-facing onboarding docs, support matrix, trial task pack, and a structured beta feedback template

### Current Constraints

The present baseline is intentionally bounded. It does not yet aim to provide:

- open-ended autonomous planning
- parallel execution or DAG scheduling
- workflow-level retry or recovery
- broad external tool families beyond the current local-first set
- database-backed persistence
- multi-provider model routing
- plugin marketplaces or third-party worker ecosystems

Those are not omissions by accident. They are scope choices that preserve local usability, inspectability, and testability.

## 3. Current Runtime Contract

### Workflow

1. A user submits one question plus optional explicit context files or URLs.
2. `TaskPlanner` selects a bounded workflow template.
3. `TaskRouter` builds each step input from the question and accumulated context.
4. `Supervisor` executes the worker chain in order.
5. `AnalysisWorker` or `ComparisonWorker` may invoke registered tools through `ToolManager`.
6. `WriterWorker` produces the final structured answer.
7. `ReviewWorker` may validate the answer when enabled.
8. `Supervisor` returns the final result, traces, tool invocations, and metadata.

### Core Schemas

- `TaskEnvelope`
- `WorkflowPlan`
- `WorkflowStep`
- `ToolInvocation`
- `ResearchTaskInput`
- `AnalysisTaskInput`
- `ComparisonTaskInput`
- `WriterTaskInput`
- `ReviewTaskInput`
- `ResearchResult`
- `AnalysisResult`
- `ComparisonResult`
- `FinalAnswer`
- `ReviewResult`
- `TaskTrace`
- `WorkflowResult`

### Runtime Components

- `Supervisor`
- `TaskPlanner`
- `TaskRouter`
- `TaskManager`
- `PromptManager`
- `ModelRunner` protocol
- `FakeModelRunner`
- `OllamaClient`
- `OllamaModelRunner`
- `CachedModelRunner`
- `ToolManager`
- `Tool` protocol
- `ResearchWorker`
- `AnalysisWorker`
- `ComparisonWorker`
- `WriterWorker`
- `ReviewWorker`
- `AuditLogger` and `AuditStore`
- `AcceptanceLogger` and `AcceptanceStore`
- `RetryPolicy`
- `StructuredResultCache`
- `AgentOrchestratorError`

## 4. Baseline Maintenance Criteria

The current V1 baseline should continue to satisfy all of the following:

- `python main.py "How should I bootstrap a supervisor-worker system?" --runner fake --output json` succeeds.
- the planner selects bounded workflow templates instead of falling back to one hard-coded path.
- the analysis and comparison paths can incorporate explicit local files or URLs through the registered tool layer.
- `Supervisor` coordinates workflow execution and does not handcraft worker answers.
- worker inputs and outputs stay schema-validated.
- fake and Ollama runners remain interchangeable behind the same orchestration contract.
- audit records can be written and inspected without requiring a separate service.
- acceptance runs can be persisted and compared through local report artifacts.
- cache status and retry metadata remain visible in traces and persisted artifacts.
- the guided Streamlit inspection surfaces remain aligned with the underlying workflow result and persisted artifact formats.
- automated tests keep covering workflow selection, tool usage, CLI output, persistence, and query flows.

## 5. Next Milestone

The next milestone should stay narrow. It should improve the usefulness and stability of the existing baseline without turning into a platform rewrite.

### 5.1 More Bounded Workflow Templates

Goal:
- add a small number of clearly testable templates for common task classes that are not well served by the current five-path planner

Expected changes:
- extend planner classification rules in a deterministic, inspectable way
- add router input construction for any new template-specific context
- add worker logic only when the new template truly requires a different contract
- add acceptance cases that prove the new template is selected for the right requests

Guardrails:
- do not introduce open-ended autonomous task graph generation
- do not add templates whose routing logic cannot be explained or tested

### 5.2 Stronger Ollama Compatibility

Goal:
- make local-model execution more robust across a small, documented set of Ollama models

Expected changes:
- refine prompt constraints for structured JSON output
- harden extraction and parse recovery around real model variance
- document a supported or known-good local model matrix
- keep retry logic isolated to the model layer

Guardrails:
- do not let model-specific branching leak into planner or supervisor behavior
- do not treat retries as workflow replay

### 5.3 Better Observability And Regression Comparison

Goal:
- make persisted run history and acceptance history more useful during day-to-day iteration

Expected changes:
- enrich run and acceptance summaries with higher-signal metadata
- improve acceptance comparison output so regressions are easier to spot
- keep documentation aligned with the actual CLI inspection surfaces

Guardrails:
- stay file-based and local-first for now
- do not add database or distributed tracing infrastructure in this milestone

### 5.4 Desktop Packaging Foundation

Goal:
- prepare the repo for a future installer-based beta aimed at non-technical users who should not need to open a terminal

Expected changes:
- provide a packaging-friendly Python UI launcher that can serve as the stable target for native app bundlers
- separate the current repo-based technical beta from the future installer-based beta in docs and support statements
- identify one narrow first platform for installer packaging instead of promising every operating system at once
- validate `macOS` as the first installer-preview target before widening platform scope
- move default writable runtime artifacts toward user-friendly locations once the packaging story solidifies

Guardrails:
- do not claim native installer support before an actual packaged build exists
- do not let packaging work destabilize the current repo-based beta path
- do not expand into hosted deployment or multi-user infrastructure as part of installer prep

## 6. Trial Readiness / Beta Readiness

This section defines the gate for inviting external users to try the project. The goal is not to make the system universally deployable yet. The goal is to make one trial path clear, repeatable, and supportable.

### 6.1 First Beta Audience

The first beta should target:

- technical users who are comfortable cloning a repository and running a Python project locally
- evaluators who can follow a short setup guide without live assistance
- users who can provide actionable feedback about workflow quality, setup friction, and failure modes

The first beta should not target:

- non-technical users
- users who expect a hosted SaaS experience
- users who need production uptime, data guarantees, or multi-user collaboration

Default assumption for the first wave:

- macOS or Linux users
- Python 3.11+
- terminal access
- optional Ollama installation for the local-model path

### 6.2 Recommended Trial Surfaces

The beta should expose one primary path and one secondary path:

- primary trial surface: `streamlit run app.py`
- secondary validation surface: `python main.py "..."`

The primary beta flow should use:

- fake runner for the fastest smoke test and deterministic onboarding
- optional Ollama follow-up path for testers who want to evaluate real local-model behavior

Guardrails:

- do not ask first-wave testers to choose between many entrypoints
- do not require Ollama for the very first success path
- do not position the fake runner as model-quality validation; use it only for setup and workflow validation

### 6.3 Beta Deliverables

Before inviting external testers, the repo should provide:

- one beta-facing quickstart path that gets a new tester to a successful run in 5-10 minutes
- one recommended command or UI path for first use, with no branching decisions until after the first successful run
- one short supported-environment matrix in `README.md` or a beta guide
- one known-issues section covering the most likely setup and runtime failures
- one standard feedback template asking for environment, runner, task, observed behavior, and reproduction steps
- one small sample task pack that lets testers evaluate the system consistently

Recommended documentation additions:

- `docs/beta_quickstart.md` or an equivalent section in `README.md`
- `docs/beta_support_matrix.md` or an equivalent support section in `README.md`
- `docs/beta_task_pack.md` or an equivalent standard tester prompt pack
- `docs/known_issues.md` or an equivalent concise troubleshooting section
- a GitHub issue template or lightweight feedback form

### 6.4 Supported Environment Matrix

The first beta should publish a narrow support statement instead of implying broad compatibility.

Required to document:

- supported operating systems for the first wave
- required Python version
- whether the Streamlit UI is the recommended entrypoint
- whether Ollama is optional or required for each evaluation path
- one or more known-good Ollama model names
- expected hardware baseline for the Ollama path, even if approximate

Minimum support promise for the first beta:

- fake runner path is expected to work on supported systems
- Ollama path is best-effort outside the documented model matrix
- unsupported environments should fail with clear guidance, not silent ambiguity

### 6.5 Standard Trial Script

Every external tester should be asked to try the same small script before free-form exploration.

Required trial tasks:

1. Run the Streamlit UI or CLI with the fake runner and complete one research-style request.
2. Run one analysis-style request against `docs/sample_data/quarterly_metrics.csv`.
3. Inspect traces or tool invocations to verify the workflow is understandable.
4. If Ollama is installed, rerun one task with a documented supported model.
5. Report one positive impression and one point of friction.

Required success condition for each trial:

- the tester reaches one successful end-to-end result without direct intervention from the maintainer
- the tester can identify which workflow path ran
- the tester can tell when tools were used
- the tester knows what to do next after the first run

### 6.6 Beta Exit Criteria

The project is ready for external trial use only when all of the following are true:

- a new tester can complete the recommended first-run path using only the published docs
- the fake-runner smoke test succeeds consistently on supported systems
- the sample CSV analysis workflow succeeds consistently on supported systems
- the Streamlit UI and CLI both surface enough information to understand workflow selection and failures
- README commands and beta docs have been manually re-verified against current CLI flags
- the repo clearly states what is supported, what is experimental, and what is out of scope
- a feedback collection channel exists before invitations go out

Operational target for the first beta wave:

- at least 3 external testers
- at least 80 percent complete the first-run path without maintainer intervention
- setup blockers and unclear docs are tracked as explicit issues

### 6.7 Feedback Collection And Triage

Feedback collection should be lightweight but structured.

Each tester report should capture:

- operating system
- Python version
- runner used: `fake` or `ollama`
- model name if Ollama was used
- whether they used Streamlit, CLI, or both
- the task they attempted
- whether the first-run path succeeded
- the most confusing step
- the most valuable part of the experience

Triage buckets for incoming feedback:

- setup friction
- model compatibility
- workflow quality
- tool correctness
- UI clarity
- documentation gaps

Expected response loop:

- log every tester issue in one visible place
- fix onboarding blockers before expanding the tester pool
- update docs after each beta round, not just code

### 6.8 Beta Packaging Decision

For the first beta, the project should commit to one packaging story:

- distribution model: repository plus local setup instructions
- shortest launcher: `bash scripts/start_beta.sh`
- primary launcher: Streamlit UI
- fallback launcher: CLI

Explicitly deferred until later:

- hosted demo deployments
- installers or native desktop packaging
- Docker as the only supported path
- multi-user or remotely hosted orchestration services

### 6.9 Installer-Based Beta Expansion

If the target tester changes from a technical evaluator to a true non-technical user, the current beta gate is no longer sufficient. A separate installer-based beta milestone is required.

Required product shift:

- the tester should receive an installer or app bundle instead of a repository setup guide
- the tester should be able to launch the product without opening a terminal
- the first-run path should start in a beginner-safe guided UI with built-in sample tasks
- runtime artifacts such as logs or cached data should live in ordinary user-writable app locations

Required deliverables before that installer beta:

- one stable desktop-oriented launcher entrypoint inside the Python project
- one chosen first operating system for packaged distribution: `macOS`
- one bundling path such as PyInstaller, Briefcase, or an equivalent native-packaging workflow
- one documented first-launch behavior covering browser opening or embedded webview behavior
- one support statement for where logs, runs, and failure details are stored on the tester machine

Exit criteria for installer beta:

- a tester can install and launch the app without cloning the repo
- a tester can reach the guided starter-task screen without maintainer help
- the packaged build includes all UI/runtime dependencies needed for the supported first-run path
- the app fails with visible, plain-language guidance when the local model path is unavailable

Initial scope recommendation:

- keep `macOS` as the first installer-preview target instead of broadening immediately
- keep the fake-runner path as the packaged first-run success path
- treat Ollama support as a later follow-up even inside the installer beta

## 7. Stabilization Backlog

The stabilization backlog should remain subordinate to the three milestone themes above.

- keep `README.md`, `ROADMAP.md`, and `docs/quickstart.md` aligned with the actual CLI and runtime behavior
- expand regression tests when workflow routing or persistence surfaces change
- preserve schema compatibility for persisted artifacts unless there is a clear migration story
- keep fake-runner coverage strong so local regression checks stay fast and deterministic
- keep the repo-based beta path and the future installer-based path clearly distinguished in docs and support promises

## 8. Current File Layout

```text
.
├── .github/
│   └── ISSUE_TEMPLATE/
│       └── beta_feedback.md
├── app.py
├── desktop_launcher.py
├── main.py
├── scripts/
│   ├── build_macos_app.sh
│   └── start_beta.sh
├── docs/
│   ├── architecture.md
│   ├── beta_quickstart.md
│   ├── beta_support_matrix.md
│   ├── beta_task_pack.md
│   ├── known_issues.md
│   ├── macos_packaging.md
│   ├── project_status.json
│   ├── quickstart.md
│   └── sample_data/
│       ├── quarterly_metrics.csv
│       ├── quarterly_metrics.json
│       └── quarterly_metrics_baseline.csv
├── models/
│   ├── cached_runner.py
│   ├── fake_runner.py
│   ├── model_runner.py
│   ├── ollama_client.py
│   ├── ollama_runner.py
│   └── prompt_manager.py
├── orchestrator/
│   ├── acceptance.py
│   ├── acceptance_runs.py
│   ├── bootstrap.py
│   ├── cache.py
│   ├── inspection.py
│   ├── planner.py
│   ├── project_status.py
│   ├── runtime_paths.py
│   ├── router.py
│   ├── runs.py
│   ├── supervisor.py
│   └── task_manager.py
├── schemas/
│   ├── acceptance_schema.py
│   ├── audit_schema.py
│   ├── cache_schema.py
│   ├── result_schema.py
│   ├── task_schema.py
│   ├── tool_schema.py
│   └── worker_schema.py
├── tests/
│   ├── __init__.py
│   ├── test_acceptance.py
│   ├── test_acceptance_query.py
│   ├── test_audit_logging.py
│   ├── test_cache.py
│   ├── test_cache_query.py
│   ├── test_cli.py
│   ├── test_desktop_launcher.py
│   ├── test_exit_codes.py
│   ├── test_inspection.py
│   ├── test_ollama_runner.py
│   ├── test_project_status.py
│   ├── test_run_query.py
│   ├── test_review_workflow.py
│   ├── test_runtime_paths.py
│   ├── test_supervisor.py
│   ├── test_task_planner.py
│   └── test_tool_manager.py
├── tools/
│   ├── acceptance.py
│   ├── audit.py
│   ├── cache.py
│   ├── csv_analysis_tool.py
│   ├── data_computation_tool.py
│   ├── errors.py
│   ├── http_fetch_tool.py
│   ├── json_analysis_tool.py
│   ├── local_file_tool.py
│   ├── registry.py
│   └── retry.py
└── workers/
    ├── analysis_worker.py
    ├── base.py
    ├── comparison_worker.py
    ├── research_worker.py
    ├── review_worker.py
    └── writer_worker.py
```

## 9. Long-Term Directions

These are still valid ideas, but they should remain out of the near-term milestone unless the project explicitly decides to broaden scope.

### 9.1 Parallel And Multi-Agent Execution

- asynchronous or DAG-based scheduling
- fan-out and fan-in orchestration patterns
- result aggregation and conflict resolution between branches

### 9.2 Human-In-The-Loop Workflows

- approval checkpoints before expensive or risky steps
- progress streaming, pause, and cancel controls
- mid-run feedback that can alter execution strategy

### 9.3 Broader Tool Families

- database access
- notebook generation or execution
- richer code and IDE automation
- broader external API integrations

### 9.4 Richer Result Presentation

- HTML or dashboard output
- notebook-friendly artifacts
- richer report packaging beyond the current markdown path

### 9.5 Multi-Provider And Enterprise Surfaces

- model routing across providers beyond Ollama
- richer metrics and tracing
- more advanced compliance or enterprise audit layers

### 9.6 Extensibility

- plugin-style worker or tool registration
- third-party extension contracts
- curated prompt or worker libraries

## 10. Capability Snapshot

| Capability | Current Baseline | Next Milestone | Long Term |
| --- | --- | --- | --- |
| Bounded workflow routing | yes | expand templates carefully | keep bounded unless explicitly redesigned |
| Tool integration | yes, local-first | broaden within local-first constraints | broader tool families |
| Ollama support | yes | harden compatibility | multi-provider routing |
| Audit and acceptance persistence | yes | improve summaries and comparison quality | richer observability |
| Request cache and model retry | yes | maintain and document | more advanced invalidation only if needed |
| Parallel execution | no | not in scope | yes |
| Human-in-the-loop checkpoints | no | not in scope | yes |
| Plugin or marketplace model | no | not in scope | possible |

That sequencing matters. The orchestrator should stay useful, testable, and understandable at each step instead of becoming a generic platform before the current baseline is truly stable.
