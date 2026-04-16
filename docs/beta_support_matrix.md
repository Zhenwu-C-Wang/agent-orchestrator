# Beta Support Matrix

This matrix defines the current support promise for the first external beta wave. It is intentionally narrower than the full feature set in the repository.

## Summary

| Area | Current Beta Position |
| --- | --- |
| Audience | Technical users running the repo locally |
| Primary entrypoint | `streamlit run app.py` |
| Secondary entrypoint | `python main.py "..."` |
| Supported runner for first success path | `fake` |
| Optional runner for follow-up evaluation | `ollama` |
| Supported operating systems | macOS, Linux |
| Required Python version | 3.11+ |
| Hosted deployment support | not in scope |

## Entry Surface Matrix

| Surface | Status | Notes |
| --- | --- | --- |
| Streamlit UI | supported | Recommended first-run path for beta testers |
| CLI | supported | Good for validation, automation, and troubleshooting |
| Hosted demo | not supported | Not part of the first beta wave |
| Desktop installer | not supported | Deferred |

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
- the sample CSV task is the recommended first data task
- the Ollama path is best-effort and secondary
- unsupported environments should fail with clear guidance rather than silent ambiguity
