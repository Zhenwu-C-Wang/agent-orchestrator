# ROADMAP: Practical V1 for a Supervisor / Worker Orchestrator

This repository now targets a **practical, immediately usable V1** rather than a demo-only MVP. The goal is to ship a runnable local-first orchestration framework that can already handle real tasks through role-based workers, a small integrated toolchain, and structured outputs, while still keeping the first release disciplined enough to build and verify.

## 1. V1 Product Decision

### Problem We Are Solving

Build a supervisor-driven orchestration framework that can take one user request, understand the task type, delegate work to focused workers, optionally use integrated tools, and return one final answer with structured intermediate output that is already useful in day-to-day work.

### In Scope

- Python implementation
- A local-first supervisor / worker architecture that can be run from the CLI immediately after setup
- A small but usable worker catalog: `ResearchWorker`, `WriterWorker`, `ReviewWorker`, and one analysis-oriented worker path
- One `Supervisor`
- One `TaskRouter` with limited dynamic routing between predefined workflow templates
- One `TaskPlanner` or equivalent planning layer for task classification and workflow selection
- One structured `ModelRunner` interface
- One local-model adapter for Ollama
- One deterministic fake runner for tests and demos
- One pluggable `ToolManager`
- A minimal integrated toolchain for practical use, including local file/context reading, external HTTP/API access through adapters, guarded Python/data analysis execution, and markdown/JSON result rendering
- One optional JSON audit logger for run persistence
- One read-only local run status query over audit artifacts
- One optional acceptance report logger for validation persistence
- One read-only acceptance report query over local JSON artifacts
- One acceptance report comparison path for regression checks
- One model-layer retry policy for Ollama calls and JSON parsing
- One optional request-level structured result cache
- One optional TTL-based cache expiry policy
- One local cache inspection and maintenance CLI
- One normalized CLI error taxonomy with stable exit codes
- CLI entrypoint for local execution

### Out Of Scope For This Version

- Fully open-ended agent swarms or unconstrained autonomous planning
- Arbitrary plugin ecosystems or third-party marketplaces
- Production-grade distributed scheduling
- Complex human approval graphs
- Rich real-time streaming UIs
- Durable storage beyond local JSON audit artifacts
- Broad enterprise compliance features
- Full multi-provider model routing in the initial release

The rule for this version is simple: if a feature does not make the framework more immediately useful or safer to operate in local real tasks, defer it to a later phase.

## 2. Locked Technical Choices

These choices are intentionally fixed so the framework can become usable quickly without reopening infrastructure decisions.

| Topic | Decision |
| --- | --- |
| Language | Python 3.11+ |
| Schema validation | `pydantic` |
| Local model provider | Ollama via HTTP API |
| Test runner | `pytest` |
| CLI entrypoint | `python main.py "question"` |
| Default demo runner | `fake` |
| Local model runner | `ollama` |

## 3. V1 Workflow Contract

### Workflow

1. User submits a request.
2. `Supervisor` asks `TaskPlanner` and `TaskRouter` for the workflow plan.
3. The system classifies the request into a bounded workflow template.
4. One or more workers execute the selected workflow, optionally invoking registered tools.
5. `WriterWorker` or an equivalent synthesis step assembles the final answer.
6. `ReviewWorker` may validate the result when enabled.
7. `Supervisor` returns the final answer plus task traces, tool usage, and execution metadata.

### Required Schemas

- `TaskEnvelope`
- `WorkflowPlan`
- `ToolInvocation`
- `ResearchTaskInput`
- `AnalysisTaskInput`
- `WriterTaskInput`
- `ResearchResult`
- `AnalysisResult`
- `FinalAnswer`
- `TaskTrace`
- `WorkflowResult`

### Required Runtime Components

