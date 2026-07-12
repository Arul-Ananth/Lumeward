# Clipboard History Diagnosis

> Historical resolved diagnosis. Current privacy behavior is documented in
> `../security.md` and `../../modes.md`.

Date: 2026-03-21
Status: Resolved
Resolution verified: 2026-07-12

## Summary

This audit records two historical clipboard-history defects:

1. The desktop UI persisted clipboard consent, but the collector previously
   read only the static configuration value.
2. Clipboard questions previously relied only on semantic vector retrieval,
   which could favor older or unrelated memories.

Both defects are resolved in the current implementation. This document remains
as regression context.

## Implemented Resolution

- `backend/desktop/telemetry_manager.py` synchronizes the preference-derived
  clipboard settings into the runtime configuration before collection starts.
- `backend/desktop/collectors/clipboard_collector.py` accepts the resolved
  runtime enablement value and observes the raw-text consent setting.
- `backend/common/services/memory/vector_db.py` detects clipboard-history
  questions and retrieves recent clipboard events directly.
- `backend/common/services/newsletter/pipeline.py` adds that direct clipboard
  context before falling back to semantic memory.

The direct path preserves session preference, de-duplicates text, limits the
amount of context, and reports clearly when no matching clipboard entry exists.

## Original Impact

Before the fix, newly copied text could be absent even after the user enabled
clipboard collection. Questions such as `what did I just copy?` could then use
older semantically similar memory instead of recent clipboard events.

## Regression Verification

Run these checks with the supported desktop environment:

```powershell
.\venv_win\Scripts\python.exe scripts\verify\verify_clipboard_runtime_optin.py
.\venv_win\Scripts\python.exe scripts\verify\verify_clipboard_query_context.py
```

The implementation, rather than this historical audit, is the source of truth
for current behavior.
