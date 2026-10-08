# Projects

Each folder is one Ignition project; `src/` holds exactly the files the gateway and the Designer read and write.

| Project | Role |
| --- | --- |
| `library` | Inheritable: shared scripts (`library.*`), style classes, views |
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
- Strings use `.format()` (no f-strings in Jython 2.7).

## Checks

```sh
cd projects
uv sync
uv run ruff format --check . && uv run ruff check .
uv run pyright
uv run pytest
```

`conftest.py` registers mocks for the `system.*` modules, so scripts import under pytest exactly as they do in the gateway.

## Editing in the Designer

Start the develop stack (`develop/`), which mounts `src/` of each project into the gateway, and edit in the Designer. Changes land straight in these folders; `scripts/setup-git.sh` makes git strip the Designer's noise from `resource.json` files when they are staged.
