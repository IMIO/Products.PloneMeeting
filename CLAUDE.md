# CLAUDE.md — Products.PloneMeeting

## What is this project?

Products.PloneMeeting is a Plone-based application for managing official meetings (deliberations) in Belgian local authorities. It handles the full lifecycle: creating agenda items, submitting them for review, building meeting agendas, recording decisions, managing advices from organizations, voting, and generating official documents.

It is part of the **iMio** ecosystem — a suite of open-source tools for Belgian municipalities — and is commercially known as **iA.Delib**.

## Tech stack

- **Python 2.7** on **Plone 4.3** (Zope 2)
- Content types: mix of legacy **Archetypes** and modern **Dexterity** (see migration status below)
- Build system: **zc.buildout** (extends `buildout.pm/communes-dev.cfg` from IMIO)
- Templates: **TAL/TALES** page templates (`.pt`)
- Frontend: jQuery-based with **CKEditor** for rich text
- Document generation: **appy** (POD templates)
- Search/dashboard: **eea.facetednavigation** + `collective.eeafaceted.dashboard`
- i18n: `zope.i18nmessageid` — translations live in the separate `imio.pm.locales` package
- CI: Jenkins (`Jenkinsfile`) with Docker pipeline

## Migration roadmap

The long-term goal is to **migrate to Plone 6**. As part of this effort, all Archetypes content types are being progressively migrated to Dexterity. **Write Python 3 compatible code whenever possible** (use `from __future__ import` imports, avoid `dict.has_key()`, use `six` for compatibility, etc.).

### AT-to-DX migration status

**Already migrated to Dexterity (ignore AT patterns for these):**

| Type | Since |
|------|-------|
| `Meeting` | v4.2 (2021) |
| `MeetingAdvice` (`meetingadvice`) | v4.0 (2014) |
| `MeetingCategory` (`meetingcategory`) | v4.1.10 (2015) |
| `annex`, `annexDecision` | Already DX |
| `ContentCategory`, `ContentCategoryGroup`, `ContentSubcategory` | Already DX |
| `ItemAnnexContentCategory`, `ItemAnnexContentSubcategory` | Already DX |
| `DashboardPODTemplate`, `ConfigurablePODTemplate`, `StyleTemplate` | Already DX |
| `directory`, `organization`, `person`, `held_position` | Already DX (collective.contact) |

**Still Archetypes (migration pending):**

| Type | File |
|------|------|
| `MeetingConfig` | `MeetingConfig.py` |
| `MeetingItem` | `MeetingItem.py` |
| `MeetingItemTemplate` | Subtype of MeetingItem |
| `MeetingItemRecurring` | Subtype of MeetingItem |
| `ToolPloneMeeting` | `ToolPloneMeeting.py` |

## Repository layout

```
src/Products/PloneMeeting/
  MeetingConfig.py        # Meeting type configuration (Archetypes, ~8k lines)
  MeetingItem.py          # Agenda item (Archetypes, ~8k lines — migration to DX pending)
  Meeting.py              # Meeting object (Dexterity, ~2k lines)
  ToolPloneMeeting.py     # Portal tool — global configuration singleton
  config.py               # Constants, permissions, project name
  interfaces.py           # Marker interfaces, event interfaces, browser layer
  utils.py                # Utility functions
  vocabularies.py         # Zope vocabulary factories
  adapters.py             # Adapter implementations
  events.py               # Event handlers (workflow transitions, object lifecycle)
  indexes.py              # Catalog index definitions
  columns.py              # Faceted dashboard column definitions
  content/                # Dexterity content types (advice, categories, etc.)
  browser/                # Browser views, viewlets, portlets, batch actions
    views.py              # Main views (~128KB)
    overrides.py          # UI overrides (~80KB)
    templates/            # 60+ .pt templates
  behaviors/              # Dexterity behaviors
  widgets/                # Custom form widgets (PMCheckBoxWidget, etc.)
  workflows/              # DCWorkflow definitions (Python-based)
  migrations/             # Upgrade steps (migrate_to_4100 through 4217+)
  profiles/               # GenericSetup profiles (default + testing)
  skins/                  # Legacy Plone skins (templates, JS, CSS)
  filters/                # CSS transform filters (content anonymization)
  external/               # External service integrations (iA.Vision)
  documentgenerator/      # POD template generation support
  faceted_conf/           # Faceted navigation XML configs
  ftw_labels/             # Label management integration
  ckeditor/               # CKEditor plugin customizations
  tests/                  # Test suite (20+ test modules)
  model/                  # UML model and adaptations
```

