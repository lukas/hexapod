# Notes for agents working in this repo

## Catalog and revision discipline

Start with MCP `list_catalog` / `get_catalog_item`, or `buildviz catalog list`.
The catalog organizes persistent robots, assemblies, studies, and saved views;
legacy build IDs, branches, and versions remain their storage addresses.
Reuse the existing catalog identity before creating another source.

- Use `create_view` for an inspection selection of unchanged geometry. Pin its
  source branch and revision; never create a robot or experimental branch just
  to show a subassembly. An assembly can also select parts from an exact robot
  revision without copying geometry.
- Use `publish_revision` for geometry changes. Keep the existing robot or
  component identity, or create a study with an explicit parent for an
  alternative. Every new revision requires one or two sentences explaining
  what changed and why; generic messages such as "update" are rejected.
- Keep current CAD separate from `asBuilt`. Only record installed hardware
  from evidence, and keep as-built and milestone references pinned. Do not
  infer physical installation from the latest scene or its version number.
- Preserve old URLs, branches, revision descriptions, and original timestamps.
  Mark reconstructed history descriptions retrospective. Archive obsolete
  catalog entries rather than deleting their source histories.
- Before publishing, read the exact source version's feedback with
  `get_version_feedback` / `buildviz feedback`. Supply `reason` / `--reason`
  explaining WHY the revision is needed, separately from WHAT changed.
- Record failures, user-reported issues, observations and hypotheses against
  the version where they occurred using `record_version_feedback`. Return after
  testing to append validation or an evidence-backed resolution linking the
  original issue and tested successor. A newer version is not proof of a fix.

See `HEXAPOD_CATALOG.md` for the initial robot mapping, its known uncertainty,
and the repeatable metadata migration.

## Python: always use uv

All Python in this repo runs through [uv](https://docs.astral.sh/uv/) — never
call `python3`, `pip`, or hand-rolled virtualenvs directly.

- **Run scripts** with `uv run <script.py>`. Every script carries PEP 723
  inline metadata (the `# /// script` block at the top) declaring its Python
  version and dependencies, so `uv run` resolves everything on the fly — no
  venv setup, no `pip install`.
- **Add a dependency** to a script by editing its `# /// script` block (or
  `uv add --script <script.py> <package>`), not by installing into some
  environment.
- **New scripts** must start with the `#!/usr/bin/env -S uv run --script`
  shebang plus a `# /// script` metadata block. Copy the header from
  `deploy/coreweave/migrate_local_builds.py` (stdlib-only) or
  `scripts/export_hexapod_prototype.py` (with dependencies).
- One-off snippets in a shell should use `uv run python -c '...'` rather than
  `python3 -c '...'`.

Everything else in this repo is Node/TypeScript — use `npm` / `npx` for that
as usual (see README.md and BUILDVIZ_LLM_INTERFACE.md).
