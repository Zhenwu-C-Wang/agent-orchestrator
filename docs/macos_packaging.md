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
- a post-build validation script: `scripts/validate_macos_app.sh`
- a DMG build script: `scripts/build_macos_dmg.sh`
- a DMG validation script: `scripts/validate_macos_dmg.sh`

This is packaging groundwork, not a signed or notarized end-user release.

## Local Validation Status

The first local macOS app-bundle preview has now been built successfully on the maintainer machine, and a local DMG preview path now exists as well.

Current state:

- local `.app` bundle generation works
- local `.dmg` generation works
- packaged resources include `app.py`, `docs/project_status.json`, and the built-in sample datasets
- the next meaningful validation step is a second-machine launch check, not another same-machine build

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

The build script now ends by running:

```bash
bash scripts/validate_macos_app.sh
```

You can rerun that validation step independently after moving or reusing the bundle.

## DMG Preview Command

If you want a more shareable macOS preview artifact after the `.app` exists, run:

```bash
bash scripts/build_macos_dmg.sh
```

If the build succeeds, the DMG is written under:

```text
dist/macos/Agent Orchestrator.dmg
```

The DMG build script ends by running:

```bash
bash scripts/validate_macos_dmg.sh
```

That validation step checks:

- the disk image verifies cleanly
- the mounted image contains `Agent Orchestrator.app`
- the mounted image includes an `Applications` shortcut

## Current Caveats

- the packaged app still opens the guided UI in the system browser rather than an embedded native webview
- the output is now a local `.app` bundle plus a local `.dmg` preview, but neither is a signed installer
- notarization, signing, and drag-to-Applications polish are not implemented yet
- Ollama support in packaged builds is still a later follow-up

## What Must Still Happen Before External Non-Technical Testing

- validate that the generated `.app` and `.dmg` launch cleanly on a second macOS machine
- verify that the first-run path works without the repo present on disk
- add plain-language failure handling around missing local model support
- decide whether the first non-technical release should remain a `.dmg` or move to a more polished signed distribution flow
