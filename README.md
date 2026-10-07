# Ignition demo

A best-practice template for running Inductive Automation Ignition 8.3 as code:
the gateway, its configuration and its projects all come from this repository,
and every environment is built the same way.

- **Projects as code.** Each Ignition project lives in `projects/` as the files
  the Designer writes, with its Python scripts linted, type-checked and unit
  tested outside the gateway. A sanitiser strips the Designer's noise
  (timestamps, actors, signatures) so diffs show only real changes.
- **Immutable gateway image.** `gateway/` bakes the projects into the image and
  points Ignition at them, so shipping a project means shipping a new image tag,
  and every gateway in a redundant pair runs the same code.
- **Platform as code.** `deploy/` uses OpenTofu to install the
  [ignition-failover](https://github.com/apollogeddon/ignition-helm) chart with
  redundancy, TLS and active routing, plus its database.
- **Gateway configuration as code.** `deploy/` also configures the running
  gateway through its REST API with the
  [ignition provider](https://github.com/apollogeddon/ignition-tfpl): database
  connections, tag providers, user sources, alarm journals and so on.

## Layout

| Path | What it holds |
| --- | --- |
| `projects/library/` | An inheritable project: shared scripts, styles and views |
| `projects/project/` | The application project; inherits from `library` |
| `gateway/` | The gateway image: Ignition plus the projects |
| `deploy/modules/` | OpenTofu modules: `platform`, `gateway`, `gateway-config`, `trial-keepalive` |
| `deploy/environments/` | One root module per environment (`k3s` is the reference) |
| `local/` | Docker Compose for Designer work, with the projects mounted live |
| `scripts/` | Repository tooling: the resource sanitiser and git setup |

## Who owns what

Each setting has exactly one owner, so nothing fights over it:

| Owner | Owns |
| --- | --- |
| The gateway image | Project contents (views, scripts, named queries) |
| The Helm chart | Redundancy, the Gateway Network, certificates, pod security |
| OpenTofu (`gateway-config`) | Gateway resources: connections, providers, users, alarming |

Projects are deliberately not managed through the REST API: the image is their
single source, so a gateway never drifts from the tag it runs.

## Getting started

```sh
scripts/setup-git.sh          # once per clone: enables the resource sanitiser
```

See each folder's README for its workflow.