## Key domain objects

| Object | Type | Description |
|--------|------|-------------|
| `MeetingConfig` | Archetypes | Configures a meeting type (council, college, etc.) — workflows, categories, permissions |
| `Meeting` | Dexterity | A meeting instance with date, attendees, signatories, agenda |
| `MeetingItem` | Archetypes | An agenda point — goes through review workflow, collects advices, gets decided (DX migration pending) |
| `MeetingAdvice` | Dexterity | An advice (opinion) given by an organization on an item |
| `ToolPloneMeeting` | OFS | Portal tool managing global configuration and all MeetingConfigs |

## Building & running

This is a buildout-based project. From the buildout root (`pm42_dev/`):

```bash
bin/buildout              # Build/install
bin/instance fg           # Run Plone in foreground
```

## Running tests

```bash
# From the buildout root (pm42_dev/)
bin/test -s Products.PloneMeeting                    # All tests
bin/test -s Products.PloneMeeting -t testMeetingItem # Single test module
bin/test -s Products.PloneMeeting -t test_method_name # Single test method
```

Tests use `unittest` + `plone.app.testing`. The base test class is `PloneMeetingTestCase` (`tests/PloneMeetingTestCase.py`). The test profile (`PM_TESTING_PROFILE_FUNCTIONAL`) sets up a full Plone site with sample meeting configurations.

## Code style & conventions

- **Encoding header**: `# -*- coding: utf-8 -*-` on every `.py` file
- **License header**: GPL block at the top of every file
- **Imports**: single-line, alphabetically sorted (`isort` with `force_single_line = True`)
- **Line length**: 200 characters max (configured in `setup.cfg`)
- **Complexity**: max cyclomatic complexity 15 (`flake8`)
- **Naming**: `PascalCase` for classes, `snake_case` for functions, `UPPER_SNAKE_CASE` for constants. Private methods prefixed with `_`
- **Security**: `AccessControl.ClassSecurityInfo` declarations on class methods
- **i18n**: `from Products.PloneMeeting.config import PMMessageFactory as _` — wrap translatable strings with `_()`

## Commit message style

Short imperative sentence. Reference issues with `#NNN` (GitHub PR) or `#PROJECT-NNN` (external tracker like `#SUP-50375`, `#VIS-2654`). Examples:

```
Fixed actions_panel cache issue for reviewers (#313)
Added new datagrid field MeetingConfig.cssTransforms (#314)
```

## Changelog

Update `CHANGES.rst` for every user-facing change. Format:

```rst
- Description of change with `backtick-quoted` code references.
  [author_shortname]
```

## Migrations

Upgrade steps live in `migrations/migrate_to_XXXX.py`. Each file corresponds to a profile version. Register new migrations in the appropriate ZCML. The migration base class and helpers are in `migrations/__init__.py`.

## Important patterns

- **Workflow adaptations** (`MeetingConfig.wfAdaptations`): dynamically modify workflows at runtime
- **TAL expressions**: used extensively in `MeetingConfig` fields to configure behavior (evaluated via `_evaluateExpression` in utils)
- **safe_utils**: functions exposed to restricted Python/TAL — adding new ones requires registration
- **Faceted collections**: dashboard views are built with `DashboardCollection` objects and faceted navigation configs
- **Event-driven**: heavy use of Zope event subscribers for side effects on transitions and edits (`events.py`)
