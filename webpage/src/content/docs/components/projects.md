---
title: Projects
description: Ignition projects kept as files, with tested scripts and clean diffs.
---

Each folder in `projects/` is one Ignition project, and this page covers how they are kept as files and how their scripts are checked. `src/` holds exactly the files the gateway and the Designer read and write, so the repository is the project.

| Project | Role |
| --- | --- |
| `library` | Inheritable: shared scripts (`library.*`), style classes, views and UDT definitions |
| `project` | The application; `project.json` names `library` as its parent |

## The demo application

`project` is a small Perspective application over the [database](../database/)'s assets, at `/data/perspective/client/project`. A docked header (`Shell/Header`) links its six pages, with the active alarm count on Alarms, and shows the time and the gateway's Ignition release. Everything it shows is live: a gateway timer runs a model of the plant on the assets' tags (see [The live process](#the-live-process)):

| Page | View | Shows |
| --- | --- | --- |
| `/` Overview | `Page/Overview` | KPI cards (assets, online, offline, pumped flow, last event), pumped flow per area over the last 72 hours (Time Series Chart), assets per area (Pie Chart), a card per area, and the selected area's assets |
| `/plant` Plant | `Page/Plant` | A process schematic from the intake well to the transfer pumps: tanks, pumps, blowers, the contact tank and its valve, bound to the asset tags and joined by pipes that colour while their stage flows; each symbol opens the equipment popup (`Popup/Equipment`), with a live gauge and Start or Stop |
| `/analytics` Analytics | `Page/Analytics` | Gauges for availability, intake against capacity and reservoir level, the plant's output over the last day, hourly delivered volume against reservoir level (XY Chart), the tanks' level history over the last hour (tag history), a day-by-hour heatmap of intake flow, and each area's load |
| `/assets` Assets | `Page/Assets` | Every asset with its status and latest reading; the selected asset's trend, recent events, and Acknowledge and Log note actions |
| `/events` Events | `Page/Events` | Counts by kind and the event log, newest first |
| `/alarms` Alarms | `Page/Alarms` | Counts of active, unacknowledged and high-priority alarms, the Alarm Status Table (acknowledge here) and the Alarm Journal Table |

The views use only built-in components, styled by the `library` project's style classes (`Card`, `Kpi/*`, `Pill/*`, `Shell/*`, ...); the `Cells/Pill` view draws a status or event kind as a coloured pill inside tables. Every binding is one call into a script module, which shapes the named queries' rows and is unit-tested:

| Module | Does |
| --- | --- |
| `project.overview` | The Overview's KPIs, area cards, pie data and flow trend |
| `project.plant` | The schematic's symbol states, readings and pipe colours, and the equipment popup |
| `project.analytics` | The Analytics page's gauges, chart, heatmap and area load |
| `project.assets` | The asset table and the asset detail panel |
| `project.events` | Validates and records events, and lists them |
| `project.process` | The plant model the process timer runs on the tags, and the popup's Start and Stop |
| `project.alarms` | Counts the assets' alarms for the Alarms page and the header |

The message flows:

- **Select an area.** An area card on the Overview sends the `areaSelected` page message (`system.perspective.sendMessage`); the area panel's handler sets the view's selected area and refreshes its table.
- **Select an asset.** A row of the Assets table sends `assetSelected`; the detail panel's handler loads that asset.
- **Acknowledge or log a note.** The detail panel's buttons call `project.events.send`, which asks the `recordEvent` gateway message handler (`system.util.sendRequest`). The handler, `ignition/message/recordEvent/handleMessage.py`, calls `project.events.handle`: it validates the request, inserts the row with the `events/insert` named query and answers `{ok, text}`, which the panel shows. The panel then refreshes and sends the `eventRecorded` session message, which refreshes the Events and Plant pages in any other tab of the session.
- **Open equipment.** A symbol on the Plant page opens the equipment popup, whose Acknowledge button records an event the same way.

The named queries (`assets/list`, `assets/status`, `readings/flowByArea`, `readings/hourly`, `readings/asset`, `events/list`, `events/insert`) are plain SQL on the `demo` connection, the same on 8.1 and 8.3. The data comes from `database/init`, which PostgreSQL only runs when the database volume is created: after pulling a change to it, reset the develop stack with `docker compose -f develop/docker-compose.yml down -v`.

## The live process

