# Documentation Index

## Current sources of truth

- `../README.md`: setup, dependencies, implemented product summary and startup.
- `../modes.md`: local desktop, enterprise desktop, server, auth and Qdrant profiles.
- `architecture/overview.md`: current code and domain architecture.
- `architecture/migration_strategy.md`: versionless desktop/server schema behavior.
- `security.md`: current trust boundaries, safeguards and deferred hardening.
- `roadmap.md`: implemented, next and explicitly deferred work.
- `deployment/enterprise-packaging.md`: native Qdrant and server/desktop distribution model.

## Component documentation

- `../backend/desktop/README.md`
- `../backend/server/README.md`
- `../backend/common/services/auth/README.md`
- `../frontend/README.md`
- `../scripts/dev/README.md`

## Historical material

The following files are retained for decision history and are not statements of
current implementation:

- `architecture/enterprise_team_context_assessment.md`
- `architecture/openclaw_parity_privacy_security_recommendations.md`
- `frontend_desktop_feature_parity_plan.md`
- `audits/issues.md`
- `audits/clipboard_history_diagnosis.md`

## Agent prompts

- `prompts/system_prompt.md` is a short compatibility aid.
- `prompts/context_restoration_system_prompt.md` is deprecated and points to the
  current source-of-truth documents.

When documentation and code disagree, treat code as authoritative and update
the active documentation in the same change.
