---
title: Cluster
description: OpenTofu modules that deploy and configure the gateway on Kubernetes.
---

`cluster/` holds the OpenTofu modules that deploy the gateway image to Kubernetes and configure the running gateway, and one root module per environment. `k3s` is the reference environment.

| Module | What it manages |
| --- | --- |
| `modules/platform` | The namespace (restricted Pod Security), and the demo PostgreSQL database from `database/init` with a NetworkPolicy and nightly backup |
| `modules/gateway` | The [ignition-failover](https://github.com/apollogeddon/ignition-helm) Helm chart running the gateway image, and a nightly gateway backup (8.3) |
| `modules/resources` | Gateway resources through the REST API (8.3): the database connection and optional journal, users, audit and email profiles |

Each environment is applied in two stages, as the Ignition provider needs a running gateway:

1. `environments/<env>/infra`: the platform and the gateway.
2. `environments/<env>/config`: the gateway's configuration, from `infra`'s state. Required on 8.3; 8.1 seeds its own.

Both stages keep their state, encrypted with a passphrase, in a Secret in the cluster, locked by a Lease ([State](#1-state)).

## What the gateway module sets, and why

- **Redundancy with `activeRouting`**: users only reach the Active gateway.
- **`restartOnRenewal`**: renewed certificates load on a restart, Backup first.
- **Soft pod anti-affinity**: Master and Backup on different nodes.
- **Readiness, liveness and startup probes**, with room for a slow state transfer.
- **Resource limits**: the gateway's from `memory_mb`.
- **Generated passwords** and an **API key (8.3)**: no chart defaults, and `config` authenticates from the first start.
- **`acceptEula`, from `accept_eula`**: the module fails until you accept.
- **A release tag, optionally pinned by digest**: a moving tag changes the gateway on any restart.
- **`emptyDir` size limits**: a runaway log can't fill the node.
- **NetworkPolicies**: only the namespace and the ingress controller reach the gateway; the chart's other pods take no connections.
- **`-Dignition.projects.dir`**: projects come from the image (see [Gateway image](../gateway-image/)).
- **An atomic install and upgrade** ([A failed install](#a-failed-install)).
- **A plan-time TLS check**: fails the plan if the API key needs TLS the ingress lacks.
- **The seed environment (8.1)**: the gateway seeds its own configuration.

`ignition_version` (`8.1` or `8.3`) chooses between the API key and the seed; the k3s environment reads it from the image tag.

### The gateway's Secret

Passwords, licensing, and the API key or seed variables reach the gateway from one Secret:

- `chart_version` 4.x: the chart renders `<name>-secrets` from `ignition.secrets`.
- A chart from 5.0, or `chart_path`: the module creates `<name>-gateway` (`kubernetes_secret_v1.gateway`) and passes it as `ignition.existingSecret`. A hash of it on the pod template rolls the gateways when it changes. An [External Secrets](https://external-secrets.io/) `ExternalSecret` of the same name and keys can replace it.

### A local chart (`chart_path`)

`chart_path` installs an unreleased chart from a directory, such as an [ignition-helm](https://github.com/apollogeddon/ignition-helm) checkout's `charts/failover`:

- The module builds its `file://` dependencies on every install and upgrade (`dependency_update`): no `helm dependency build` needed.
- A hash of the chart's and its `file://` dependencies' files goes in the release's description, so an edit at the same chart version still upgrades. It skips `charts/`, `Chart.lock`, `tests/` and `ci/`.
- A dependency from a chart repository isn't hashed: change its version in `Chart.yaml`.

## Module inputs

### `platform`

| Input | Default | Purpose |
| --- | --- | --- |
| `namespace` | required | Namespace for the gateway and database |
| `name` | none | Prefix for resource names, so two deployments can share a namespace |
| `create_namespace` | `true` | Create the namespace; `false` uses an existing one |
| `db_init_dir` | required | `*.sql` files run in name order on the database's creation |
| `db_image` | `docker.io/library/postgres:17.12` | PostgreSQL image, also run by the backup job |
| `db_name`, `db_user` | `demo` | Database name and user |
| `db_password` | generated | Database password (sensitive) |
| `db_storage` | `2Gi` | Database volume size |
| `storage_class` | cluster default | StorageClass for the database and its backups |
| `db_backup` | `23 2 * * *`, 7 days, `5Gi` | Nightly `pg_dump`: `schedule`, `retention_days`, `storage`, `storage_class`; `null` for none |
| `db_client_labels` | `app.kubernetes.io/name = ignition` | Pod labels allowed to connect |
| `registry` | none | Private registry credentials for a pull secret (sensitive) |

### `gateway`

| Input | Default | Purpose |
| --- | --- | --- |
| `namespace` | required | Namespace to install into |
| `name` | `ignition` | The chart's `applicationName` |
| `accept_eula` | required | Accept the [Ignition EULA](https://inductiveautomation.com/ignition/license); must be `true` |
| `chart_version` | `4.2.6` | Chart version to install |
| `chart_path` | none | Local chart to install instead ([A local chart](#a-local-chart-chart_path)) |
| `timeout` | `900` | Seconds an install or upgrade may take, at least 300 |
| `atomic` | `true` | Uninstall a failed first install, roll back a failed upgrade ([A failed install](#a-failed-install)) |
| `image_repository`, `image_tag` | required | The gateway image; `latest` is refused |
| `image_digest` | none | `sha256:...` pinning the tag |
| `image_pull_policy` | `IfNotPresent` | `Never` for images imported into the nodes |
| `image_pull_secrets` | `[]` | Pull secrets for a private registry |
| `admin_password` | generated | Admin password (sensitive) |
| `license_key`, `activation_token` | none | `IGNITION_LICENSE_KEY` and `IGNITION_ACTIVATION_TOKEN` (sensitive) |
| `redundancy` | `true` | Master/Backup pair with active routing |
| `issuer` | required | cert-manager issuer for the Gateway Network and web certificates |
| `ingress` | none | `host`, `namespace` (the controller's, required), `class_name`, `tls_secret`, `annotations` |
| `persistence` | `3Gi`, cluster default | Data volumes' `size`, `storage_class`; fixed after the first apply |
| `backup` | `47 2 * * *`, 7 days, `5Gi`, the ingress URL | Nightly `.gwbk` (8.3), as `db_backup` plus `url`, `image` |
| `memory_mb` | `1024` | JVM max heap; the container limit is twice this |
| `values` | `{}` | Extra chart values, merged last |
| `ignition_version` | `8.3` | `8.3` gets an API key, `8.1` a seed environment |
| `api_token_name` | `iac` | Name of the generated API key (8.3) |
| `api_token_require_tls` | `true` | Take the API key over HTTPS or the ingress's TLS only (8.3) |
| `seed_environment` | `{}` | Variables for the 8.1 seed spec (sensitive) |

### `resources`

Each optional block is off unless set; `{}` takes its defaults. The k3s `config` stage and `develop/config` set all four to `{}`.

| Input | Default | Purpose |
| --- | --- | --- |
| `database` | required | The demo database to connect to (sensitive) |
| `connection_name` | `demo` | Name of the connection the named queries use |
| `alarm_journal` | none | Alarm events in the demo database |
| `user_source` | none | Internal user source and identity provider |
| `audit_profile` | none | Audit profile in the demo database |
| `smtp` | none | SMTP and email notification profiles (`{}` is `localhost:25`) |

### The k3s stages

| Stage | Input | Default | Purpose |
| --- | --- | --- | --- |
| both | `state_passphrase` | required | Encrypts state and plans, at least 16 characters; set `TF_VAR_state_passphrase` |
| `infra` | `accept_eula` | required | Accept the Ignition EULA |
| `infra` | `kubeconfig`, `kube_context` | `~/.kube/config`, `default` | The cluster to deploy to |
| `infra` | `namespace` | `ignition` | Namespace for the demo |
| `infra` | `image_repository`, `image_tag`, `image_digest`, `image_pull_policy` | as `gateway`; repository `ghcr.io/apollogeddon/ignition-gateway` | The image ([Choose the image](#3-choose-the-image)) |
| `infra` | `ghcr_username`, `ghcr_token` | none | A token with `read:packages`, for a private package |
| `infra` | `hostname` | required | Host name for the web UI, through Traefik |
| `infra` | `ingress_annotations` | `{}` | Merged over the Ingress's own |
| `infra` | `http_redirect` | `true` | Redirect HTTP to HTTPS; `false` leaves port 80 unrouted |
| `infra` | `issuer_name` | `cluster-issuer` | cert-manager ClusterIssuer |
| `infra` | `redundancy` | `true` | Master/Backup pair |
| `infra` | `admin_password`, `license_key`, `activation_token` | generated, none, none | Admin password and licensing (sensitive) |
| `infra` | `storage_class` | cluster default | StorageClass for every volume |
| `infra` | `chart_path` | none | Local chart to install ([A local chart](#a-local-chart-chart_path)) |
| `infra` | `gateway_timeout`, `gateway_atomic` | `900`, `true` | The gateway module's `timeout` and `atomic` |
| `config` | `infra_state` | the example's | The `infra` stage's `backend.hcl` values |
| `config` | `gateway_url` | the `infra` ingress URL | Gateway to configure |
| `config` | `ignition_token` | the generated key | API key, `name:secret` (sensitive) |
| `config` | `allow_insecure_tls` | `false` | Skip certificate checks; throwaway clusters only |

## Deploying to k3s

You need OpenTofu 1.8+, a kubeconfig context, cert-manager with a ClusterIssuer, and Traefik with its CRDs.

### 1. State

```sh
kubectl create namespace tofu-state
cp cluster/environments/k3s/infra/backend.hcl.example cluster/environments/k3s/infra/backend.hcl
cp cluster/environments/k3s/config/backend.hcl.example cluster/environments/k3s/config/backend.hcl
```

- Each stage's state is the Secret `tfstate-default-<secret_suffix>`, locked by a Lease of the same name.
- If you change infra's `backend.hcl` (git-ignored), set the same values in config's `infra_state`.
- Limit who can read Secrets in `tofu-state`.

### 2. Encryption

```sh
export TF_VAR_state_passphrase='<at least 16 characters>'
```

- Both stages use the same passphrase. Never write it to a file: without it the state is lost.

#### If you have local state

Move an earlier release's unencrypted `terraform.tfstate` into the cluster once:

```sh
export TF_ENCRYPTION='
method "unencrypted" "migrate" {}
state {
  method = method.aes_gcm.state
  fallback {
    method = method.unencrypted.migrate
  }
}'
cd cluster/environments/k3s/infra
tofu init -migrate-state -backend-config=backend.hcl
tofu plan    # reads the migrated state: expect only this release's changes
cd ../config
tofu init -migrate-state -backend-config=backend.hcl
unset TF_ENCRYPTION
```

Once `tofu plan` works without `TF_ENCRYPTION`, delete the local `terraform.tfstate*` files.

### 3. Choose the image

- Set `image_tag` to a release, `<ignition version>-<release version>` such as `8.3.10-2.0.1` (see [Gateway image](../gateway-image/#published-images)), from `ghcr.io/apollogeddon/ignition-gateway`. `latest` and `-main` tags are refused, as CI re-pushes `-main`.
- Optionally pin `image_digest` from the release's `images-<version>.txt`, or `docker buildx imagetools inspect ghcr.io/apollogeddon/ignition-gateway:8.3.10-2.0.1`.
- A private package also needs `ghcr_username` and `ghcr_token`.
- Every tag must start with `8.1` or `8.3`.

#### If you use a local build

```sh
docker build -f gateway/Dockerfile -t localhost/ignition-gateway:8.3-dev .
docker save localhost/ignition-gateway:8.3-dev -o gateway.tar
# on the k3s host (in WSL the file is under /mnt/c/...)
sudo k3s ctr images import gateway.tar
```

Then set `image_repository = "localhost/ignition-gateway"`, `image_tag = "8.3-dev"` and `image_pull_policy = "Never"`.

### 4. Infra

```sh
cd cluster/environments/k3s/infra
cp k3s.example.tfvars terraform.tfvars   # set accept_eula, image_tag and hostname
tofu init -backend-config=backend.hcl
tofu apply
tofu output -raw admin_password
```

In `terraform.tfvars`:

1. `accept_eula = true`, once you've read the [Ignition EULA](https://inductiveautomation.com/ignition/license).
2. `image_tag`, and optionally `image_digest`.
3. `hostname`: resolves to the node from your machine and inside the cluster; `<ip>.nip.io` works.
4. Licensing (optional): `TF_VAR_license_key` and, if leased, `TF_VAR_activation_token`, not in the file.
5. `admin_password` (optional): generated when unset.

After the apply:

- On 8.3 each gateway restarts once to load its API key (see [Gateway image](../gateway-image/#83-an-api-key-from-the-start)), answering 503 for about 30 seconds. Wait before opening the project or applying `config`.
- The Ingress serves HTTPS only, on Traefik's `websecure` entrypoint, with the `ignition-ingress-tls` certificate.
- Two CronJobs back up nightly into their own claims, keeping 7 days, at times in the cluster's time zone:

| CronJob | Backs up | At | Restore with |
| --- | --- | --- | --- |
| `database-backup` | `pg_dump -Fc` | 02:23 | `pg_restore` |
| `ignition-backup` (8.3) | a `.gwbk` from `GET /data/api/v1/backup` through the ingress, checked against its TLS Secret's `ca.crt` | 02:47 | the gateway's web UI, or the chart's `ignition.restore` on an empty data volume |

Copy the claims off the cluster too (Velero, or `kubectl cp`).

#### A failed install

A pair's first install takes about 5 minutes; the module waits up to `timeout` (15 minutes). With `atomic` (default) a failed install is uninstalled, so the next apply retries, and a failed upgrade rolls back. To keep a failing install's pods to debug, apply with `-var gateway_atomic=false`, then `kubectl -n ignition get pods,events`, `kubectl -n ignition logs ignition-1 --all-containers` and `helm -n ignition status ignition`.

#### If apply fails with `cannot re-use a name that is still in use`

A failed release was left behind (`gateway_atomic = false`, or an earlier module release). Remove it, and the data volumes it left for a clean start, then apply:

```sh
helm -n ignition uninstall ignition
kubectl -n ignition delete pvc data-ignition-0 data-ignition-1   # optional
tofu apply
```

### 5. Config

Required on 8.3: it creates the `demo` connection, and until then the Assets page shows an ERROR. On 8.1 there is no `config` stage; the seeded users' password is `tofu output -raw demo_users_password` in `infra`.

Install the Ignition provider from its [network mirror](https://apollogeddon.github.io/ignition-tofu/docs/guides/installation/), in `~/.tofurc` or the file `TF_CLI_CONFIG_FILE` names:

```hcl
provider_installation {
  network_mirror {
    url     = "https://apollogeddon.github.io/ignition-tofu/providers/"
    include = ["registry.opentofu.org/apollogeddon/ignition"]
  }
  direct {
    exclude = ["registry.opentofu.org/apollogeddon/ignition"]
  }
}
```

```sh
cd cluster/environments/k3s/config
tofu init -backend-config=backend.hcl
tofu apply
```

- Commit each stage's `.terraform.lock.hcl`; move it on with `tofu init -upgrade`.
- `config` reads `infra`'s API key from its state; set `ignition_token` to use another.
- A 503 straight after `infra`: the gateway is still restarting. Apply again a minute later.

#### If your ClusterIssuer is a private CA

The apply fails with `x509: certificate signed by unknown authority`. On Linux, set `SSL_CERT_FILE` to the system CAs plus yours; on macOS and Windows, trust the CA in the system store:

```sh
kubectl -n ignition get secret ignition-ingress-tls -o jsonpath='{.data.ca\.crt}' | base64 -d > my-ca.crt
cat /etc/ssl/certs/ca-certificates.crt my-ca.crt > ca-bundle.pem
export SSL_CERT_FILE="$PWD/ca-bundle.pem"
```

`allow_insecure_tls = true` skips the check, on a throwaway cluster only: anyone who intercepts the connection gets the key.

#### If the gateway is on plain HTTP

The API key needs HTTPS or the ingress's TLS. For plain HTTP, set `api_token_require_tls = false`, as `develop/` does on loopback. Any pod reaching the gateway's HTTP port could fake the ingress's `X-Forwarded-Proto: https`, so keep other workloads out of the namespace.

### From CI

A manual run of `index` plans both stages and applies them once reviewers approve ([`.github/WORKFLOWS.md`](https://github.com/apollogeddon/ignition-demo/blob/main/.github/WORKFLOWS.md#deploy)).

## Tests

`tofu test` runs each module's and the k3s `infra` stage's tests against mock providers, with no cluster:

```sh
tofu -chdir=cluster/modules/gateway init -backend=false && tofu -chdir=cluster/modules/gateway test
```

The same goes for `cluster/modules/platform`, `cluster/modules/resources` (whose `init` needs the provider mirror) and `cluster/environments/k3s/infra`.

The `e2e` pipeline deploys both stages to a throwaway k3d cluster, to catch what only a cluster refuses (see [`.github/WORKFLOWS.md`](https://github.com/apollogeddon/ignition-demo/blob/main/.github/WORKFLOWS.md#e2e)).
