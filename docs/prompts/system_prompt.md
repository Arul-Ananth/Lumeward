# Lumeward System Prompt

## Purpose

This prompt is the short compatibility-facing context restoration prompt for agents or tools that still expect `docs/prompts/system_prompt.md` to exist.

Use it to quickly regain working context in the Lumeward repository without duplicating the full architecture notes.

## Product Summary

Lumeward is a hybrid AI brief assistant with two runtime modes built on a shared backend core:

- `SERVER`
  - FastAPI backend for web clients.
  - Supports `trusted_lan` and `interactive` auth profiles.
  - Can optionally route model calls through a remote OpenAI-compatible engine.
  - Supports explicit `.zip` folder upload through `/news/ingest/folder` for local indexing.
- `DESKTOP`
  - PySide6 desktop app.
  - Local bridge ingestion, OCR, clipboard/file context capture, and brief generation.
  - Desktop UI is structured around `Personal Feed`, collapsible `Guidance`, and `Deep Dive Viewer`.

## Runtime and Trust Summary

- Startup resolution lives in `backend/main.py`.
- Runtime precedence is: CLI flags, then environment variables, then code defaults.
- Desktop mode resolves to the local desktop identity path.
- `untrusted` is documentation terminology for server deployments that use the `interactive` auth profile with normal hardening.

## Primary Docs To Consult

Start with these documents instead of relying on this file for deep implementation detail:

- `README.md`
  - operator-facing summary of current implemented behavior
- `modes.md`
  - runtime modes, trust profiles, and connectivity profiles
- `docs/architecture/overview.md`
  - current implementation shape
- `docs/security.md`
  - trust boundaries and safeguards
- `docs/roadmap.md`
  - implemented work versus optional future items
- `docs/prompts/context_restoration_system_prompt.md`
  - fuller repo-context prompt for implementation work

## Assistant Rules

- Use the repository code as the source of truth.
- Prefer the current domain-based service paths under `backend/common/services/`.
- Do not invent routes, settings, tools, or modules that do not exist in the repo.
- If docs and code diverge, trust the code first and then update the docs.
- Keep responses concise, implementation-aligned, and explicit about paths and commands.

## Known Caveat

This is the short compatibility prompt.

If deeper architectural or implementation context is needed, use `docs/prompts/context_restoration_system_prompt.md` as the fuller reference.
