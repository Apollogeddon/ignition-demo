# Projects

The Ignition projects, kept as files, and the Python tooling that checks their scripts. Each folder is one Ignition project; its `src/` holds exactly the files the gateway and the Designer read and write.

| Project | Role |
| --- | --- |
| `library` | Inheritable: shared scripts (`library.*`), style classes, views and UDT definitions |
| `project` | The application; `project.json` names `library` as its parent |

## Script conventions

Gateway scripts run on Jython 2.7, while the tooling here runs them under Python 3.12 with the [Ignition API stubs](https://pypi.org/project/ignition-api-stubs/):

- Every importable script folder has an `__init__.py` re-exporting its `code.py` (`from .code import *`), and its `resource.json` lists both files. Ignition imports the package through it the same way CPython does.
- Types use comments, not annotations, and type-only imports sit under `MYPY = False` / `if MYPY:` so the gateway never runs them:

  ```python
  MYPY = False
  if MYPY:
  	from typing import Any, Dict


  def summarise(
  	rows,  # type: Iterable[Dict[str, Any]]
  ):
  	# type: (...) -> List[Dict[str, Any]]
  ```

- Import gateway functions directly (`from system.db import execQuery`) and name loggers `demo.<project>.<module>`. Log routine progress at DEBUG and keep INFO for events worth noticing.
- Format strings with `.format()`: Jython 2.7 has no f-strings.

The [Projects](../webpage/src/content/docs/components/projects.md) docs page covers the conventions in full, along with the library modules, gateway events and UDT definitions.

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

The same checks are available as [poe](https://poethepoet.natn.io/) tasks (`uv run poe <task>`):

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
- `uv run forgepy sync` refreshes the files in `.forgepy/`.
- `conftest.py` registers mocks for the `system.*` modules, so scripts import under pytest exactly as they do in the gateway.

Lefthook runs ruff on staged Python files, and the compatibility check whenever a script under `*/src/` changes.

## Editing in the Designer

Start the develop stack (see [`develop/`](../develop/README.md)), which mounts each project's `src/` into the gateway, and edit in the Designer. Changes land straight in these folders. `scripts/setup-git.sh` makes git strip the Designer's noise from `resource.json` files when they are staged.
