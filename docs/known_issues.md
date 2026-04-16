# Known Issues And Beta Support Scope

This document tracks the current support boundary for external testers. It is intentionally conservative.
For the explicit beta support promise, see [beta_support_matrix.md](./beta_support_matrix.md).

## Current Beta Support Scope

The first beta wave is currently aimed at:

- macOS and Linux users
- Python 3.11+
- local execution from a cloned repository
- Streamlit as the primary entrypoint
- CLI as a secondary validation surface

At this stage, the project does not promise:

- hosted access
- Windows-first support
- production uptime or hardened data guarantees
- broad local-model compatibility across arbitrary Ollama models

## Common Setup Issues

### `streamlit: command not found`

Cause:
- the UI dependencies are not installed

Try:

```bash
pip install -e '.[ui]'
```

### `pytest: command not found`

Cause:
- the dev dependencies are not installed

Try:

```bash
pip install -e '.[dev]'
```

### The UI launches but imports fail immediately

Cause:
- the environment was created but dependencies were not installed into the active virtualenv

Try:

```bash
source .venv/bin/activate
pip install -e '.[ui]'
```

## Common Ollama Issues

### Connection errors to `http://localhost:11434`

Cause:
- Ollama is not running locally
- the base URL is incorrect

What to do:

- start Ollama locally before choosing the `ollama` runner
- verify the base URL in the CLI flag or Streamlit sidebar
- if you are only testing onboarding, switch back to the `fake` runner first

### The selected model is missing locally

Cause:
- the model name is valid for your workflow settings but has not been pulled into your local Ollama installation

What to do:

- use a model you already have locally
- start with one of the example names used in this repo, such as `llama3.1` or `qwen2.5:14b`
- expect the Ollama path to be narrower and more experimental than the fake-runner path

### The Ollama path runs but structured output quality is inconsistent

Cause:
- local models vary in how reliably they follow structured JSON constraints

What to do:

- retry with the same model before changing prompts
- increase `--max-retries` modestly if needed
- capture the model name and exact task in your feedback

## Common Workflow Issues

### The wrong workflow seems to be selected

What to know:

- research-style tasks typically route to `research_then_write`
- analysis-style tasks, attached files, or attached URLs typically route to `analysis_then_write`
- direct comparison across multiple attached contexts typically routes to `comparison_then_write`
- advisory requests over attached context may broaden into `research_then_analysis_then_write` or `research_then_comparison_then_write`
- inline file and URL discovery are disabled by default unless you explicitly opt in

What to do:

- check the plan preview in Streamlit before running
- if using the CLI, rerun with `--output json` and inspect `workflow_plan`
- include the exact task text in your feedback if routing looks wrong

### A URL-based analysis task shows failed tool invocations

Cause:
- the remote URL may be unavailable
- the server may reject the request
- local network policy may block access

What to do:

- confirm the URL is reachable from your machine
- treat URL-backed analysis as more fragile than local file analysis in this beta
- prefer the sample CSV path for first-run evaluation

### Uploaded files in Streamlit do not preserve the original path

What to know:

- the UI copies uploaded files into a temporary directory before running the workflow
- this is expected behavior for the current local UI

What to do:

- judge success by whether the workflow detects and analyzes the uploaded content, not by the original absolute path

## Feedback Expectations

When reporting a problem, please include:

- operating system
- Python version
- runner used
- model name if applicable
- whether you used Streamlit, CLI, or both
- the exact task you attempted
- what you expected
- what actually happened

If you are filing an issue in GitHub, use the beta feedback template when possible.
