---
title: Projects
description: Ignition projects kept as files, with tested scripts and clean diffs.
---

Each folder in `projects/` is one Ignition project. `src/` holds exactly the files the gateway and the Designer read and write, so the repository is the project.

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
- **Strings.** Use `.format()`; Jython 2.7 has no f-strings.

## Checks

```sh
cd projects
uv sync
uv run ruff format --check . && uv run ruff check .
uv run pyright
uv run pytest
```

`conftest.py` registers mocks for the `system.*` modules, so scripts import under pytest exactly as they do in the gateway.

## The resource sanitiser

Every Designer save rewrites a resource's `lastModification` (who and when) and its `lastModificationSignature`, and may list a `thumbnail.png`. None of it changes what the resource does, but it turns every save into a diff and every merge into a conflict.

`scripts/sanitise.py` rewrites only those fields to fixed values and leaves the rest of the file byte for byte:

| Field | Becomes |
| --- | --- |
| `actor` | `"system"` |
| `timestamp` | `"2025-01-01T00:00:00Z"` |
| `lastModificationSignature` | a fixed value |
| `"thumbnail.png"` in `files` | removed |

Ignition accepts the fixed values and rewrites them on its next save. `scripts/setup-git.sh` (or `setup-git.ps1`) enables it as a git clean filter, so files are sanitised as they are staged. You can also run it directly:

```sh
uv run --no-project scripts/sanitise.py --check FILE...   # list files that need it
uv run --no-project scripts/sanitise.py --fix FILE...     # rewrite in place
```

## UDT definitions

The `library` project keeps its UDT definitions as files in `src/udts/<folder>/<name>.json`, so they ship in the gateway image with everything else. `udts/index.json` lists them in import order: a type must come after every type it nests.

The `library.udts` scripts import each definition into `[<provider>]_types_/<folder>`, overwriting what is there, so the files are the source of truth and the gateway converges on them. `exportAll` writes the gateway's definitions back to the files, normalised (sorted keys, four-space indent), so a Designer change shows up as a clean diff.

The equipment types (`blower`, `level`, `mixer`, `pump`) match the asset kinds in the [database](../database/).