- `Supervisor`
- `TaskPlanner`
- `TaskRouter`
- `TaskManager`
- `PromptManager`
- `ModelRunner` protocol
- `FakeModelRunner`
- `OllamaClient`
- `OllamaModelRunner`
- `ToolManager`
- `Tool` protocol
- `AuditLogger`
- `AuditStore`
- `RetryPolicy`
- `StructuredResultCache`
- `AgentOrchestratorError`
- `ResearchWorker`
- `AnalysisWorker`
- `WriterWorker`
- `ReviewWorker` behind a feature flag

## 4. Definition Of Done

The V1 is done only when all of the following are true:

- The command `python main.py "How should I bootstrap a supervisor-worker system?" --runner fake --output json` succeeds.
- The command `python main.py "Analyze this local dataset and summarize the findings" --runner ollama --output markdown` succeeds when the required tool path is available.
- The output contains a structured workflow plan, intermediate worker blocks, a structured `final_answer` block, and `traces`.
- `Supervisor` does not handcraft answers; it only coordinates the workflow.
- Each worker validates input and output against explicit schemas.
- The framework can choose among bounded workflow templates instead of relying on a single hard-coded path.
- A local Ollama runner exists behind the same `ModelRunner` interface.
- Tool usage is isolated behind a registry and explicit invocation records.
- At least one integrated tool path is usable end-to-end for practical work beyond pure text transformation.
- Audit logging can persist a run as one JSON artifact when requested.
- Local runs can be listed and inspected through a read-only audit query CLI.
- Acceptance runs can optionally persist one report artifact and query it later.
- Acceptance history can be compared against a baseline run for regression checks.
- The Ollama runner can retry model invocation or JSON parsing failures without replaying the whole workflow.
- Exact repeated requests can reuse cached structured results when cache is enabled.
- Cache TTL can expire older entries when configured.
- Cache hit, miss, or expiry status is visible in task-level trace metadata and audit artifacts.
- Local cache entries can be listed, pruned, or cleared through a dedicated CLI.
- CLI failures are classified into stable exit codes for automation.
- Automated tests cover routing, worker execution, tool invocation, and CLI JSON output.

## 5. Executable Work Breakdown

### M0: Project Bootstrap

Deliverables:

- `pyproject.toml`
- package directories and `__init__.py` files
- CLI entrypoint
- `README.md` install and run instructions

Acceptance:

- A new contributor can create a virtualenv, install dependencies, and run tests using only the README.

### M1: Core Orchestration

Deliverables:

- `Supervisor`
- `TaskPlanner`
- `TaskRouter`
- `TaskManager`
- `ResearchWorker`
- `AnalysisWorker`
- `WriterWorker`
- `ReviewWorker`
- schemas for task input, worker output, workflow plans, and traces

Acceptance:

- At least two bounded workflow templates run end-to-end with the fake runner.
- `WorkflowResult` includes both intermediate and final structured outputs.

### M2: Local Model And Tooling

Deliverables:

- `OllamaClient`
- `OllamaModelRunner`
- `ToolManager`
- one local context/file tool
- one guarded analysis or execution tool
- prompt templates for planner and workers
- optional JSON audit persistence
- read-only audit query CLI
- optional acceptance report persistence
- read-only acceptance report query CLI
- acceptance report comparison support
- model-layer retry policy
- request-level structured result cache
- TTL-based cache expiry and local cache management CLI
- normalized CLI exit codes

Acceptance:

- The same workflow can be executed with `--runner ollama --model <model-name>`.
- Local-model calls are isolated behind the `ModelRunner` contract.
- Tool calls are isolated behind the `ToolManager` contract.
- The framework can support at least one research-style request and one analysis-style request without code changes.
- Audit artifacts can be written without changing worker logic.
- Run inspection reads persisted artifacts instead of requiring a live process registry.
- Acceptance history is preserved separately from per-question workflow audit records.
- Acceptance regression checks compare report artifacts instead of replaying old runs.
- Retry logic is isolated to model execution and parse recovery.
- Cache reuse is isolated to exact request matches and does not affect workflow order.
- Cache expiry remains local, opt-in, and request-level.
- CLI automation can rely on stable exit codes instead of parsing free-form error text.

### M3: Usability Baseline

Deliverables:

- workflow unit tests
- tool integration tests
- CLI integration test
- JSON extraction/parser test for model output normalization
- architecture note
- quickstart usage scenarios

Acceptance:

- `pytest` passes locally.
- The repo contains one document that explains responsibility boundaries and one quickstart path for real usage.

## 6. Task List For Immediate Execution

These are the first engineering tasks to create as issues or work items.

1. Create the Python package and dependency manifest.
2. Define the core schemas in `schemas/`, including workflow plans and tool invocation records.
3. Implement the `ModelRunner` protocol and fake runner.
4. Implement the Ollama client and runner.
5. Implement the prompt manager and planner prompts.
6. Implement `ResearchWorker`, `AnalysisWorker`, `WriterWorker`, and the optional `ReviewWorker`.
7. Implement `TaskPlanner`, `TaskRouter`, `TaskManager`, and `Supervisor`.
8. Implement `ToolManager` and at least two practical tool adapters.
9. Add `main.py` and JSON/pretty/markdown output modes.
10. Add optional JSON audit logging.
11. Add read-only run status query over persisted audit artifacts.
12. Add optional acceptance report persistence and read-only acceptance query.
13. Add model-layer retries for Ollama execution and parse recovery.
14. Add request-level structured result caching.
15. Add TTL-based cache expiry and a local cache management CLI.
16. Add normalized CLI failure classification and exit codes.
17. Add tests for workflow routing, tool invocation, CLI, audit persistence, acceptance persistence, status query, retry behavior, caching, cache expiry, cache management, exit codes, and JSON extraction.
18. Add architecture and quickstart documentation for real usage scenarios.

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
│   ├── planner.py
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
│   ├── tool_schema.py
│   └── worker_schema.py
├── tools/
│   ├── __init__.py
│   ├── acceptance.py
│   ├── audit.py
│   ├── cache.py
│   ├── errors.py
│   ├── http_tool.py
│   ├── python_tool.py
│   ├── registry.py
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
│   ├── test_supervisor.py
│   ├── test_task_planner.py
│   └── test_tool_manager.py
├── workers/
│   ├── analysis_worker.py
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

Use at least these six questions to validate the fake or local runner workflow:

1. How should I bootstrap a supervisor-worker agent system?
2. What are the tradeoffs of fake runners versus local models in an MVP?
3. How should I define worker schemas before adding more workers?
4. What risks appear when a supervisor directly writes the final answer?
5. When should I add retry, cache, and audit layers to this system?
6. Analyze a local CSV file and summarize the most important changes.

The pass condition is not “the wording looks nice.” The pass condition is:

- no runtime crash
- valid schema output
- correct workflow order for the selected workflow template
- correct tool invocation records when a tool-backed task is requested
- final answer references the research summary instead of inventing a separate path

## 9. Next Milestone After This One

Only after the practical V1 above is stable should the project add:

- workflow-level retry policy
- advanced cache invalidation and eviction policy
- richer status/query APIs beyond audit-backed local inspection
- broader dynamic planning
- richer tool families such as databases, notebooks, and IDE automation
- parallel branches
- human-in-the-loop checkpoints

## 10. Future Vision: Multi-functional AI Systems Framework

After the practical V1 is proven stable, the long-term vision extends this orchestration layer into a comprehensive **multi-functional intelligent systems framework** capable of:

### 10.1 Dynamic Workflow Planning (P1)

**Goal:** Adapt workflow to question type and context instead of using a fixed pipeline.

**Components:**
- `DynamicTaskPlanner`: Analyzes user questions and generates adaptive workflow graphs
- `AdaptiveTaskRouter`: Extends `TaskRouter` to support dynamic routing
- `DecisionTree`: Maps question semantics to recommended worker chains
- `WorkflowGraph`: DAG-based task scheduling (sequential, parallel, conditional branches)

**Example Use Cases:**
- Technical questions → Research + Code Analysis + Testing
- Data questions → Research + Data Analysis + Visualization
- Multi-step tasks → Task decomposition + parallel execution + result synthesis

