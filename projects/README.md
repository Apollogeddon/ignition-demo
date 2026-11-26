# Projects

The Ignition projects, kept as files, and the Python tooling that checks their scripts. Each folder is one Ignition project; its `src/` holds exactly the files the gateway and the Designer read and write.

| Project | Role |
| --- | --- |
| `library` | Inheritable: shared scripts (`library.*`), style classes, views and UDT definitions |
| `project` | The application; `project.json` names `library` as its parent |

## The demo application

`project` is a small Perspective application over the [database](../database/README.md)'s assets, at `/data/perspective/client/project`. A docked header (`Shell/Header`) links its five pages and shows the time and the gateway's Ignition release:

| Page | View | Shows |
| --- | --- | --- |
| `/` Overview | `Page/Overview` | KPI cards (assets, online, offline, pumped flow, last event), pumped flow per area over the last 72 hours (Time Series Chart), assets per area (Pie Chart), a card per area, and the selected area's assets |
| `/plant` Plant | `Page/Plant` | A live process schematic from the intake well to the transfer pumps: tanks, pumps, blowers, the contact tank and its valve, joined by pipes that colour while their stage flows; each symbol opens the equipment popup (`Popup/Equipment`) |
| `/analytics` Analytics | `Page/Analytics` | Gauges for availability, intake against capacity and reservoir level, the plant's output over the last day, hourly delivered volume against reservoir level (XY Chart), a day-by-hour heatmap of intake flow, and each area's load |
| `/assets` Assets | `Page/Assets` | Every asset with its status and latest reading; the selected asset's trend, recent events, and Acknowledge and Log note actions |
| `/events` Events | `Page/Events` | Counts by kind and the event log, newest first |

The views use only built-in components, styled by the `library` project's style classes (`Card`, `Kpi/*`, `Pill/*`, `Shell/*`, ...); the `Cells/Pill` view draws a status or event kind as a coloured pill inside tables. Every binding is one call into a script module, which shapes the named queries' rows and is unit-tested:

| Module | Does |
| --- | --- |
| `project.overview` | The Overview's KPIs, area cards, pie data and flow trend |
| `project.plant` | The schematic's symbol states, readings and pipe colours, and the equipment popup |
| `project.analytics` | The Analytics page's gauges, chart, heatmap and area load |
| `project.assets` | The asset table and the asset detail panel |
| `project.events` | Validates and records events, and lists them |

The message flows:

- **Select an area.** An area card on the Overview sends the `areaSelected` page message (`system.perspective.sendMessage`); the area panel's handler sets the view's selected area and refreshes its table.
- **Select an asset.** A row of the Assets table sends `assetSelected`; the detail panel's handler loads that asset.
- **Acknowledge or log a note.** The detail panel's buttons call `project.events.send`, which asks the `recordEvent` gateway message handler (`system.util.sendRequest`). The handler, `ignition/message/recordEvent/handleMessage.py`, calls `project.events.handle`: it validates the request, inserts the row with the `events/insert` named query and answers `{ok, text}`, which the panel shows. The panel then refreshes and sends the `eventRecorded` session message, which refreshes the Events and Plant pages in any other tab of the session.
- **Open equipment.** A symbol on the Plant page opens the equipment popup, whose Acknowledge button records an event the same way.

The named queries (`assets/list`, `assets/status`, `readings/flowByArea`, `readings/hourly`, `readings/asset`, `events/list`, `events/insert`) are plain SQL on the `demo` connection, the same on 8.1 and 8.3. The data comes from `database/init`, which PostgreSQL only runs when the database volume is created: after pulling a change to it, reset the develop stack with `docker compose -f develop/docker-compose.yml down -v`.

## How the views are built

Every page follows the same pattern, so a new one starts from a copy of another:

