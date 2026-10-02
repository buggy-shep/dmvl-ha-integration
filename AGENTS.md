# AGENTS.md — dmvl-ha-integration

Working agreement for humans and AI agents contributing to this repository.

## 1. Role in the group

This repository is part of a group of projects that build a self-hosted
control stack for a residential utility account ("Domovladelets" / homeowner):

| Repository | Role | Visibility | Language |
|---|---|---|---|
| `pydmvl` | Python client for the homeowner account API | public | English |
| `dmvl-ha-integration` (this repo) | Home Assistant custom integration, consumes `pydmvl` from PyPI | public | English |

The integration is the consumer: it depends on `pydmvl` as an external package,
does not duplicate client logic, and performs no authentication of its own.
Group identity: code name `dmvl`, package/import `pydmvl`, Home Assistant
domain `dmvl`.

## 2. Language

All repository text is English: code, comments, docstrings, documentation,
commit messages, and review notes. Runtime translation files under
`custom_components/dmvl/translations/*.json` are user-facing content and may be
written in another language (there is a `ru.json` because the service is used
in Russia); everything else stays English.

## 3. Stack and commands

- Home Assistant custom component under `custom_components/dmvl/`.
- Validation: `hassfest` + HACS validation run in CI
  (`.github/workflows/validate.yml`).
- Local tests use `pytest` with `pytest-homeassistant-custom-component`
  fixtures.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements_dev.txt
.venv/bin/pytest -m "not live"
```

Live tests (real account, real credentials) carry the `live` marker and are run
manually only. Credentials come from the environment: `DMVL_USERNAME`,
`DMVL_PASSWORD`.

## 4. HACS compatibility (hard requirements)

The repository must stay installable and validatable by HACS
(https://hacs.xyz/docs/publish/integration). CI
(`.github/workflows/validate.yml`) enforces this; never merge changes that break
it.

- Layout: exactly one integration per repository — a single subdirectory under
  `custom_components/`, named after the domain (`custom_components/dmvl/`).
  Every file the integration needs at runtime lives inside that directory;
  repo-root files (`hacs.json`, `README.md`, `specs/`, workflows) are not
  runtime content.
- `hacs.json` sits in the repository root. `name` is the only required key.
  Keep the file minimal and do not invent keys.
- `manifest.json` must define at least the HACS-required keys `domain`,
  `name`, `documentation`, `issue_tracker`, `codeowners`, `version`, plus the
  keys required by hassfest. `version` must be AwesomeVersion-compatible
  (SemVer) and must equal the tag of the release that ships it.
- Brand assets: `custom_components/dmvl/brand/icon.png` must exist — HACS
  validates it directly. Optional files follow the brands conventions:
  `logo.png`, `dark_icon.png`, `dark_logo.png`, and the `@2x` variants.
- GitHub releases: every change to runtime code ships as a tagged release
  (`vX.Y.Z` — a full GitHub Release, a tag alone is not enough). HACS derives
  the offered version from the latest release tag.
- Repository metadata on GitHub: public repository, description filled in,
  topics set, issues enabled.
- CI checks (`hacs/action` with `category: integration`,
  `home-assistant/actions/hassfest`) must stay green. Do not add entries to
  `with.ignore`; if a check ever needs ignoring, record the reason in a spec.
- Inclusion in the HACS default store (`hacs/default`) is optional and is not
  pursued while the dependency is unpublished.

## 5. Home Assistant integration standards

Follow the official integration development docs
(https://developers.home-assistant.io):

- File structure: runtime files under `custom_components/dmvl/` (`__init__.py`,
  `manifest.json`, `config_flow.py`, `const.py`, coordinator, platform files,
  `diagnostics.py`, `translations/en.json`). Tests mirror the Home Assistant
  layout: `tests/` at the repository root with `__init__.py` and
  `conftest.py`.
- Manifest: `integration_type: hub`, `iot_class: cloud_polling`,
  `config_flow: true`, `requirements` pinned with `==` and limited to packages
  not shipped with Home Assistant core.
- Config flow: attach a stable string `unique_id` (the normalized login; never
  a user-changeable name) with `async_set_unique_id` +
  `_abort_if_unique_id_configured`; support `reconfigure`; trigger `reauth` via
  `ConfigEntryAuthFailed`; use an options flow for optional settings; on schema
  changes bump `VERSION`/`MINOR_VERSION` and implement `async_migrate_entry`.
- Setup: validate the account in `async_setup_entry` and raise
  `ConfigEntryNotReady` (retry) or `ConfigEntryAuthFailed` (reauth) instead of
  failing; implement `async_unload_entry`; keep runtime objects on
  `entry.runtime_data` (not `hass.data`); all I/O async, no blocking calls in
  the event loop.
- Entities: unique IDs, `has_entity_name`, device registry entries with real
  identifiers, availability handling, entity categories; diagnostics support.
- Translations: runtime translations come from `translations/en.json`; do not
  use `strings.json` or `[%key:...]` placeholders — both are Home Assistant
  core build-time features that do not work in custom components.
- Quality scale: the baseline is bronze — `config-flow`,
  `config-flow-test-coverage`, `unique-config-entry`, `test-before-setup`,
  `test-before-configure`, `runtime-data`, `entity-unique-id`,
  `has-entity-name`, `entity-event-setup`, `appropriate-polling`,
  `common-modules`, `dependency-transparency`, `brands`, and the `docs-*`
  documentation rules; grow toward silver next. The target tier is silver.

## 6. Spec-driven development (SDD)

- Every feature starts with a spec in `specs/NNNN-slug.md` (zero-padded
  number, short slug). Status lifecycle: `draft → approved → implemented →
  superseded`.
- Implementation without an `approved` spec is forbidden. Specs marked
  "implementation pending research" must not be implemented until they move to
  `approved`.
- Spec template: Summary / Motivation / Requirements (MUST/SHOULD) / Design /
  API / Test plan / Acceptance criteria / Out of scope / Status.
- Moving a spec from `draft` to `approved` is a reviewable change (PR or a
  recorded decision in the conversation).
- Specs for user-visible features must account for §4/§5: config-flow steps,
  unique IDs, translations, release/versioning impact.

## 7. Test-driven development (TDD)

- Tests are written first and must fail before the implementation exists.
- The integration consumes the real `pydmvl` library through an
  `httpx.MockTransport`; there is no HTTP mocking above the library boundary.
  Fixtures are synthetic.
- `config_flow.py` must have full test coverage (bronze rule).
- A merge requires a fully green run of the gate commands (§3).

## 8. Git process

- Default branch: `master`. Direct commits to `master` are forbidden (the
  initial scaffold import is the only exception).
- One feature = one branch `feat/NNNN-slug` containing the spec, the tests, and
  the implementation together.
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`,
  `test:`, `chore:`, `refactor:`).
