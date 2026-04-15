# Quickstart Scenarios

This document shows the fastest ways to exercise the current framework end to end.

## 1. Research Workflow From The CLI

Use the fake runner for a deterministic knowledge-style request:

```bash
python main.py "How should I bootstrap a supervisor-worker agent system?" \
  --runner fake \
  --output pretty
```

Useful variants:

- `--output json` for the full structured workflow result
- `--output markdown` for a report-style artifact
- `--with-review` to append the optional validation step

## 2. Tool-Backed Analysis Workflow

Run the built-in CSV sample through the analysis path:

```bash
python main.py "Analyze this dataset and summarize the most important changes." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --output markdown
```

What to look for:

- workflow selection should be `analysis_then_write`
- `tool_invocations` should include `local_file_context` and `csv_analysis`
- `tool_invocations` should also include `data_computation`
- the analysis summary should mention the attached CSV

The same explicit-context path also works for JSON snapshots:

```bash
python main.py "Summarize the most important changes in this JSON snapshot." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.json \
  --output json
```

What to look for in the JSON run:

- `tool_invocations` should include `local_file_context`, `json_analysis`, and `data_computation`
- the analysis summary should mention computed dataset metrics

Inline file-path and URL discovery is disabled by default. If you want to opt back in, use:

```bash
python main.py "Analyze \`docs/sample_data/quarterly_metrics.csv\` and summarize the most important changes." \
  --runner fake \
  --allow-inline-context-files
```

## 3. Hybrid Advisory Workflow

Use explicit structured context together with an advisory question when you want the planner to combine prior reasoning and tool-backed analysis:

```bash
python main.py "Analyze this dataset and recommend what we should prioritize next." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --output json
```

What to look for:

- workflow selection should be `research_then_analysis_then_write`
- traces should run in the order `research`, `analysis`, `writer`
- `tool_invocations` should still include `local_file_context`, `csv_analysis`, and `data_computation`
- the JSON result should contain both `research` and `analysis` blocks before the final answer

## 4. URL-Backed Analysis Workflow

Attach one or more URLs explicitly when you want the analysis path to ground itself in fetched page content:

```bash
python main.py "Summarize the most important findings from this webpage." \
  --runner fake \
  --context-url https://example.com/report \
  --output markdown
```

What to look for:

- workflow selection should be `analysis_then_write`
- `tool_invocations` should include `http_fetch`
- the analysis summary should mention the fetched URL context

The Streamlit sidebar exposes the same capability through a multiline URL input.

## 5. Comparison Workflow

Use two explicit contexts when you want the planner to compare datasets instead of only summarizing one:

```bash
python main.py "Compare these datasets and summarize the most important differences." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --context-file docs/sample_data/quarterly_metrics_baseline.csv \
  --output json
```

What to look for:

- workflow selection should be `comparison_then_write`
- traces should run in the order `comparison`, `writer`
- `tool_invocations` should still include `local_file_context`, `csv_analysis`, and `data_computation`
- the JSON result should contain a `comparison` block

If you ask which dataset you should prioritize next, the planner should broaden that to `research_then_comparison_then_write`.

## 6. Persist And Inspect A Run

Write audit output while running a workflow:

```bash
python main.py "Analyze this dataset and summarize the most important changes." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --audit-dir artifacts/runs \
  --output json
```

Then inspect the saved record:

```bash
python -m orchestrator.runs --audit-dir artifacts/runs list
python -m orchestrator.runs --audit-dir artifacts/runs latest --output json
```

## 7. Run The Acceptance Dataset

Run the full acceptance suite locally:

```bash
python -m orchestrator.acceptance --runner fake
```

The current 10-case dataset includes:

- research-style orchestration cases
- review coverage when `--with-review` is enabled
- one tool-backed CSV analysis case
- one tool-backed JSON analysis case
- one hybrid advisory-plus-context case
- one comparison case over paired datasets
- one hybrid comparison case over paired datasets

Persist a report if you want later comparison:

```bash
python -m orchestrator.acceptance --runner fake --report-dir artifacts/acceptance
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance compare
```

## 8. Use The Streamlit Console

Launch the local UI:

```bash
streamlit run app.py
```

The UI is useful when you want to:

- type questions interactively
- preview the selected workflow plan before execution, including route warnings and guidance
- inspect overview, intermediates, tools, traces, and exports in separate guided tabs after execution
- export JSON, Markdown, or text summaries
- review recent persisted runs with the same inspection summary if an audit directory is configured
- inspect persisted acceptance reports and local cache health from the same console when those directories are configured
- drill into one acceptance case or one cache entry when you need to inspect regressions, traces, tool usage, metadata, or response previews
