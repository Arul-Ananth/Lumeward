# Lumeward Enterprise Team-Context Architecture Assessment

> **Historical assessment (2026-07-12):** This records the pre-implementation
> findings that motivated the enterprise work. Its claims about missing event
> ownership, organizations, workspaces, tags and plugin-grant models are no
> longer current. Use `architecture/overview.md`, `modes.md` and `roadmap.md`
> for implemented status. Plugin execution, enterprise identity federation,
> compliance operations and complete member onboarding remain future work.

Date: 2026-07-12

Status: architecture assessment only. This document does not implement the proposed changes and is not legal advice.

## Executive conclusion

Lumeward is **partially aligned** with the intended product, but the current server architecture is not yet suitable for a multi-user enterprise team-context deployment.

The local desktop foundation is sound: it has an explicit desktop runtime, local SQLite and embedded Qdrant storage, a fixed local identity, opt-in collectors, and native capabilities that a browser cannot reliably provide. The server foundation also has useful pieces: authenticated users, PostgreSQL, server Qdrant, per-user digests, schedules, feed cards, and vector filters.

The missing center of the enterprise model is ownership and authorization. Lumeward currently understands either one local desktop user, one shared synthetic server user, or unrelated interactive users. It does not understand organizations, teams/workspaces, memberships, roles, team-scoped context, personal-versus-team visibility, independently granted plugin permissions, or tags.

The desired enterprise product should not be modeled as "one shared user." It should be modeled as:

```text
Organization
  -> Teams / workspaces
      -> Members and roles
      -> Team-relevant context sources
      -> Shared tags and policies
      -> Individually personalized feeds
  -> Plugin installations and permission grants
  -> Retention, residency, audit, and export policies
```

The shared engine should perform generation and retrieval under an authenticated user and active team context. It should not itself become an undifferentiated shared memory bucket.

## Intended product model

### Local desktop

- One normal user runs Lumeward locally.
- Local collectors, context, preferences, feed, model choice, and storage remain local by default.
- Native clipboard, folder watching, OCR, hotkeys, and keyring capabilities remain available.
- A local user may optionally connect to an enterprise team service, but local/private context must not be uploaded implicitly.

### Enterprise

- Every human has an individual enterprise identity.
- A user can belong to one or more teams/workspaces.
- A team draws context that affects that team's work; it does not automatically ingest all enterprise information.
- Context has an explicit scope such as `private`, `team`, or `organization`, with `team` as the normal enterprise default.
- Feed ranking is personal to the user and may use role, interests, explicit follows/mutes, tags, and team priorities.
- Shared context and personal feed preferences are distinct data domains.
- Plugins are installed and permissioned independently. An email connector does not inherit an RSS connector's permissions, credentials, teams, or data access.
- Tags are first-class metadata, not strings embedded only in generated text.

## Current alignment

### What already aligns

1. **Local-first desktop runtime.** `backend/desktop/main.py` creates a fixed local user and starts local storage and native services. This is a reasonable model for a normal single-user desktop app.

2. **Shared backend services.** Generation, memory, ingestion, feeds, and newsletter behavior are under `backend/common/services/`, which is the right general boundary for reuse by desktop and enterprise clients.

3. **Some per-user isolation exists.** Digests, schedules, feed cards, feedback memories, and Qdrant retrieval use `user_id`. This is a useful starting point, but it is not a team authorization model.

4. **Native collection is opt-in.** Clipboard and telemetry settings are separate and default off. That aligns with privacy-by-default better than implicit collection.

5. **Network actions have an allowlist policy.** `backend/common/services/security_policy.py` validates known network actions and blocks search access to local/private addresses. The policy should become the common enforcement point for plugins rather than remaining limited to search and engine health.

6. **Source permissions are anticipated.** `backend/common/services/newsletter/sources.py` lists example permissions such as network, file, storage, and secret access. These are metadata only, but the vocabulary is directionally useful.

### What does not yet align

#### 1. There is no team/workspace domain model

`backend/common/models/sql.py` has `User`, but no organization, team, workspace, membership, role assignment, or policy tables. A `user_id` foreign key cannot express:

- context shared with one team but not another;
- a team member's role;
- team administration versus ordinary membership;
- organization context selectively made available to a team;
- a user's private context combined with permitted team context;
- plugin grants limited to selected teams.

This is the most important architectural gap.

#### 2. Shared mode is the wrong enterprise abstraction

The current shared/trusted path resolves every request to one synthetic identity. The documentation explicitly states that memory/profile state is shared for that identity. This is acceptable only for a single trusted kiosk or genuinely communal workspace.

It cannot provide individual feed customization, per-user audit records, revocation, private preferences, or team boundaries. Enterprise mode should always authenticate individual users. `AUTH_MODE=shared` should remain a local/demo compatibility mode, not the enterprise deployment mode.

#### 3. Raw events can cross user boundaries

`EventRaw` has no `user_id`, `team_id`, visibility, or source-installation owner. `load_unprocessed_events()` in `backend/common/services/intelligence_feed/ingestion_events.py` queries all qualifying events and then normalizes each result using the `user_id` supplied by the feed request.

Consequently, in a multi-user server, an event created from one user's clipboard, upload, or generation may be processed into another user's feed. The resulting `IntelligenceFeed` row is user-scoped, but its source event was not.

This is a release-blocking enterprise isolation defect. Event ownership and authorization must be stored on the event and included in the database query; filtering after retrieval is insufficient.

#### 4. Personalization is hard-coded rather than user- or role-driven

`backend/common/services/intelligence_feed/feed_scorer.py` uses global constants such as `BOOSTED_KEYWORDS` and `MUTED_KEYWORDS`. Every user receives the same keyword policy. Feedback is saved as vector memory, but there is no explicit feed-preference model for:

- followed or muted tags;
- role and responsibility;
- source weights;
- team priorities;
- notification thresholds;
- private versus shared ranking signals.

A personal feed needs a durable `FeedPreference` model and a ranking input assembled from user preferences, membership role, team policy, and item metadata. Role should influence relevance, not automatically grant data access.

#### 5. Tags are not implemented as a first-class feature

Feed topics are stored as JSON text, but there are no tag entities, normalized tag keys, aliases, tag assignments, tag visibility, or tag-based retrieval APIs. Qdrant payloads also lack a consistent tag and scope schema.

Recommended minimum model:

- `Tag(id, organization_id, normalized_key, display_name, color, description)`
- `ContextTag(context_item_id, tag_id, source=manual|plugin|derived, confidence)`
- `UserTagPreference(user_id, tag_id, weight, muted)`
- optional `TeamTagPolicy(team_id, tag_id, priority, required|blocked)`

Tags should help retrieval and feed ranking. They should not be treated as authorization labels unless a separate, explicit policy maps them to access rules.

#### 6. Plugins do not exist yet

`/news/sources` exposes planned metadata only. There is no loader, signed manifest, installation record, isolated runtime, version policy, credential vault binding, permission grant, source checkpoint, health state, or revocation path.

The placeholder endpoint should not evolve directly into in-process arbitrary Python imports. Plugins should be connectors behind a narrow protocol:

```text
Plugin manifest
  -> requested capabilities
  -> administrator/user grant for a defined scope
  -> isolated connector process or remote connector
  -> normalized ContextItem output
  -> central validation, tagging, retention, and indexing
```

Each plugin installation needs its own permission grant. Recommended capability families are:

- `network:origin`
- `secret:credential_reference`
- `context:write` with allowed team/workspace IDs
- `context:read` only when essential and separately approved
- `filesystem:user_selected` for desktop connectors
- `schedule:poll`
- `webhook:receive`

Default should be no context read, no arbitrary filesystem access, no subprocess execution, no unrestricted network, and no access to another plugin's secrets. The model should validate typed plugin outputs and treat all retrieved content as untrusted input because context can contain prompt injection.

#### 7. Context is tied directly to users and Qdrant collections

Vector retrieval filters only on `user_id`. Team context needs a stable relational source of truth and a richer vector payload, for example:

```text
organization_id
workspace_id
owner_user_id
visibility
source_installation_id
context_item_id
tags
classification
retention_policy_id
```