- Merge into `master` only after the review gate (§9), squash-merge, then
  delete the feature branch.
- After merging runtime changes to `master`: tag `vX.Y.Z` matching the
  manifest `version` and publish a GitHub Release (§4).

## 9. Review gate (mandatory)

A feature branch may merge into `master` only when both hold:

1. A full local run is green (§3/§7).
2. A skeptic review returns no `BLOCKING` findings. Always launch it in the
   **background** (`Task` with `background: true`) so work can continue while it
   runs; handle the verdict when it arrives. Invoke the group's `skeptic`
   subagent (Task tool; its definition is maintained in the non-public group
   workspace, not in this public repository) with a prompt such as:

   > Review branch `feat/NNNN-slug` against its spec `specs/NNNN-slug.md`
   > (diff base: `master`). Follow the group skeptic checklist and answer in
   > the verdict format (`BLOCKING: ...` / `NITS: ...` / `APPROVED`).

`BLOCKING` findings forbid the merge; fix and re-review.

## 10. Secrets and safety

- Your own account and property data are confidential: never include them in
  this public repository — in code, docs, examples, fixtures, or commit
  history. This covers logins, passwords, tokens (including the password hash
  sent by the API), full names, addresses, personal account numbers, object and
  payment identifiers, and receipt links. Use synthetic placeholders
  (`<account>`, `<password>`); real values live only in Home Assistant storage
  or gitignored `*.local.json` files.
- The integration never performs actions on the account beyond periodic
  read-only polling. Any account-changing action would require an explicit
  user confirmation in the conversation and a separate spec.
- TLS verification is a user option. Desktop clients of this service may need
  to disable it because the service serves an incomplete certificate chain;
  the option defaults to disabled and the rationale is documented in the user
  documentation. Never enable credential logging.

## 11. Publication policy (public repository)

- Do not copy text or material from non-public sources into this repo.
- Public documentation is an English description of observed service behavior.
  Cite only this repository's own specs; do not name non-public sources, and do
  not state or claim how the API was determined.
- Keep the disclaimers in place (unofficial, not affiliated with the service
  operator, your own account only).

## 12. Release runbook (new versions)

Release only for runtime changes; documentation-only changes ship without a
release.

1. Bump `manifest.json` `version` (SemVer) as part of the feature branch; it
   must equal the release tag.
2. Feature branch `feat/NNNN-slug` (spec + tests + version bump), gate
   (§3/§7), skeptic, squash-merge into `master`.
3. Push `master`, then create a GitHub Release `vX.Y.Z` matching the manifest
   `version`.
4. Changing the library version means updating the `manifest.json`
   `requirements` pin **and** `requirements_dev.txt`, plus the spec. Both pins
   use the exact PyPI release (`pydmvl==X.Y.Z`).

## 13. References

- Specs: `specs/` (`0001-config-flow` is the first deliverable).
- Dependency strategy: `pydmvl` is consumed from PyPI, pinned with the exact
  release in both `manifest.json` and `requirements_dev.txt`.
- Versioning: SemVer, `0.x` while the integration is unstable; manifest
  `version` and the release tag move together (§4).
- HACS publishing rules: https://hacs.xyz/docs/publish/start,
  https://hacs.xyz/docs/publish/integration,
  https://hacs.xyz/docs/publish/include
- Home Assistant integration development:
  https://developers.home-assistant.io/docs/creating_integration_file_structure,
  https://developers.home-assistant.io/docs/creating_integration_manifest,
  https://developers.home-assistant.io/docs/core/integration_quality_scale,
  https://developers.home-assistant.io/docs/core/integration/config_flow
