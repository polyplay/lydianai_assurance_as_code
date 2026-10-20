# Sphinx-Needs in the AAC app — is it needed?

*Proposal saved for future reference; no implementation planned at this time.*

## Context

While updating the LydianAI site to reflect the current app, Sphinx-Needs kept surfacing as a prominent capability: featured on the product page, called out in the CLI reference, and given its own section in the "Creating a project" doc. The question raised: is this compatibility genuinely load-bearing, or can it be removed? Two motivations are on the table:

- **Audience** — Sphinx-Needs is a niche requirements-authoring tool. Safety-critical automotive teams typically use DOORS, Polarion, or Jama. Leading with Sphinx risks looking narrow.
- **Complexity** — Sphinx-specific code adds ~1,500 LOC, six architecture functions, thirteen MUST-PASS acceptance criteria, a 70-entry type-mapping table, and a dedicated mapping specification. That is a lot of surface area for one particular tool.

## Findings

From a thorough survey of the AAC app codebase:

- Sphinx-Needs is the **only** bulk-import path in the app today. Direct artefact creation via API/CLI exists but is per-item; there is no generic CSV, XML, or canonical-JSON bulk loader.
- The architecture already anticipates multiple import sources: `F-IMP-03` through `F-IMP-06` are generic (state machine, conflict detection, batch processing, decision handling). Only `F-IMP-02` (the parser/normalizer) is Sphinx-specific.
- The 13 MUST-PASS acceptance criteria (`ACC-IMP-001` through `-014`) are largely about *import behavior* (conflict handling, ask-user vs automatic mode, resumable batching) — they are not intrinsically Sphinx-specific.
- Downstream features (validation, traceability, baselines, release gate, repository integration) are indifferent to the source: they operate on canonical artefact revisions and do not depend on any Sphinx-Needs metadata.
- `POST /api/v1/projects/{project_id}/imports/sphinx` is published in the OpenAPI schema, so removal is technically a contract break — but the app is pre-1.0.

## Recommendation: replace, don't remove

**Sphinx-Needs compatibility as-implemented is not needed. Bulk import is.** The right move is to keep the generic import pipeline and swap the Sphinx-specific parser + mapping for a generic canonical bulk-import format that any upstream tool can produce.

Why this beats both extremes:

- **Keep-as-is** carries the 1,500 LOC and ties the product story to a niche tool.
- **Remove-entirely** leaves users with no way to load 500+ requirements. Not viable for a real compliance workflow.
- **Replace** preserves the essential capability, deletes the Sphinx-specific complexity, and broadens audience — teams using DOORS/Polarion/Jama/CSV can export to the canonical format directly, and existing Sphinx-Needs users can be served by a small external adapter.

The app already treats the parser as a plug-in port (`ISphinxParser`), so this is refactoring in the direction the architecture was already pointing.

## Implementation outline

**App — remove Sphinx-specific pieces, add generic bulk-import**

1. Define a **canonical bulk-import format** (JSON, list of artefact records that mirror the existing canonical artefact schema plus optional relationship records).
2. Refactor `aac_backend/services/import_service.py` — retain the generic pipeline (F-IMP-03..06); drop `F-IMP-02` Sphinx parser and the `SPHINX_TYPE_TO_ARTEFACT_TYPE` 70-entry mapping; add a canonical-format parser.
3. Replace endpoint `POST /api/v1/projects/{project_id}/imports/sphinx` with `POST /api/v1/projects/{project_id}/imports/artefacts` (generic). Update `aac_backend/api/imports.py`.
4. Replace CLI command `aac import-sphinx` with `aac import` in `aac_backend/cli.py` (lines 376–381, 534).
5. Update the web UI import feature: relabel from Sphinx-Needs to generic bulk import in `web/js/features/imports.js`.
6. Delete `docs/sphinx_needs_mapping_specification.md`.
7. Rewrite `docs/requirements_baseline.md` (`AAC-IMPORT-FR-080` through `-085`) to be format-neutral.
8. Rewrite `docs/software_architecture.md` (`F-IMP-01` through `F-IMP-06`) — drop `ISphinxParser`, add `ICanonicalImportParser`.
9. Rewrite `docs/mvp_acceptance_criteria.md` (`ACC-IMP-001` through `-014`) as generic bulk-import criteria.
10. Update `documentation/user_manual.md` "Import Sphinx-Needs Evidence" section and `documentation/admin_manual.md`.
11. Update `tests/test_import_recovery.py` to use the canonical format fixtures.
12. Update the `make smoke-test` path if it currently uses the Sphinx endpoint.

**Site — remove Sphinx-Needs mentions, reference generic import**

13. `src/content/docs/assurance-cli.md` — replace `## Sphinx-Needs import` section (lines 57–70) with a generic `## Bulk import` section; update the CI scripting example on line 175.
14. `src/content/docs/assurance-creating-project.md` — replace the "Importing from Sphinx-Needs" section (lines 110–121) with a bulk-import section pointing at the canonical format.
15. `src/pages/github.astro` line 80 — change "Import from Sphinx-Needs or create items directly" to "Bulk-import from a canonical JSON file or create items directly".
16. `src/pages/assurance-as-code.astro` line 211 — in the User role card, change "Runs Sphinx-Needs imports" to "Runs bulk imports".

**Optional follow-up (out of scope for the initial change)**

17. Publish a small standalone `aac-sphinx-adapter` utility (separate repo) that reads a Sphinx-Needs JSON export and emits the canonical format, so existing Sphinx-Needs users are not stranded.

## Files to modify

App:
- `aac_backend/services/import_service.py`
- `aac_backend/api/imports.py`
- `aac_backend/models/imports.py` (schema fields may need adjustment)
- `aac_backend/cli.py`
- `web/js/features/imports.js`
- `docs/requirements_baseline.md`
- `docs/software_architecture.md`
- `docs/mvp_acceptance_criteria.md`
- `docs/sphinx_needs_mapping_specification.md` (delete)
- `documentation/user_manual.md`
- `documentation/admin_manual.md`
- `tests/test_import_recovery.py`

Site:
- `src/content/docs/assurance-cli.md`
- `src/content/docs/assurance-creating-project.md`
- `src/pages/github.astro`
- `src/pages/assurance-as-code.astro`

## Verification

- **App unit + integration:** `make test`, `make test-integration`.
- **App smoke:** `make smoke-test` (verify the end-to-end flow now uses the canonical import path).
- **API surface:** confirm OpenAPI at `/api/v1/docs` no longer exposes `/imports/sphinx`; confirms `/imports/artefacts` (or chosen name) is present.
- **CLI:** run `aac import --project-id PROJ_001 --file sample_canonical.json` against a running dev API.
- **Site:** `npx astro build`; spot-check `/assurance-as-code`, `/docs/assurance-creating-project`, `/docs/assurance-cli`, and `/github` in the dev server.
- **Regression:** run at least one baseline creation and release-gate evaluation using artefacts loaded via the new canonical import to confirm downstream features work unchanged.

## Effort estimate

Roughly 4–5 focused days of work: ~2 days on the backend refactor, ~1 day on doc rewrites, ~1 day on web UI + CLI + tests, ~0.5 day on site sync.