### 10.2 Integrated Tool Chain (P1)

**Goal:** Provide workers access to external tools and APIs dynamically.

**Components:**
- `ToolManager`: Registry and selector for available tools
- `WebScraperTool`: Extract and parse web content
- `DataAnalyzerTool`: Execute pandas/numpy analysis
- `CodeExecutorTool`: Run Python code in isolated environments
- `APICallerTool`: Invoke external services with authentication
- `DatabaseConnectorTool`: Query structured data stores
- `IDEIntegrationTool`: Automate VSCode/Jupyter operations
Workflow:

```python
class ToolManager:
    tools = {
        'web_scraper': WebScraperTool(),
        'data_analyzer': DataAnalyzerTool(),
        'code_executor': CodeExecutorTool(),
        'api_caller': APICallerTool(),
        'database': DatabaseConnectorTool(),
    }
    
    def select_tools(self, task_type: str) -> list[Tool]:
        """Route task requirements to available tools"""
        pass
```

**Benefits:**
- Workers can fetch real-time data
- Workers can execute custom analysis scripts
- Workers can integrate with external services (search, compute, databases)

### 10.3 Implicit NLP & Task Decomposition (P2)

**Goal:** Automatically understand user intent and decompose into sub-tasks.

**Components:**
- `SemanticAnalyzer`: Extract intent, entities, and task types from natural language
- `TaskDecomposer`: Break complex requests into atomic work items
- `ContextExtractor`: Build execution context from conversation history
- `LLMTaskPlanner`: Use an LLM to generate optimal task sequences

**Example:**
```
User: "Analyze sales data from Q1 2024 and compare with Q1 2023, then generate a PowerPoint report"

Decomposed Flow:
1. DataFetchWorker → Query Q1 2024 sales, Q1 2023 sales
2. DataAnalysisWorker → Compute YoY trends, changes, anomalies  
3. VisualizationWorker → Create comparison charts
4. ReportGeneratorWorker → Assemble PowerPoint with findings
```

### 10.4 Parallel & Multi-Agent Execution (P2)

**Goal:** Enable workers to execute concurrently and collaborate.

**Components:**
- `AsyncSupervisor`: Parallel task execution with dependency tracking
- `AgentCommunication`: Inter-worker message passing
- `ResultAggregator`: Combine outputs from parallel branches
- `ConflictResolver`: Reconcile divergent recommendations

**Execution Model:**
```python
# Sequential
Research → Writing → Review

# Fan-out / Fan-in (parallel research, then synthesis)
Research-v1 || Research-v2 || Research-v3 → SynthesisWorker → Review

# Conditional branching
Classifier → {TechnicialPath, AnalyticsPath, CreativePath} → Review
```

### 10.5 Interactive Feedback & Human-in-the-Loop (P3)

**Goal:** Allow user intervention during task execution.

**Components:**
- `UserApprovalNode`: Checkpoint for human decision
- `ProgressRenderer`: Real-time task status display
- `FeedbackCollector`: Capture mid-execution corrections
- `AdaptiveRetry`: Adjust strategy based on user feedback

**Scenarios:**
- Pause execution for review before synthesis step
- Request user confirmation on tool selections
- Real-time progress streaming with cancel capability

### 10.6 Rich Result Presentation (P3)

**Goal:** Flexible output formats beyond structured JSON.

**Components:**
- `ResultFormatter`: Render results as markdown, HTML, PDF, interactive dashboards
- `VisualizationEngine`: Auto-generate charts, tables, comparisons
- `ReportGenerator`: Assemble findings into formatted documents
- `StreamingRenderer`: Real-time output as tasks complete

**Output Types:**
- Markdown reports with embedded analysis
- Interactive HTML dashboards with drill-down
- PDF executive summaries
- Jupyter notebooks with executable cells
- Video/animation synthesis for complex processes

### 10.7 IDE & Development Environment Integration (P3)

**Goal:** Seamless automation of coding and development workflows.

