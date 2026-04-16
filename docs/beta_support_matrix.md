# Beta Support Matrix

This matrix defines the current support promise for the first external beta wave. It is intentionally narrower than the full feature set in the repository.
It describes the current repo-based beta, not a native desktop-installer release for non-technical end users.

## Summary

| Area | Current Beta Position |
| --- | --- |
| Audience | Technical users running the repo locally |
| Simplest launcher | `bash scripts/start_beta.sh` |
| Primary entrypoint | `streamlit run app.py` |
| Packaging-friendly UI entrypoint | `agent-orchestrator-ui` |
| Secondary entrypoint | `python main.py "..."` |
| Default UI mode | Guided mode with built-in starter tasks |
| Supported runner for first success path | `fake` |
| Optional runner for follow-up evaluation | `ollama` |
| Supported operating systems | macOS, Linux |
| Required Python version | 3.11+ |
| Hosted deployment support | not in scope |
| Native installer support | not shipped yet |
| Installer preview target | macOS |

## Entry Surface Matrix

| Surface | Status | Notes |
| --- | --- | --- |
| `scripts/start_beta.sh` | supported | Recommended shortest path for first-wave testers |
| Streamlit UI | supported | Recommended first-run path for beta testers, with Guided mode and built-in starter tasks |
| `agent-orchestrator-ui` | supported for local installed Python environments | Stable launcher target for future desktop packaging work |
| CLI | supported | Good for validation, automation, and troubleshooting |
| Hosted demo | not supported | Not part of the first beta wave |
| Desktop installer | not supported yet | Packaging groundwork is in progress, but no native installer is shipped today |

## Installer Preview Direction

Installer work is now intentionally targeting `macOS` first. That does not mean a native end-user installer is ready today. It means packaging validation should stay narrow until the first app-bundle path is proven on a second machine.

## Runner Matrix

| Runner | Status | Recommended Use |
| --- | --- | --- |
| `fake` | supported | First-run smoke test, onboarding, deterministic workflow validation |
| `ollama` | limited beta support | Follow-up evaluation after the fake-runner path succeeds |

## Workflow Matrix

| Workflow | Status | Typical Trigger |
| --- | --- | --- |
| `research_then_write` | supported | General knowledge or architecture questions |
| `analysis_then_write` | supported | Single attached dataset or URL summary |
| `research_then_analysis_then_write` | supported | Advisory request over attached data |
| `comparison_then_write` | supported | Direct comparison across multiple attached contexts |
| `research_then_comparison_then_write` | supported | Advisory comparison or prioritization across multiple attached contexts |

## Context Input Matrix

| Input Path | Status | Notes |
| --- | --- | --- |
| `--context-file` / Streamlit file upload | supported | Recommended first beta path |
| `--context-url` / Streamlit URL input | supported with caveats | More fragile than local files because remote availability can fail |
| Inline file discovery in prompt text | opt-in | Requires `--allow-inline-context-files` |
| Inline URL discovery in prompt text | opt-in | Requires `--allow-inline-context-urls` |

## Tool Matrix

| Tool | Status | Notes |
| --- | --- | --- |
| `local_file_context` | supported | Core local-file grounding path |
| `csv_analysis` | supported | Recommended first data-analysis path |
| `json_analysis` | supported | Useful for explicit JSON snapshots |
| `data_computation` | supported | Bounded numeric delta and aggregate computation |
| `http_fetch` | supported with caveats | Depends on URL reachability and local network policy |

## Ollama Guidance

The Ollama path is still a narrower beta surface than the fake runner. Use it only after the primary onboarding path succeeds.

### Documented starter models

These are the model names already referenced throughout this repo and docs:

- `llama3.1`
- `qwen2.5:14b`

Current status:

- documented for beta use
- appropriate as first-pass evaluation targets
- still subject to model-specific variance in structured output quality

This is not yet a guarantee that every local Ollama setup will behave identically across those models.

### Hardware expectation

The fake-runner path has minimal local requirements beyond Python and the project dependencies.

For the Ollama path:

- use a model size that your local machine already runs comfortably in Ollama
- expect larger models to need materially more RAM and patience during local evaluation
- treat performance and output consistency as best-effort unless a model has been explicitly validated in your environment

## Recommended First Beta Promise

For the first wave, the support promise should remain:

- the fake-runner path is expected to work on supported systems
- the Streamlit UI is the recommended entrypoint
- the repo still assumes Python is installed locally; true installer-based distribution is a later milestone
- the sample CSV task is the recommended first data task
- the Ollama path is best-effort and secondary
- unsupported environments should fail with clear guidance rather than silent ambiguity