Authorization should first produce an allowed-scope filter; retrieval should then apply that filter in both SQL and Qdrant. Do not rely on the LLM prompt to enforce visibility.

#### 8. Enterprise identity is too application-local

Interactive email/password auth is adequate for development, but enterprise deployments normally need federation, centralized deprovisioning, MFA policy, group/role claims, and conditional access through the organization's identity provider.

Use OpenID Connect with authorization code plus PKCE and map external identities and groups to Lumeward memberships. Current OAuth security best practice is [RFC 9700](https://www.rfc-editor.org/info/rfc9700/), published in 2025; it recommends PKCE for public clients and emphasizes restricted token privileges and secure redirect handling.

## Recommended target architecture

### Core ownership model

Use one codebase and one service boundary, with mode-specific adapters:

```text
Desktop-local mode
  Native desktop shell
    -> local application services
    -> SQLite + embedded Qdrant
    -> local plugin grants and OS permissions

Enterprise mode
  Desktop client and/or browser client
    -> authenticated API
    -> authorization policy service
    -> team context and personal feed services
    -> PostgreSQL + Qdrant
    -> isolated plugin connector runtime
    -> enterprise identity provider
```

The enterprise request context should include at least:

```text
user_id
organization_id
active_workspace_id
membership roles/attributes
allowed context scopes
purpose/action
```

### Separate shared context from personal state

Recommended domains:

- `ContextItem`: normalized source content and provenance.
- `ContextScope`: private/team/organization visibility and authorization attributes.
- `PluginInstallation`: connector identity, owner scope, version, and status.
- `PluginGrant`: independently approved capabilities and resource constraints.
- `FeedPreference`: personal follows, mutes, weights, and role-related preferences.
- `FeedItem`: a user-specific ranking/result referencing authorized context items.
- `Tag` and assignments: shared vocabulary plus personal weighting.
- `AuditEvent`: actor, action, resource, purpose, policy result, and trace ID.
- `RetentionPolicy`: lifecycle attached to context categories or source installations.

The inference engine should receive a request-specific context bundle containing only authorized and relevant items. Shared engine access does not imply shared visibility.

### Authorization approach

Simple RBAC alone will become awkward because access depends on user, team, resource scope, plugin installation, action, and sometimes data classification. A small hybrid model is appropriate:

- RBAC for coarse actions: organization admin, team admin, member, plugin operator.
- Resource ownership for private and team items.
- Attribute checks for workspace, visibility, source, classification, and action.

This matches the resource-focused direction in [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final), which rejects implicit trust based on network location, and the subject/object/action/environment model described in [NIST SP 800-162](https://csrc.nist.gov/pubs/sp/800/162/upd2/final).

Avoid building a general-purpose policy language initially. Central Python policy functions with deny-by-default behavior, typed inputs, and comprehensive tests are enough until policy complexity justifies an external engine.

## Least-privilege assessment

The present application is not least-privilege ready for enterprise context because shared mode collapses identities, events lack ownership, and plugin permissions are only descriptive metadata.

The target should enforce least privilege at several layers:

1. **Human access:** authenticate each user and authorize each action against the active team and resource.
2. **Plugin access:** one installation, one credential set, one capability grant, selected teams only.
3. **Database access:** separate migration/admin credentials from runtime credentials; the runtime account should not create/drop databases or schemas.
4. **Vector access:** construct server-side filters from authorized scope; never accept unrestricted user-supplied filters.
5. **Engine access:** the engine receives only the selected context bundle and has no direct database or plugin credential access.
6. **Desktop access:** request OS permissions only for the selected collector; keep clipboard and screen capture disabled by default.
7. **Network access:** explicit egress destinations per plugin and engine, with redirect and DNS rebinding defenses.
8. **Operations:** immutable or tamper-evident audit records for access, grants, exports, deletions, and administrative changes.

[NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final) states that enterprise resources should not be trusted solely because they are on a LAN and that access should use the least privileges needed for the task. [OWASP's authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) likewise recommends deny-by-default and horizontally and vertically restricted permissions. For plugins specifically, OWASP recommends vetting third parties and limiting their access to specific resources with strict ingress and egress controls; see [Ungoverned Usage of Third-Party Services](https://owasp.org/www-project-top-10-ci-cd-security-risks/CICD-SEC-08-Ungoverned-Usage-of-3rd-Party-Services) and [LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

## Privacy and compliance readiness

Lumeward processes potentially sensitive employee material: clipboard contents, documents, browsing/reading telemetry, role preferences, feedback, and inferred interests. Internal deployment does not remove privacy or employment-law obligations.

The exact legal obligations depend on jurisdiction, industry, customer contracts, data types, and how the feed is used. The following are architectural capabilities, not a declaration of legal compliance.

### Required capabilities

- A documented purpose and lawful basis for each collector and plugin source.
- Data minimization: collect only fields needed for the team workflow.
- Per-source retention and automatic deletion, including vectors and derived summaries.
- Provenance from each derived item back to the source and plugin installation.
- User and administrator access/export/correction/deletion workflows.
- Legal hold support that overrides deletion in a controlled, auditable way.
- Data residency controls for relational data, vectors, logs, backups, plugins, and remote inference.
- Encryption in transit and at rest, with enterprise-managed secret storage and rotation.
- Records of processing: purpose, categories, recipients/processors, transfers, retention, and controls.
- Audit logs that avoid recording raw sensitive context unless explicitly necessary.
- Tenant/team isolation tests and deletion verification across SQL, Qdrant, caches, backups, and plugin checkpoints.
- A clear controller/processor/subprocessor model for hosted engines and third-party plugins.
- A DPIA/risk-assessment path for broad employee monitoring or profiling.

The EU GDPR's [Article 5 principles](https://eur-lex.europa.eu/eli/reg/2016/679/art_5/oj/eng) include purpose limitation, data minimization, storage limitation, and integrity/confidentiality. The same official regulation requires [data protection by design/default](https://eur-lex.europa.eu/eli/reg/2016/679/art_25/oj/eng), [records of processing](https://eur-lex.europa.eu/eli/reg/2016/679/art_30/oj/eng), and [risk-appropriate security](https://eur-lex.europa.eu/eli/reg/2016/679/art_32/oj/eng). The [NIST Privacy Framework](https://www.nist.gov/privacy-framework/getting-started-0) provides a useful non-legal method for managing privacy risk across organizational roles.

If Lumeward is later used to evaluate employee performance, allocate work, rank workers, or make employment decisions, obtain specialist review. The European Commission's current [AI Act guidance](https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act) identifies certain employment and worker-management uses as potentially high-risk. A personalized information feed is not automatically such a system, but feature drift could move it into that category.

## Is a web UI required?

**No. A web UI is not required for the core architecture.** Enterprise users can run a desktop client that authenticates to the shared team API. The server/API, identity, authorization, team context, plugin administration, and audit model are required; a browser client is only one possible client.

However, some enterprise workflows benefit strongly from a web surface:

- organization and team administration;
- membership and role management;
- plugin installation and independent permission review;
- audit, retention, residency, and export controls;
- zero-install access for users who do not need native collectors.

The preferred long-term arrangement is one canonical business UI, not two fully independent products:

```text
Shared React business UI
  -> browser for enterprise users/admins
  -> embedded or locally served inside a thin desktop host

Thin native host
  -> clipboard, folder watch, OCR, hotkeys, keyring, OS permissions
```

This keeps native desktop capabilities while avoiding duplicate PySide and React implementations of feeds, history, schedules, tags, plugin management, and settings. If embedding React is not desired, the alternative is to keep PySide as the normal-user UI and build only a small enterprise administration web console. Maintaining two complete user-facing UIs indefinitely is the least attractive option.

## Bloated, redundant, or outdated areas

### High-value simplifications

1. **Two business UIs.** PySide and React already expose different subsets of the product. Adding teams, tags, plugin grants, provenance, and policy screens twice will create significant duplication. Select a canonical business UI before implementing those features.

2. **Verification-script sprawl.** `scripts/verify/` contains 29 Python files and about 1,588 lines, while `tests/` contains about 274 lines. Deterministic checks should continue moving to pytest fixtures and parametrized tests. Keep scripts only for packaging, live external services, and manual operational checks.

3. **Many small Qt worker classes.** Feed refresh, processing, dismissal, and deep dive each have nearly identical QThread/session/error scaffolding. A reusable desktop task runner can preserve signals and cancellation while removing repeated lifecycle code.

4. **CrewAI for a fixed two-step workflow.** `build_newsletter_crew()` constructs researcher and writer agents for a deterministic research-then-summarize operation. Unless autonomous delegation is a product requirement, a direct provider call with an explicit search step and typed result is easier to test, cheaper, and easier to constrain. Plugin execution should not be placed under an open-ended agent loop.

5. **Compatibility auth concepts.** `shared`, legacy `trusted_lan`, `desktop_local`, and interactive identities are understandable historically but should not shape the enterprise domain. Keep desktop-local and federated enterprise identity as the two product concepts; retain legacy aliases only at configuration parsing boundaries.

6. **Metadata-only source endpoint.** The placeholder source catalog is harmless but should be replaced by real plugin manifests/installations rather than expanded as another parallel source abstraction.

7. **JSON text for structured relationships.** Topics, bullets, and raw event IDs are stored as JSON strings. This was expedient for a beta, but tags, provenance, authorization, and compliance queries need normalized relational records or native JSON columns with carefully designed indexes.

### Outdated or risky patterns

- `datetime.utcnow()` is deprecated and used widely. Adopt timezone-aware UTC values before expanding schedules and audit records.
- Application-local email/password accounts are not the preferred enterprise identity architecture. Use OIDC federation and current OAuth guidance.
- LAN location as a trust decision is outdated for enterprise access; use individual identity and resource authorization.
- Bearer session tokens stored in browser `sessionStorage` are a weaker enterprise browser posture than server-managed secure HttpOnly cookies or a well-designed OIDC BFF pattern.
- Global configuration objects mutated at runtime make multi-tenant and per-request policy difficult. Enterprise-specific choices should be request-scoped or organization/workspace configuration, not process globals.
- Multiple SQL commits inside ingestion make SQL/Qdrant consistency and compliant deletion harder. Introduce explicit ingestion states, stored vector IDs, retry/compensation, and deletion jobs.
- Qdrant collections are selected globally by configuration. This is acceptable, but tenant/team isolation must be encoded in every payload and centrally enforced filter; collection names alone should not be the authorization boundary.

### Architecture that should be retained

- Mode-aware local versus server storage.
- Shared application services independent of UI.
- Explicit native desktop boundary for OS capabilities.
- Relational metadata plus vector retrieval, provided SQL remains the source of truth.
- Opt-in local collectors.
- A central network/tool policy layer, expanded to plugins and context authorization.
- Typed API schemas and deterministic validation at trust boundaries.

## Recommended implementation order

1. Fix raw-event ownership immediately: add organization/workspace/user ownership and query-time authorization.
2. Define organization, workspace/team, membership, and role models.
3. Define `ContextItem`, provenance, visibility, classification, and retention fields as the source of truth.
4. Add authorization policy functions and tests for private/team/organization access.
5. Add first-class tags and personal feed preference models.
6. Change feed ranking to combine authorized context, personal preferences, role relevance, team policy, and explicit feedback.
7. Introduce federated enterprise identity and membership provisioning.
8. Define plugin manifests, installations, independently scoped grants, secret references, and isolated execution.
9. Add audit, export, deletion, retention, and residency controls before broad employee-data ingestion.
10. Choose the canonical business UI, then implement team, tag, plugin, and administration screens once.

## Final verdict

The overall split between desktop, server, and shared services is a good starting architecture. The current notion of enterprise sharing is not aligned with the stated goal because it shares an identity rather than selectively sharing team-relevant context among individually identified users.

Do not add plugins or tags on top of the existing shared-user model. First establish ownership, team membership, context scope, and centralized authorization. Once those foundations exist, tags, personal feed customization, and independently permissioned plugins fit naturally without turning the codebase into a collection of special cases.
