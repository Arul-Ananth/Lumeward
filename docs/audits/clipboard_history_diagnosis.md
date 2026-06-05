# Clipboard History Diagnosis

Date: 2026-03-21

## Summary

The desktop clipboard-history behavior is currently broken for two separate reasons:

1. **Primary runtime bug:** the opt-in preference is saved, but the clipboard collector still checks the static config flag instead of the saved preference-derived runtime state.
2. **Secondary retrieval design issue:** even when clipboard events exist, prompts like `what did i just copy to clipboard` and `tell me what i know about langchain from my clipboard history` use semantic memory retrieval rather than a direct recent-clipboard lookup, so they can return unrelated or older content.

## Primary Bug

### What is happening

- The desktop settings dialog writes clipboard preferences to `QSettings`.
- `TelemetryManager.start()` reads those preferences.
- But `ClipboardCollector.start()` does **not** use the preference value that was read.
- Instead it checks `settings.CLIPBOARD_COLLECTION_ENABLED`, which remains the `.env` default unless explicitly updated in memory.

### Evidence

Current code path:

- Preferences are saved in [backend/desktop/preferences.py](C:/Dev/lumeward/backend/desktop/preferences.py)
- Settings dialog writes them in [backend/desktop/ui/settings_dialog.py](C:/Dev/lumeward/backend/desktop/ui/settings_dialog.py)
- Telemetry manager reads the preference in [backend/desktop/telemetry_manager.py](C:/Dev/lumeward/backend/desktop/telemetry_manager.py)
- Clipboard collector incorrectly gates startup on static config in [backend/desktop/collectors/clipboard_collector.py](C:/Dev/lumeward/backend/desktop/collectors/clipboard_collector.py)

The actual mismatch observed in this environment was:

```text
settings.CLIPBOARD_COLLECTION_ENABLED = False
settings.CLIPBOARD_STORE_RAW_TEXT = False
preference.data_collection = True
preference.clipboard_collection = True
preference.clipboard_store_raw_text = True
```

That means the UI opt-in was saved, but the collector still sees clipboard collection as disabled.

### Impact

- New clipboard changes are not captured for the current session even though the user enabled the feature.
- Session summaries therefore show `Clipboard highlights: none`.
- Queries about clipboard history then operate on stale or unrelated memory.

## Secondary Design Issue

Even after the primary bug is fixed, the current retrieval path is still not suitable for “what did I just copy?” style queries.

### Current flow

```text
clipboard change
-> telemetry event
-> session summary/profile memory
-> vector similarity search by topic text
-> generation prompt
```

### Why this fails

- The newsletter pipeline uses `get_memory_context(user_id, topic, session_id)`.
- Memory retrieval is semantic similarity on the user query string, not deterministic recent clipboard lookup.
- A query like `tell me what i know about langchain from my clipboard history` will match older stored content if that content is semantically stronger than the recent clipboard text.
- Clipboard text also gets truncated in session summaries.

Relevant files:

- [backend/common/services/newsletter/pipeline.py](C:/Dev/lumeward/backend/common/services/newsletter/pipeline.py)
- [backend/common/services/memory/vector_db.py](C:/Dev/lumeward/backend/common/services/memory/vector_db.py)
- [backend/common/services/telemetry/workers.py](C:/Dev/lumeward/backend/common/services/telemetry/workers.py)

## Supporting Observation

The desktop database does contain historical clipboard events, but not for the current failing sessions. That aligns with the runtime-gate bug: older sessions captured clipboard text, current opt-in sessions did not.

## Reproduction

1. Leave `.env` with `CLIPBOARD_COLLECTION_ENABLED=false`.
2. Open desktop settings.
3. Enable:
   - desktop telemetry
   - clipboard collection
   - raw clipboard text
4. Restart or continue using the app.
5. Copy new text.
6. Ask a clipboard-history question.

Observed result:

- Session summary still shows `Clipboard highlights: none`.
- The answer is generated from unrelated or older memory.

## Root Cause

The runtime source of truth for clipboard enablement is split across two places and not synchronized:

- persisted preference: `QSettings`
- runtime gate: `settings.CLIPBOARD_COLLECTION_ENABLED`

The collector startup gate uses the wrong one.

## Recommended Fix

### Required fix

- Make clipboard collector startup depend on the preference-derived runtime value, not the static config default.
- Ensure `TelemetryManager.start()` synchronizes both:
  - `settings.CLIPBOARD_COLLECTION_ENABLED`
  - `settings.CLIPBOARD_STORE_RAW_TEXT`

### Recommended follow-up fix

Add a separate short-lived recent clipboard store for direct lookup, instead of relying only on semantic memory retrieval. That should be used for prompts like:

- `what did i just copy to clipboard`
- `what do i know from my clipboard history`

## Verify Script

A verification script was added here:

- [verify_clipboard_runtime_optin.py](C:/Dev/lumeward/scripts/verify/verify_clipboard_runtime_optin.py)

Run it with your active Python environment to confirm the mismatch.
