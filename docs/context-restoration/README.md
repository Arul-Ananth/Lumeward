# Temporary Context Restoration Guide

Prepared on 2026-07-16 for moving the organization-administration portal work
to another computer. This folder is a temporary handoff, not a replacement for
the durable project documentation.

## Important Git boundary

At the time this handoff was prepared, the working tree was based on branch
`master` at commit `00b3f1c` and contained uncommitted implementation changes.
Uncommitted files do not appear on another computer after clone or pull.

Before leaving the source computer:

1. Run `git status --short` and review every source and documentation change.
2. Do not add `.env`, databases, `data/`, `node_modules/`, `frontend/dist/` or
   any credentials.
3. Commit the intended source, tests and documentation, including this folder.
4. Push that commit to a branch reachable from the second computer, or transfer
   a Git bundle/patch through an approved secure channel.
5. Record the final branch and commit ID here if they differ from the base above.

No commit or push was performed while creating this handoff.

## Restore on the second computer

1. Clone the repository or fetch the branch containing the handoff commit.
2. Check out that exact branch/commit and confirm `git status --short` is clean.
3. Read, in order:
   - this file;
   - `implementation-handoff.md`;
   - `verification.md`;
   - `../architecture/overview.md`;
   - `../security.md`;
   - `../deployment/enterprise-testing.md`.
4. Recreate local secrets from `.env.example`. Transfer the real `.env` only
   through an approved secret-management channel; never commit it.
5. Restore PostgreSQL and Qdrant services or create clean development instances.
6. Install dependencies and run the commands in `verification.md` before making
   further changes.

## Working assumptions

- The product is Lumeward.
- The web administration area is for an organization's administrators, not for
  Lumeward infrastructure operators.
- Organization activation is immediate after signup.
- The first workspace is required immediately after signup.
- Email/password sessions are retained; OIDC and additional authentication
  features are outside this release.
- Existing desktop signup and APIs remain backward compatible.
- Simplicity and readable feature boundaries are preferred over a general
  frontend state library or speculative abstractions.

Delete `docs/context-restoration/` after the work is safely restored and all
durable documentation has been rechecked.
