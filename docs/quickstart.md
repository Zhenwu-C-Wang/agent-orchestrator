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
python main.py "Analyze \`docs/sample_data/quarterly_metrics.csv\` and summarize the most important changes." \
  --runner fake \
  --output markdown
```

What to look for:

- workflow selection should be `analysis_then_write`
- `tool_invocations` should include `local_file_context` and `csv_analysis`
- the analysis summary should mention the referenced CSV

## 3. Persist And Inspect A Run

Write audit output while running a workflow:

```bash
python main.py "Analyze \`docs/sample_data/quarterly_metrics.csv\` and summarize the most important changes." \
  --runner fake \
  --audit-dir artifacts/runs \
  --output json
```

Then inspect the saved record:

```bash
python -m orchestrator.runs --audit-dir artifacts/runs list
python -m orchestrator.runs --audit-dir artifacts/runs latest --output json
```

## 4. Run The Acceptance Dataset

Run the full acceptance suite locally:

```bash
python -m orchestrator.acceptance --runner fake
```

The current dataset includes:

- research-style orchestration cases
- review coverage when `--with-review` is enabled
- one tool-backed CSV analysis case

Persist a report if you want later comparison:

```bash
python -m orchestrator.acceptance --runner fake --report-dir artifacts/acceptance
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance compare
```

## 5. Use The Streamlit Console

Launch the local UI:

```bash
streamlit run app.py
```

The UI is useful when you want to:

- type questions interactively
- preview the selected workflow plan before execution
- inspect tool invocations and traces after execution
- export JSON, Markdown, or text summaries
- review recent persisted runs if an audit directory is configured