- **Pages and docks.** `com.inductiveautomation.perspective/page-config/config.json` maps each URL to a page view and declares one shared top dock, `Shell/Header`, which every page shows. Its `ia.navigation.link`s take the `Shell/NavActive` class from an expression on `{page.props.path}`.
- **Custom properties fetch.** A page view's root is an `ia.container.flex` with the `Layout/Page` class, its sections nested flex containers with the `Card` class. The page's data sits in view custom properties, such as `view.custom.plant`, each bound to an expression that ticks (`now(15000)`) with a script transform that makes one call: `return project.plant.getPlant()`. Components only bind to parts of them, with property and expression bindings such as `{view.custom.plant.slots.intake1.state}`.
- **Script modules and named queries.** Each page has a module in `ignition/script-python/project/<module>/code.py`. It runs named queries through `library.db.namedQuery` and shapes the rows into plain dictionaries and lists, down to the text, symbol states and colours the view shows, so the view holds no logic and the shaping is unit-tested in `project/tests` with the `system.*` mocks in `conftest.py`. A named query is `ignition/named-query/<group>/<name>/query.sql` plus its `resource.json`, on the `demo` connection; the readings queries cover the 72 hours up to the latest reading.
- **Style classes.** Components name classes from the `library` project (`Card`, `Kpi/*`, `Section/*`, `Pill/*`, `Text/*`, `Plant/*`, `Heat/*`, `Progress/*`) rather than carry styles; inline styles are kept to layout gaps and colours that come from data, such as an area's swatch or a heatmap cell. The gateway drops what a class can't hold as a plain property (CSS variables, `filter`, the `border` shorthand), so `library`'s `stylesheet.css`, Perspective's advanced stylesheet, holds the rules that need them: the symbols' running colours and their hover glow, on `.psc-Plant\/Equipment`.
- **Small screens.** A class can't restyle its children, so the stylesheet's media queries also hold the layout below desktop width. They key on layout classes that carry no style of their own (`Layout/Kpis`, `Layout/Row`, `Layout/ChartRow`, `Layout/Gauges`, `Shell/Links`, `Plant/Canvas`). Up to 1100px, the header's clock is hidden. Up to 640px:
  - rows stack, and KPI cards go two to a row;
  - gauges take the full width, and heatmap cells drop their numbers;
  - the header keeps only the page links.

  The Plant schematic keeps its size and scrolls sideways once it doesn't fit. A container's position is an inline style, so these rules need `!important`.
- **Repeated cells.** A Flex Repeater draws one small view per item of a list: `Cells/HeatRow` and `Cells/HeatCell` make the heatmap, `Cells/AreaLoad` an area's load bar. Tables draw `Cells/Pill` in their status and kind columns.
- **Messages.** View message handlers sit on a component (`scripts.messageHandlers`). `areaSelected` and `assetSelected` are page-scoped: a card or table row on the page sends one with `system.perspective.sendMessage` and a panel on the same page handles it. `eventRecorded` is session-scoped, so recording an event refreshes the Events and Plant pages in every tab of the session. Writes go through the gateway: `project.events.send` calls `system.util.sendRequest`, which the `recordEvent` gateway message handler answers.
- **Popups.** A schematic symbol's `onClick` calls `project.plant.openEquipment`, which opens the `Popup/Equipment` view with `system.perspective.openPopup`, passing `assetId` as a view parameter. The popup binds its data to that parameter, acknowledges through `recordEvent`, and closes itself with `system.perspective.closePopup`.
- **Ignition 8.1.** Views, style classes, the stylesheet, named queries and scripts are the same files on both lines, and every component here exists in Perspective on 8.1.55 and 8.3.10. Only the gateway events and message handlers differ: 8.1 keeps them in `ignition/event-scripts/data.bin`, which `scripts/generate-event-scripts.sh` builds from the 8.3 files, so a handler is written once.

The components each page uses, beyond flex containers, labels and icons:

| View | Components |
| --- | --- |
| `Page/Overview` | Time Series Chart, Pie Chart, Table, Button |
| `Page/Plant` | Coordinate Container in fixed mode, with its pipes; Cylindrical Tank; the Pump, Motor, Vessel, Valve and Sensor symbols |
| `Popup/Equipment` | Gauge, Sparkline, Button |
| `Page/Analytics` | Simple Gauge, LED Display, XY Chart (columns and a line on two axes), Flex Repeater, Embedded View, Progress Bar |
| `Page/Assets` | Table, Time Series Chart, Text Area, Button |
| `Page/Events` | Table |

## Script conventions

Gateway scripts run on Jython 2.7, while the tooling here runs them under Python with the [Ignition API stubs](https://pypi.org/project/ignition-api-stubs/):

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
- Format strings with `.format()`: Jython 2.7 has no f-strings. A database or Perspective string is unicode there, which `"{}".format()` encodes as ASCII: join such values with `+` and keep them out of log lines.

The [Projects](../webpage/src/content/docs/components/projects.md) docs page covers the conventions in full, along with the library modules, gateway events, message handlers and UDT definitions.

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

- `ruff.toml` extends forgepy's managed Jython base in `.forgepy/ruff-jython.toml`, selects every rule, and turns off the ones that don't fit Jython scripts or Ignition's naming conventions. Scripts are indented with tabs, as the Designer writes them.
- `pyrightconfig.json` extends `.forgepy/pyrightconfig.json`, adds the script folders to the import path, and defines `MYPY` as true so basedpyright reads the type-only imports. Its `stubPath`, `stubs/`, types the gateway internals `library.gateway81` uses that the Ignition API stubs leave out.
- `uv run forgepy sync` refreshes the files in `.forgepy/`.
- `conftest.py` registers mocks for the `system.*` modules, so scripts import under pytest exactly as they do in the gateway.

Lefthook runs ruff on staged Python files, and the compatibility check whenever a script under `*/src/` changes.

## Editing in the Designer

Start the develop stack (see [`develop/`](../develop/README.md)), which mounts each project's `src/` into the gateway, and edit in the Designer. Changes land straight in these folders. `scripts/setup-git.sh` makes git strip the Designer's noise from `resource.json` files when they are staged.