The assets are UDT instances, `[default]Assets/<area>/<asset>`, which the startup event creates from the database's assets. Every equipment UDT (`library/src/udts`) has the same interface: `value`, the reading in the asset's unit, and for a pump, blower or mixer a `motor` (`running`, `fault`, `speed` and `cmdRun`, the operator's command) and `state`, an expression tag giving `running`, `stopped` or `faulted`.

- **The process timer.** The project's `process` gateway timer event (`ignition/timer/process`) calls `project.process.tick()` every five seconds. It reads every instance, steps the model (`step()`, pure and unit-tested) and writes the results:
  - the intake pumps draw from the well, harder the fuller it is, while the river refills it;
  - the outlet valve throttles as the reservoir fills, and the transfer pumps follow the network's daily demand;
  - a running motor trips now and then and is back in service 15 minutes later, unless an operator starts it sooner.
- **Records.** Each trip, reset, start and stop becomes a status event, and every five minutes each asset's reading is appended to `asset_reading`, so the charts over the seeded 72 hours keep growing.
- **Control.** The equipment popup's Start or Stop writes the motor's `cmdRun` (`project.process.command`); Start also clears a trip. The next tick applies it.
- **Alarms.** The UDTs carry them: a motor fault, and a tank's high (above 90%) and low (below 15%) level, each acknowledged by hand. The Alarms page shows them, and the `demo` alarm journal stores them in PostgreSQL.
- **History.** The `value` and `motor/running` members are stored by the `demo` SQL historian: 8.1 creates one for each database connection, and on 8.3 the [cluster's resources module](../cluster/) configures it. `library.history.averages` queries it on either line.

## How the views are built

Every page follows the same pattern, so a new one starts from a copy of another:

- **Pages and docks.** `com.inductiveautomation.perspective/page-config/config.json` maps each URL to a page view and declares one shared top dock, `Shell/Header`, which every page shows. Its `ia.navigation.link`s take the `Shell/NavActive` class from an expression on `{page.props.path}`.
- **Custom properties fetch.** A page view's root is an `ia.container.flex` with the `Layout/Page` class, its sections nested flex containers with the `Card` class. The page's data sits in view custom properties, such as `view.custom.plant`, each bound to an expression that ticks (`now(15000)`) with a script transform that makes one call: `return project.plant.getPlant()`. Components only bind to parts of them, with property and expression bindings such as `{view.custom.plant.slots.intake1.state}`.
- **Script modules and named queries.** Each page has a module in `ignition/script-python/project/<module>/code.py`. It runs named queries through `library.db.namedQuery` and shapes the rows into plain dictionaries and lists, down to the text, symbol states and colours the view shows, so the view holds no logic and the shaping is unit-tested in `project/tests` with the `system.*` mocks in `conftest.py`. A named query is `ignition/named-query/<group>/<name>/query.sql` plus its `resource.json`, on the `demo` connection; the readings queries cover the 72 hours up to the latest reading.
- **Style classes.** Components name classes from the `library` project (`Card`, `Kpi/*`, `Section/*`, `Pill/*`, `Text/*`, `Plant/*`, `Heat/*`, `Progress/*`) rather than carry styles; inline styles are kept to layout gaps and colours that come from data, such as an area's swatch or a heatmap cell. The gateway drops what a class can't hold as a plain property (CSS variables, `filter`, the `border` shorthand), so `library`'s `stylesheet.css`, Perspective's advanced stylesheet, holds the rules that need them: the symbols' running colours and their hover glow, on `.psc-Plant\/Equipment`.
- **Small screens.** A class can't restyle its children, so the stylesheet's media queries also hold the layout below desktop width. They key on layout classes that carry no style of their own (`Layout/Kpis`, `Layout/Row`, `Layout/ChartRow`, `Layout/CardHead`, `Layout/Gauges`, `Shell/Links`, `Plant/Canvas`, `Plant/GaugeRow`).
  - **Up to 1240px:** the Plant schematic's three stages wrap, scaled to 82%. It's one coordinate container per stage, with each pipe ending at its stage's edge, so on desktop the stages join into one diagram.
  - **Up to 1200px:** KPI rows wrap, four cards two by two and five three over two.
  - **Up to 1100px:** the header's clock is hidden, and heatmap cells drop their numbers.
  - **Up to 640px:**
    - rows stack, KPI cards go two to a row without icons, and a card's legend or button goes below its title;
    - gauges take the full width;
    - the schematic shows one stage per row;
    - the equipment popup fits the screen;
    - the header keeps only the page links.

  A container's position is an inline style, so these rules need `!important`.
- **Repeated cells.** A Flex Repeater draws one small view per item of a list: `Cells/HeatRow` and `Cells/HeatCell` make the heatmap, `Cells/AreaLoad` an area's load bar. Tables draw `Cells/Pill` in their status and kind columns.
- **Messages.** View message handlers sit on a component (`scripts.messageHandlers`). `areaSelected` and `assetSelected` are page-scoped: a card or table row on the page sends one with `system.perspective.sendMessage` and a panel on the same page handles it. `eventRecorded` is session-scoped, so recording an event refreshes the Events and Plant pages in every tab of the session. Writes go through the gateway: `project.events.send` calls `system.util.sendRequest`, which the `recordEvent` gateway message handler answers.
- **Tag bindings.** The schematic's symbols and tanks bind straight to their instance's `state` and `value` tags, so they change the moment the timer writes. The popup takes the instance's path as its `tagPath` parameter and binds its gauge, reading and state indirectly, as `{path}/value` with `path` bound to `{view.params.tagPath}`.
- **Popups.** A schematic symbol's `onClick` calls `project.plant.openEquipment`, which opens the `Popup/Equipment` view with `system.perspective.openPopup`, passing `assetId` and `tagPath` as view parameters. The popup loads the asset's trend and events by `assetId`, acknowledges through `recordEvent`, and closes itself with `system.perspective.closePopup`.
- **Ignition 8.1.** Views, style classes, the stylesheet, named queries and scripts are the same files on both lines, and every component here exists in Perspective on 8.1.55 and 8.3.10. Only the gateway events, the timer and the message handlers differ: 8.1 keeps them in `ignition/event-scripts/data.bin`, which `scripts/generate-event-scripts.sh` builds from the 8.3 files, so each is written once. Tag history is queried differently too (`system.historian` on 8.3, `system.tag.queryTagHistory` on 8.1), which `library.history` hides.

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

Gateway scripts run on Jython 2.7, while the tooling runs them under Python with the [Ignition API stubs](https://pypi.org/project/ignition-api-stubs/). A few conventions keep both happy:

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
- **Strings.** Use `.format()`; Jython 2.7 has no f-strings. Avoid `u""` literals: the formatter removes the prefix, and on Jython that turns a unicode string into a byte string. Build non-ASCII text at run time (`library.format` does it for its em dash) and compare against `STRING_TYPES` rather than `str` (`library.seed`). A database or Perspective string is unicode on Jython, and `"{}".format()` encodes its arguments as ASCII, so join such values with `+` (`project.assets.reading`) and keep them out of log lines.
- **Both versions.** The checks run against the 8.1 and the 8.3 API stubs. Where the versions differ, a library module chooses at run time: `library.db.namedQuery` runs `execQuery` on 8.3 and `runNamedQuery` on 8.1, and `library.history.averages` queries `system.historian` on 8.3 and `system.tag.queryTagHistory` on 8.1.

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

- `ruff.toml` extends forgepy's managed Jython base in `.forgepy/ruff-jython.toml`, selects every rule, and turns off the ones that don't fit Jython scripts or Ignition's naming conventions. Scripts are indented with tabs, as the Designer writes them.
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
| `library.seed` | Applies the 8.1 seed spec (`gateway/seed/seed.json`) through a `GatewayConfig` store, which it picks once from the gateway version (none on 8.3) |
| `library.gateway81` | `GatewayConfig` for 8.1: the only module that touches the gateway's internal persistence layer |

## Gateway events

`project`'s gateway events and message handlers are one line each, calling a script module where the work is tested:

| Event | Does |
| --- | --- |
| Startup | Applies the seed (8.1), imports the UDT definitions, then creates or updates a UDT instance per asset in the background, retrying while the database comes up |
| Project update | Exports the UDT definitions back to the files, so a UDT edit made in the Designer becomes a diff (save the project after editing tags) |
| Message handler `recordEvent` | Records an operator's note or acknowledgement and answers the view (`project.events.handle`; see [the demo application](#the-demo-application)) |

The events are written once, in 8.3's format (`ignition/startup/onStartup.py`, `ignition/update/onUpdate.py`, and `ignition/message/<name>/handleMessage.py` with its `enabled` and `threadType` in `resource.json`). 8.1 stores gateway events and message handlers as a binary `ignition/event-scripts/data.bin`, so `scripts/generate-event-scripts.sh` builds it from those files with Ignition 8.1's own serializer (in its Docker image), byte for byte reproducibly; CI fails if it is out of date. Run it after changing an event script or a message handler.

## UDT definitions

The `library` project keeps its UDT definitions as files in `src/udts/<folder>/<name>.json`, so they ship in the gateway image with everything else. `udts/index.json` lists them in import order: a type must come after every type it nests.

The `library.udts` scripts import each definition into `[<provider>]_types_/<folder>`, overwriting what is there, so the files are the source of truth and the gateway converges on them. `exportAll` writes the gateway's definitions back to the files in a canonical form (sorted keys and members, four-space indent, without the bare member placeholders 8.1 adds to nested instances), so a Designer change shows up as a clean diff and 8.1 and 8.3 export the same file.

The equipment types (`blower`, `level`, `mixer`, `pump`) match the asset kinds in the [database](../database/).
