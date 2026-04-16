# Beta Task Pack

This task pack gives external testers a consistent set of prompts to try before they move into free-form exploration. It is designed to exercise the main bounded workflow families without asking testers to invent their own evaluation rubric.

## How To Use This Pack

- start with the Streamlit UI unless you are explicitly validating the CLI
- use the `fake` runner first
- treat the Ollama path as optional follow-up validation
- record both the workflow selected and any visible tool invocations

## Task 1: Research Baseline

Prompt:

```text
How should I bootstrap a supervisor-worker agent system?
```

Expected workflow:

- `research_then_write`

What testers should check:

- the plan is easy to understand before execution
- the final answer is readable without opening raw JSON
- traces make it clear which worker ran

## Task 2: CSV Analysis Baseline

Context:

- `docs/sample_data/quarterly_metrics.csv`

Prompt:

```text
Summarize the most important changes in this data.
```

Expected workflow:

- `analysis_then_write`

Expected tools:

- `local_file_context`
- `csv_analysis`
- `data_computation`

What testers should check:

- the final answer references the dataset rather than hallucinating unrelated content
- tool usage is understandable
- the analysis feels grounded in the attached file

## Task 3: JSON Analysis Baseline

Context:

- `docs/sample_data/quarterly_metrics.json`

Prompt:

```text
Summarize the most important changes in this JSON snapshot.
```

Expected workflow:

- `analysis_then_write`

Expected tools:

- `local_file_context`
- `json_analysis`
- `data_computation`

What testers should check:

- the system handles explicit JSON input cleanly
- JSON-specific tooling is visible in the run output
- the final answer remains readable to a human

## Task 4: Multi-Context Comparison

Context:

- `docs/sample_data/quarterly_metrics.csv`
- `docs/sample_data/quarterly_metrics_baseline.csv`

Prompt:

```text
Compare these datasets and summarize the most important differences.
```

Expected workflow:

- `comparison_then_write`

Expected tools:

- `local_file_context`
- `csv_analysis`
- `data_computation`

What testers should check:

- it is obvious that the system compared two contexts rather than summarizing one
- the workflow path is understandable from the UI or JSON output
- the comparison output feels grounded in both inputs

## Task 5: Advisory Data Workflow

Context:

- `docs/sample_data/quarterly_metrics.csv`

Prompt:

```text
Analyze this dataset and recommend what we should prioritize next.
```

Expected workflow:

- `research_then_analysis_then_write`

What testers should check:

- the result combines reasoning plus data-backed analysis
- the broader advisory route is understandable
- the output feels more decision-oriented than a plain summary

## Task 6: Advisory Comparison Workflow

Context:

- `docs/sample_data/quarterly_metrics.csv`
- `docs/sample_data/quarterly_metrics_baseline.csv`

Prompt:

```text
Compare these datasets and recommend which one we should prioritize next.
```

Expected workflow:

- `research_then_comparison_then_write`

What testers should check:

- the recommendation feels grounded in the comparison
- the workflow path is understandable
- the system does not hide the fact that multiple steps were involved

## Optional Task 7: Ollama Follow-Up

After at least one successful fake-runner task, rerun any one task above with:

- `Runner = ollama` in Streamlit, or
- `--runner ollama --model <model-name>` in the CLI

Suggested starter models:

- `llama3.1`
- `qwen2.5:14b`

What testers should check:

- whether the workflow still completes end to end
- whether the output remains structured and readable
- whether failures are clear when the local model path misbehaves

## Feedback Prompts For Testers

After the task pack, ask each tester:

- Which task felt strongest?
- Which task felt most confusing?
- Was the selected workflow understandable before and after execution?
- Did tool usage feel helpful or distracting?
- Did the UI or CLI make it obvious what to try next?

If collecting feedback through GitHub, pair this task pack with `.github/ISSUE_TEMPLATE/beta_feedback.md`.