**Components:**
- `VSCodeAutomation`: Create projects, write code, run tests
- `JupyterNotebookWorker`: Data exploration and visualization
- `GitIntegration`: Commit, branching, pull request automation
- `TestGeneratorWorker`: Auto-generate test cases

**Capabilities:**
- Scaffold full projects with one question
- Auto-generate boilerplate code
- Run tests and report coverage immediately
- Suggest refactoring or performance improvements

### 10.8 Observability & Enterprise Features (P4)

**Goal:** Production-grade monitoring and compliance.

**Components:**
- `DistributedTracing`: OpenTelemetry integration
- `CostAnalyzer`: Track API calls and compute usage
- `ComplianceLogger`: Audit trail for regulated workloads
- `PerformanceProfiler`: Latency and resource metrics per step
- `MetricsExporter`: Prometheus/Grafana integration

### 10.9 Multi-Model & Multi-Provider Support (P4)

**Goal:** Run the same workflow across different LLM providers.

**Components:**
- `ModelRouter`: Select best model for task type and budget
- `OpenAIAdapter`, `AnthropicAdapter`, `HuggingFaceAdapter`
- `ProviderAggregator`: Compare outputs across providers
- `LatencyCostOptimizer`: Choose provider based on SLA and budget

### 10.10 Extensibility Framework (P4)

**Goal:** Allow third-party workers and tool plugins.

**Components:**
- `WorkerRegistry`: Plugin discovery and validation
- `ToolPlugin`: Standard interface for custom tools
- `PromptTemplate`: Community prompt library
- `WorkerMarketplace`: Share proven worker implementations

---

## 11. Implementation Phases

| Phase | Timeline | Focus | Goal |
|-------|----------|-------|------|
| **Phase 1 (Practical V1)** | 1-2 months | Bounded dynamic routing, local models, core toolchain, observability | Deliver immediate usability |
| **Phase 2 (Dynamic)** | 2-3 months | Richer adaptive routing, dynamic tools, NLP decomposition | Support diverse use cases |
| **Phase 3 (Parallel)** | 3-4 months | Concurrent execution, multi-agent collaboration, interactive feedback | Scale to complex workflows |
| **Phase 4 (Enterprise)** | 4+ months | Enterprise features, IDE integration, multi-provider support | Production deployments |

---

## 12. Capability Matrix

| Capability | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Notes |
|-----------|-----|--------|--------|---------|-------|
| Fixed workflows | ✅ | ✅ | ✅ | ✅ | Foundation |
| Bounded workflow routing | ✅ | ✅ | ✅ | ✅ | V1 usability requirement |
| Local model support | ✅ | ✅ | ✅ | ✅ | Via Ollama |
| Structured output | ✅ | ✅ | ✅ | ✅ | Pydantic schemas |
| Audit logging | ✅ | ✅ | ✅ | ✅ | JSON artifacts |
| **Dynamic workflows** | ⏳ | ✅ | ✅ | ✅ | Starts bounded in V1 |
| **Tool integration** | ✅ | ✅ | ✅ | ✅ | Local-first in V1, broader later |
| **Parallel execution** | ❌ | ⏳ | ✅ | ✅ | Async supervisor |
| **NLP decomposition** | ⏳ | ⏳ | ✅ | ✅ | Starts as bounded classification |
| **Human-in-loop** | ❌ | ❌ | ✅ | ✅ | Interactive checkpoints |
| **Rich formatting** | ❌ | ❌ | ✅ | ✅ | HTML, PDF, notebooks |
| **IDE automation** | ❌ | ❌ | ⏳ | ✅ | VSCode, Jupyter |
| **Multi-provider** | ❌ | ❌ | ❌ | ✅ | OpenAI, Anthropic, etc. |
| **Observability** | ✅ | ✅ | ✅ | ✅ | Grows with phases |
| **Plugins/Marketplace** | ❌ | ❌ | ❌ | ✅ | Community extensibility |

That sequence matters because the framework needs to be useful on day one without collapsing into an unbounded platform build.
