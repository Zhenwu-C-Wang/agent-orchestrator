# Beta Quickstart

This guide is the recommended first-run path for external testers. It is intentionally narrow: one setup path, one primary UI surface, and one small task script.

## Who This Is For

The current beta path is designed for:

- technical users who can run a Python project locally
- macOS or Linux users
- testers who can use a terminal and a local browser

The current beta path is not yet optimized for:

- non-technical users
- hosted or multi-user evaluation
- unsupported operating systems or custom deployment environments

## What You Need

- Python 3.11+
- a terminal
- a browser for the Streamlit UI
- optional: Ollama installed locally if you want to try the local-model path

## Reference Docs

- [beta_support_matrix.md](./beta_support_matrix.md) for the current support promise and runner matrix
- [beta_task_pack.md](./beta_task_pack.md) for the standard prompts and expected workflows
- [known_issues.md](./known_issues.md) for troubleshooting and current caveats

## 1. Install

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the primary beta surface and its dependencies:

```bash
pip install -e '.[ui]'
```

If you plan to run tests locally as part of evaluation, also install the dev dependencies:

```bash
pip install -e '.[dev]'
```

## 2. Launch The Recommended Entry Point

Start the Streamlit UI:

```bash
streamlit run app.py
```

When the page opens:

- keep `Runner` set to `fake`
- leave `Enable review stage` off for the first run
- keep the default audit directory unless you specifically want to disable persisted history

Why start here:

- it is the fastest way to see the selected workflow
- it exposes traces and tool invocations without extra commands
- it avoids requiring Ollama for the first successful run

## 3. Complete The First Research Task

Use the default question or paste this into `Task Input`:

```text
How should I bootstrap a supervisor-worker agent system?
```

Click `Run Workflow`.

Success looks like this:

- the plan preview shows `research_then_write`
- the run finishes without manual intervention
- the page shows a final answer plus traces
- `Tool Invocations` reports that no tools were needed for this task

## 4. Complete The First Analysis Task

In the sidebar, use `Attach context files` and upload:

```text
docs/sample_data/quarterly_metrics.csv
```

Then use this task:

```text
Summarize the most important changes in this data.
```

Click `Run Workflow` again.

Success looks like this:

- the plan preview switches to `analysis_then_write`
- the run shows an analysis block before the final answer
- `Tool Invocations` includes `local_file_context` and `csv_analysis`
- the final output references the uploaded dataset

## 5. Optional Ollama Follow-Up

Only do this after the fake-runner path succeeds.

In the sidebar:

- switch `Runner` to `ollama`
- make sure your Ollama server is running at the configured base URL
- start with one of the example model names already used in this repo, such as `llama3.1` or `qwen2.5:14b`

Then rerun either the research task or the CSV analysis task.

What to watch for:

- whether the workflow still completes end to end
- whether the final answer remains structured and readable
- whether retries or parse failures surface clearly in the UI or CLI

The Ollama path is still a narrower, best-effort beta surface than the fake runner. Treat the fake runner as the baseline onboarding path.
If you want a more structured evaluation order, use [beta_task_pack.md](./beta_task_pack.md).

## 6. Optional CLI Validation

If you want to confirm the same workflow outside the UI, run:

```bash
python main.py "How should I bootstrap a supervisor-worker system?" --runner fake --output json
```

For the sample CSV analysis path:

```bash
python main.py "Summarize the most important changes in this data." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --output json
```

## 7. What To Report Back

Please report:

- your operating system
- your Python version
- whether you used Streamlit, CLI, or both
- whether the first-run path succeeded without maintainer help
- the most confusing step
- the most useful part of the experience
- whether you tried Ollama, and if so which model

If you are filing feedback in GitHub, use the beta feedback template in `.github/ISSUE_TEMPLATE/beta_feedback.md`.

## 8. If You Get Stuck

See [known_issues.md](./known_issues.md) for the current support scope and common failure modes.
