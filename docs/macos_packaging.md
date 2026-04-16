# macOS Packaging Preview

This document defines the first installer-oriented packaging target for the project. It is intentionally narrower than the repo-based beta path.

## Current Decision

- first installer target: `macOS`
- first-run success path inside the packaged app: `fake` runner
- current UI surface inside the packaged app: the guided Streamlit UI launched through `desktop_launcher.py`
- local-model support inside packaged builds: deferred until after the fake-runner path feels solid

## Why macOS First

- it matches the maintainer's current development environment
- it keeps the packaging path narrow while the installer story is still forming
- it lets us validate one native app-bundle workflow before committing to broader platform support

## What Exists Today

- a packaging-friendly launcher entrypoint: `agent-orchestrator-ui`
- desktop-mode runtime paths that move audit and acceptance artifacts out of the repo and into normal user locations
- a macOS build scaffold script: `scripts/build_macos_app.sh`

This is packaging groundwork, not a signed or notarized end-user release.

## Desktop Runtime Paths On macOS

When the UI is launched through the desktop launcher, the app now defaults to these macOS user-writable locations:

- audit runs: `~/Library/Application Support/Agent Orchestrator/runs`
- acceptance reports: `~/Library/Application Support/Agent Orchestrator/acceptance`
- cache path if enabled: `~/Library/Caches/Agent Orchestrator/structured-results`

That keeps packaged app data out of the app bundle and out of the repo checkout.

## Build Prerequisites

- macOS
- Python 3.11+
- project UI dependencies
- packaging dependencies including PyInstaller

Install the packaging extras from the repo root:

```bash
pip install -e '.[ui,packaging]'
```

## Build Command

Use the scaffold script:

```bash
bash scripts/build_macos_app.sh
```

If the build succeeds, the app bundle is written under:

```text
dist/macos/Agent Orchestrator.app
```

## Current Caveats

- the packaged app still opens the guided UI in the system browser rather than an embedded native webview
- the output is a local `.app` bundle, not a signed installer
- notarization, signing, and drag-to-Applications polish are not implemented yet
- Ollama support in packaged builds is still a later follow-up

## What Must Still Happen Before External Non-Technical Testing

- validate that the generated `.app` launches on a second macOS machine
- verify that the first-run path works without the repo present on disk
- add plain-language failure handling around missing local model support
- decide whether the first non-technical release should be an `.app` bundle or a `.dmg`
