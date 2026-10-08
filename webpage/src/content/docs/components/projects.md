---
title: Projects
description: Ignition projects kept as files, with tested scripts and clean diffs.
---

Each folder in `projects/` is one Ignition project, and this page covers how they are kept as files and how their scripts are checked. `src/` holds exactly the files the gateway and the Designer read and write, so the repository is the project.

| Project | Role |
| --- | --- |
| `library` | Inheritable: shared scripts (`library.*`), style classes, views and UDT definitions |
| `project` | The application; `project.json` names `library` as its parent |

## Script conventions

Gateway scripts run on Jython 2.7, while the tooling runs them under Python 3.12 with the [Ignition API stubs](https://pypi.org/project/ignition-api-stubs/). A few conventions keep both happy:

- **Packages.** Every importable script folder has an `__init__.py` re-exporting its `code.py` (`from .code import *`), and its `resource.json` lists both files. Ignition imports the package through it the same way CPython does.
- **Type comments.** Types use comments, not annotations, and type-only imports sit under `MYPY = False` / `if MYPY:` so the gateway never runs them:

  ```python
  MYPY = False
  if MYPY:
  	from typing import Any, Dict


  def summarise(
  	rows,  # type: Iterable[Dict[str, Any]]
  ):
  	# type: (...) -> List[Dict[str, Any]]
  ```

- **Imports and logging.** Import gateway functions directly (`from system.db import execQuery`) and name loggers `demo.<project>.<module>`. Log routine progress at DEBUG and keep INFO for events worth noticing.
- **Strings.** Use `.format()`; Jython 2.7 has no f-strings. Avoid `u""` literals: the formatter removes the prefix, and on Jython that turns a unicode string into a byte string. Build non-ASCII text at run time (`library.format` does it for its em dash) and compare against `STRING_TYPES` rather than `str` (`library.seed`).
- **Both versions.** The checks run against the 8.1 and the 8.3 API stubs. Where the versions differ, a library module chooses at run time: `library.db.namedQuery` runs `execQuery` on 8.3 and `runNamedQuery` on 8.1.

## Checks

```sh
cd projects
uv sync
uv run ruff format --check . && uv run ruff check .
uv run basedpyright
uv run poe compat
uv run pytest
```

`uv sync` installs the 8.3 API stubs by default. To run the tests against the 8.1 stubs as well, use a second environment (CI runs every check against both):

```sh
UV_PROJECT_ENVIRONMENT=.venv-81 uv sync --no-default-groups --group dev --group ignition81
UV_PROJECT_ENVIRONMENT=.venv-81 uv run --no-sync pytest
```

The checks are also [poe](https://poethepoet.natn.io/) tasks, run with `uv run poe <task>`:

| Task | Runs |
| --- | --- |
| `format` | `ruff format .` |
| `lint` | `ruff check --fix .`, then `ruff format .` |
| `type` | `basedpyright` |
| `compat` | vermin and `forgepy check-jython`: the scripts must stay valid Jython 2.7 |
| `test` | `pytest`, with coverage |
| `sync-check` | `forgepy sync --check`: fails if the configs in `.forgepy/` are out of date |
| `security` | `osv-scanner scan -r .` (needs OSV-Scanner installed) |

## Tooling

The tooling comes from [forgepy](https://github.com/apollogeddon/forgepy)'s `--jython` setup:

- `ruff.toml` extends forgepy's managed Jython base in `.forgepy/ruff-jython.toml`, selects every rule, and turns off the ones that don't fit Jython scripts or Ignition's naming conventions. Scripts are indented with tabs, as the Designer writes them; the tests target Python 3.12.
- `pyrightconfig.json` extends `.forgepy/pyrightconfig.json`, adds the script folders to the import path, and defines `MYPY` as true so basedpyright reads the type-only imports.
- `uv run forgepy sync` refreshes the files in `.forgepy/`; CI fails if they are out of date.
- `conftest.py` registers mocks for the `system.*` modules, so scripts import under pytest exactly as they do in the gateway.

Lefthook runs ruff on staged Python files, and the compatibility check whenever a script under `*/src/` changes.

## The resource sanitiser

Every Designer save rewrites a resource's `lastModification` (who and when) and its `lastModificationSignature`, and may list a `thumbnail.png`; an 8.1 gateway reading projects from disk rewrites them too, reordering keys and dropping the final newline. None of it changes what the resource does, but it turns every save into a diff and every merge into a conflict.

`scripts/sanitise.py` writes every `resource.json` in one canonical form:

| Field | Becomes |
| --- | --- |
| `actor` | `"system"` |
| `timestamp` | `"2025-01-01T00:00:00Z"` |
| `lastModificationSignature` | a fixed value |
| `"thumbnail.png"` in `files` | removed |
| layout | sorted keys, two-space indent, final newline |

Ignition accepts the fixed values and rewrites them on its next save; with the filter, those rewrites never show up as changes. `scripts/setup-git.sh` (or `setup-git.ps1`) enables it as a git clean filter, so files are sanitised as they are staged. You can also run it directly:

```sh
uv run --no-project scripts/sanitise.py --check FILE...   # list files that need it
uv run --no-project scripts/sanitise.py --fix FILE...     # rewrite in place
```

## Library modules

| Module | Purpose |
| --- | --- |
| `library.data` | Dataset rows as dictionaries |
| `library.db` | Named queries on both versions |
| `library.format` | Display formatting |
| `library.log` | Consistently named loggers |
| `library.udts` | UDT definitions kept as files: import and export |
| `library.seed` | Applies the 8.1 seed spec (`gateway/seed/seed.json`) |
| `library.gateway81` | The 8.1 configuration store `library.seed` writes through |

## Gateway events

`project`'s gateway events are one line each, calling `project.gateway`, where the work is tested:

| Event | Does |
| --- | --- |
| Startup | Applies the seed (8.1), imports the UDT definitions, then creates or updates a UDT instance per asset in the background, retrying while the database comes up |
| Project update | Exports the UDT definitions back to the files, so a UDT edit made in the Designer becomes a diff (save the project after editing tags) |

The events are written once, in 8.3's format (`ignition/startup/onStartup.py`, `ignition/update/onUpdate.py`). 8.1 stores gateway events as a binary `ignition/event-scripts/data.bin`, so `scripts/generate-event-scripts.sh` builds it from those files with Ignition 8.1's own serializer (in its Docker image), byte for byte reproducibly; CI fails if it is out of date. Run it after changing an event script.

## UDT definitions

The `library` project keeps its UDT definitions as files in `src/udts/<folder>/<name>.json`, so they ship in the gateway image with everything else. `udts/index.json` lists them in import order: a type must come after every type it nests.

The `library.udts` scripts import each definition into `[<provider>]_types_/<folder>`, overwriting what is there, so the files are the source of truth and the gateway converges on them. `exportAll` writes the gateway's definitions back to the files in a canonical form (sorted keys and members, four-space indent, without the bare member placeholders 8.1 adds to nested instances), so a Designer change shows up as a clean diff and 8.1 and 8.3 export the same file.

The equipment types (`blower`, `level`, `mixer`, `pump`) match the asset kinds in the [database](../database/).
