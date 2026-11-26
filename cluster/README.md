# Cluster

OpenTofu modules that deploy the gateway image to Kubernetes and configure the running gateway, and one root module per environment. `k3s` is the reference environment.

| Module | What it manages |
| --- | --- |
| `modules/platform` | The namespace (restricted Pod Security) and the demo PostgreSQL database, initialised from `database/init`, with startup, readiness and liveness probes, resource limits, a NetworkPolicy that only lets the gateways in, and a nightly `pg_dump` backup |
| `modules/gateway` | The [ignition-failover](https://github.com/apollogeddon/ignition-helm) Helm chart running the gateway image, and a nightly gateway backup (8.3) |
| `modules/resources` | Gateway resources through the REST API (8.3): the database connection and, when asked for, the alarm journal, user source and identity provider, login audit profile, and SMTP and email notification profiles |

Each environment is applied in two stages, because the Ignition provider can only connect once the gateway is running:

1. `environments/<env>/infra`: the platform and the gateway (kubernetes and helm providers).
2. `environments/<env>/config`: the gateway's configuration (Ignition provider). It reads the database details and the API key from the `infra` state.

Both stages keep their state in a Secret in the cluster, locked by a Lease, and encrypt it, and every plan, with a passphrase: the state holds every password ([State](#1-state)).

## What the gateway module sets, and why

| Setting | Why |
| --- | --- |
| Redundancy with `activeRouting` | Users only ever reach the Active gateway; rolling updates wait for the Backup to sync |
| `restartOnRenewal` | A running gateway does not re-read renewed certificates; restart the pair, Backup first |
| Soft pod anti-affinity | Master and Backup on different nodes when there are several |
| Readiness, liveness and startup probes | Readiness holds traffic until the gateway runs, liveness restarts one that stops answering, and the startup probe covers slow starts (e.g. a redundant state transfer) without a lax liveness probe |
| Resource requests and limits | Sized from `memory_mb` for the gateway; the chart's own for its init containers, labeller and CronJobs |
| Generated admin and keystore passwords | No chart defaults in a deployed gateway |
| `acceptEula`, from `accept_eula` | The chart no longer accepts the Ignition EULA for you; the module fails until you do |
| An image tag, optionally pinned by digest | A moving tag (`latest`, `<ignition version>-main`) changes the gateway on any restart |
| `emptyDir` size limits | A runaway log cannot fill the node |
| NetworkPolicy, with the ingress controller allowed in | Only the namespace and the ingress controller reach the gateway |
| A deny-all NetworkPolicy for the chart's other pods | The active-routing labeller, the certificate-renewal job and the backup job only call out, so nothing may connect to them |
| `-Dignition.projects.dir` | Projects come from the image (see [`gateway/`](../gateway/README.md)) |
| A generated API key (8.3) | The `config` stage authenticates with it from the first start; nobody creates a key by hand |
| A plan-time check that an ingress has TLS when the API key needs it | Otherwise the first `config` apply fails with 401 or 403 |
| The seed environment (8.1) | The gateway seeds its own configuration (connection, users, journal, audit and so on) on start |

`ignition_version` (`8.1` or `8.3`) chooses between the API key and the seed. The k3s environment reads it from the image tag, which must start with `8.1` or `8.3`.

### The gateway's Secret

The passwords, the license key and activation token, and the API key (8.3) or the seed's variables (8.1) all reach the gateway as environment variables from one Secret, never as plain chart values in the pod spec:

- With `chart_version` 4.x, the chart renders that Secret itself, `<name>-secrets`, from `ignition.secrets`.
- With a chart from 5.0 on, or a local chart (`chart_path`), the module creates it as `<name>-gateway` (`kubernetes_secret_v1.gateway`) and passes it as `ignition.existingSecret`. The chart then renders none, and a hash of the Secret on the pod template rolls the gateways when it changes, as the chart has no pod annotations of its own. To keep the secrets out of OpenTofu altogether, replace that resource with an [External Secrets](https://external-secrets.io/) `ExternalSecret` that writes a Secret of the same name, with the same keys.

`chart_path` is for testing an unreleased chart: point it at a local `charts/failover` after `helm dependency build` there.

## Module inputs

### `platform`

| Input | What it sets | Default |
| --- | --- | --- |
| `namespace` | Namespace for the gateway and its database | required |
| `name` | Prefix for the resource names (`<name>-database`, `<name>-registry` and so on), so two deployments can share a namespace | none: the unprefixed names |
| `create_namespace` | Create the namespace, with restricted Pod Security enforced; `false` uses an existing one | `true` |
| `db_init_dir` | Folder of `*.sql` files run, in name order, when the database is first created | required |
| `db_image` | PostgreSQL image, pinned to a minor release; the backup job runs it too | `docker.io/library/postgres:17.12` |
| `db_name`, `db_user` | Database name and user | `demo` |
| `db_password` | Database password (sensitive) | generated |
| `db_storage` | Database volume size | `2Gi` |
| `storage_class` | StorageClass for the database volume, and its backups unless `db_backup` sets one | the cluster default |
| `db_backup` | A nightly `pg_dump` into a volume of its own: `schedule`, `retention_days`, `storage`, `storage_class`; `null` for none | `23 2 * * *`, 7 days, `5Gi` |
| `db_client_labels` | Pod labels allowed to connect to the database (the gateway pods) | `app.kubernetes.io/name = ignition` |
| `registry` | Credentials for a private image registry, stored as a pull secret (sensitive) | none |

### `gateway`

| Input | What it sets | Default |
| --- | --- | --- |
| `namespace` | Namespace to install into (created by the platform module) | required |
| `name` | The chart's `applicationName`, used for its resources and pod labels | `ignition` |
| `accept_eula` | Accept the [Ignition EULA](https://inductiveautomation.com/ignition/license); must be `true` | required |
| `chart_version` | The Helm chart version to install | `4.2.6` |
| `chart_path` | A local chart directory to install instead, to test an unreleased chart | none |
| `image_repository`, `image_tag` | The gateway image; one tag fully describes the projects it runs, and `latest` is refused | required |
| `image_digest` | `sha256:...` pinning the tag, rendered as `tag@digest` | none |
| `image_pull_policy` | `Never` for images imported straight into the nodes | `IfNotPresent` |
| `image_pull_secrets` | Pull secret names for a private registry | `[]` |
| `admin_password` | Gateway admin password (sensitive) | generated |
| `license_key`, `activation_token` | A license key the gateway activates on start, and a leased key's activation token, as `IGNITION_LICENSE_KEY` and `IGNITION_ACTIVATION_TOKEN` (sensitive) | none |
| `redundancy` | A Master/Backup pair with active routing and certificate-renewal restarts | `true` |
| `issuer` | cert-manager issuer for the Gateway Network and web certificates | required |
| `ingress` | Ingress for the gateway web UI: `host`, `namespace` (the ingress controller's, required), `class_name`, `tls_secret`, `annotations` | none |
| `persistence` | The gateways' data volumes: `size`, `storage_class` (set them before the first apply: a StatefulSet's volumes can't change in place) | `3Gi`, the cluster default |
| `backup` | A nightly `.gwbk` download (8.3): `schedule`, `retention_days`, `storage`, `storage_class`, `url`, `image`; `null` for none | `47 2 * * *`, 7 days, `5Gi`, the ingress's HTTPS URL |
| `memory_mb` | Gateway JVM max heap in MB; the container limit is twice this | `1024` |
| `values` | Extra chart values, merged last | `{}` |
| `ignition_version` | `8.1` or `8.3`: 8.3 gets an API key for the `resources` module, 8.1 a seed environment | `8.3` |
| `api_token_name` | Name of the generated API key (8.3) | `iac` |
| `api_token_require_tls` | Take the API key over HTTPS only, or through the ingress's TLS (8.3) | `true` |
| `seed_environment` | Environment variables for the 8.1 seed spec (`gateway/seed/seed.json`) (sensitive) | `{}` |

### `resources`

Every block but the connection is off unless you set it; `{}` creates it with its defaults.

| Input | What it sets | Default |
| --- | --- | --- |
| `database` | The demo database the gateway connects to (sensitive) | required |
| `connection_name` | Name of the gateway's database connection, which the projects' named queries use | `demo` |
| `alarm_journal` | Store alarm events in the demo database | none |
| `user_source` | An internal user source, and an identity provider using it, for the project's users | none |
| `audit_profile` | An audit profile in the demo database (logins and configuration changes) | none |
| `smtp` | Outgoing mail for alarm notifications: an SMTP profile and an email notification profile (`{}` is `localhost:25`) | none |

The k3s `config` stage and `develop/config` set all four to `{}`, as the 8.1 seed creates them too.

### The k3s stages

| Stage | Input | What it sets | Default |
| --- | --- | --- | --- |
| both | `state_passphrase` | Passphrase the state and plans are encrypted with, at least 16 characters; set `TF_VAR_state_passphrase` (sensitive) | required |
| `infra` | `accept_eula` | Accept the Ignition EULA | required |
| `infra` | `kubeconfig`, `kube_context` | The kubeconfig file and the k3s cluster's context | `~/.kube/config`, `default` |
| `infra` | `namespace` | Namespace for the demo | `ignition` |
| `infra` | `image_repository`, `image_tag`, `image_digest`, `image_pull_policy` | The gateway image (see [Choose the image](#3-choose-the-image)) | `ghcr.io/apollogeddon/ignition-gateway`, required, none, `IfNotPresent` |
| `infra` | `ghcr_username`, `ghcr_token` | A GitHub user and token with `read:packages`, for a private GHCR package | none |
| `infra` | `hostname` | Host name for the gateway web UI, through Traefik | required |
| `infra` | `ingress_annotations` | Annotations merged over the Ingress's own (cert-manager's issuer, Traefik's `websecure` entrypoint with TLS) | `{}` |
| `infra` | `http_redirect` | Redirect plain HTTP to HTTPS with a Traefik Middleware; `false` leaves port 80 unrouted | `true` |
| `infra` | `issuer_name` | cert-manager ClusterIssuer for the gateway and ingress certificates | `cluster-issuer` |
| `infra` | `redundancy` | A redundant Master/Backup pair | `true` |
| `infra` | `admin_password`, `license_key`, `activation_token` | The gateway's admin password and licensing (sensitive) | generated, none, none |
| `infra` | `storage_class` | StorageClass for every volume and backup | the cluster default |
| `config` | `infra_state` | Where the `infra` stage keeps its state: its `backend.hcl` values | the example's |
| `config` | `gateway_url` | Gateway URL to configure | the `infra` stage's ingress URL |
| `config` | `ignition_token` | Gateway API key (`name:secret`) (sensitive) | the key the `infra` stage generated |
| `config` | `allow_insecure_tls` | Accept the gateway's certificate without verifying it; for a throwaway local cluster only | `false` |

## Deploying to k3s

Prerequisites:

- OpenTofu 1.8 or later
- A kubeconfig context for the cluster (`kube_context`, default `default`, the name k3s gives it)
- cert-manager with a ClusterIssuer (`issuer_name`, default `cluster-issuer`)
- Traefik, k3s's default ingress controller, with its CRDs (the HTTP redirect is a Traefik `Middleware`)

### 1. State

Each stage keeps its state in the Secret `tfstate-default-<secret_suffix>` in a namespace of its own, and locks it with a Lease of the same name, so two applies can't run at once. Create that namespace, and each stage's partial backend configuration:

```sh
kubectl create namespace tofu-state
cp cluster/environments/k3s/infra/backend.hcl.example cluster/environments/k3s/infra/backend.hcl
cp cluster/environments/k3s/config/backend.hcl.example cluster/environments/k3s/config/backend.hcl
```

`backend.hcl` names the state's `secret_suffix` and `namespace`, and the kubeconfig (`config_path`, `config_context`); it is git-ignored. If you change the infra stage's, give the config stage the same values as `infra_state`, which it reads the infra outputs with. Anyone who can read Secrets in that namespace can read the state's ciphertext, so keep it to the people who deploy.

### 2. Encryption

The state holds every password, and so does a saved plan, so both stages encrypt both with AES-GCM, with a key derived (PBKDF2) from `state_passphrase`. Set it in the environment, never in a file, and keep it somewhere safe: the state can't be read without it.

```sh
export TF_VAR_state_passphrase='<at least 16 characters>'
```

Both stages take the same passphrase, as `config` decrypts the `infra` state with it.

#### Migrating local state

Earlier releases kept each stage's state in an unencrypted local `terraform.tfstate`. Move it into the cluster, encrypting it, by adding an unencrypted fallback for reading it, for this one run only, through `TF_ENCRYPTION`:

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

`tofu init -migrate-state` copies the local state into the Secret, encrypting it on the way. Delete the local `terraform.tfstate` and `terraform.tfstate.backup` files once `tofu plan` reads the new state without `TF_ENCRYPTION`. The encryption is not `enforced`, as that would refuse the fallback this migration needs.

### 3. Choose the image

By default the environment pulls a published image from `ghcr.io/apollogeddon/ignition-gateway` (`image_repository`, with `image_pull_policy = "IfNotPresent"`). Set `image_tag` to a release's `<ignition version>-<release version>`, such as `8.3.10-2.0.1`. `latest` and `<ignition version>-main` are refused: CI re-pushes `-main` on every merge, so a restarted pod could run another build. To pin the tag to an exact image, also set `image_digest` from the release's `images-<version>.txt`, or:

```sh
docker buildx imagetools inspect ghcr.io/apollogeddon/ignition-gateway:8.3.10-2.0.1
```

If the package is private, also set `ghcr_username` and `ghcr_token` (a GitHub token with `read:packages`) to create a pull secret.

To run a locally built image instead, import it into k3s's containerd directly:

```sh
docker build -f gateway/Dockerfile -t localhost/ignition-gateway:8.3-dev .
docker save localhost/ignition-gateway:8.3-dev -o gateway.tar
# on the k3s host (in WSL the file is under /mnt/c/...)
sudo k3s ctr images import gateway.tar
```

Then set `image_repository = "localhost/ignition-gateway"`, `image_tag = "8.3-dev"` and `image_pull_policy = "Never"`. Every tag must start with its Ignition version (`8.1` or `8.3`), as the environment reads the version from it.

### 4. Infra

```sh
cd cluster/environments/k3s/infra
cp k3s.example.tfvars terraform.tfvars   # set accept_eula, image_tag and hostname
tofu init -backend-config=backend.hcl
tofu apply
tofu output -raw admin_password
```

In `terraform.tfvars`:

1. **`accept_eula = true`**, once you've read the [Ignition EULA](https://inductiveautomation.com/ignition/license). The module refuses to deploy without it.
2. **`image_tag`** (and optionally `image_digest`), as above.
3. **`hostname`**: any name that resolves to the k3s node, from your machine and from inside the cluster (the gateway backup goes through it). `nip.io` maps `<ip>.nip.io` to `<ip>`.
4. **Licensing**, optional: `license_key` and, for a leased license, `activation_token`. They reach the gateway as `IGNITION_LICENSE_KEY` and `IGNITION_ACTIVATION_TOKEN` through its Secret, and it activates on start. Without them the gateway runs a trial. Pass them as `TF_VAR_license_key` and `TF_VAR_activation_token` rather than writing them to the file.
5. **`admin_password`**, optional: generated when unset.

**TLS.** The Ingress serves the gateway over HTTPS only, on Traefik's `websecure` entrypoint, with the `ignition-ingress-tls` certificate from your ClusterIssuer. Plain HTTP gets a permanent redirect to HTTPS (`http_redirect`), so no admin login crosses the network in the clear. `ingress_annotations` overrides any annotation, for another entrypoint name for instance. The gateway module fails the plan if the gateway would only take its API key over TLS (`api_token_require_tls`, the default) but the ingress has no `tls_secret`.

**Backups.** Two CronJobs back up nightly into volumes of their own, keeping 7 days:

- `database-backup` runs `pg_dump -Fc` at 02:23 UTC into the `database-backup` claim. Restore one with `pg_restore`.
- `ignition-backup` (8.3) downloads a gateway backup (`GET /data/api/v1/backup`, with the module's API key) at 02:47 UTC into the `ignition-backup` claim. It goes through the ingress's HTTPS URL, and checks the certificate against the `ca.crt` of the ingress's TLS Secret, which a private CA issuer writes. Restore a `.gwbk` from the gateway's web UI, or through the chart's `ignition.restore` on an empty data volume. 8.1 has no REST API, so there's no gateway backup there.

A backup stays on the cluster's own storage: copy the claims off the cluster too (with Velero, or `kubectl cp` from a pod that mounts them). `storage_class` sets the class of every volume; the gateway module's `persistence` and both modules' backup inputs set their sizes.

### 5. Config

The Ignition provider is not published to a registry. Its docs site serves every release as a [provider network mirror](https://apollogeddon.github.io/ignition-tofu/docs/guides/installation/), so point OpenTofu at it once in your CLI configuration (`~/.tofurc`, or the file named by `TF_CLI_CONFIG_FILE`):

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

`tofu init` then installs the provider for your platform, and each stage's `.terraform.lock.hcl` fixes the exact build and its checksums: commit it, and move it on with `tofu init -upgrade`. To use a provider built from source instead, see the provider's [installation guide](https://apollogeddon.github.io/ignition-tofu/docs/guides/installation/).

The provider authenticates with the API key the `infra` stage generated, which the gateway installed for itself. `config` reads it from the `infra` state, with the same passphrase; set the `ignition_token` variable to use another:

```sh
cd cluster/environments/k3s/config
tofu init -backend-config=backend.hcl
tofu apply
```

The provider checks the gateway's certificate, and the API key it sends is a gateway administrator's, so keep the check on. The ingress certificate comes from your ClusterIssuer: if that's a private CA, give OpenTofu its certificate. On Linux, point `SSL_CERT_FILE` at a bundle that holds the system CAs and yours (on macOS and Windows, add the CA to the system's trust store):

```sh
cat /etc/ssl/certs/ca-certificates.crt my-ca.crt > ca-bundle.pem
export SSL_CERT_FILE="$PWD/ca-bundle.pem"
```

On a throwaway local cluster you can skip the check instead with `allow_insecure_tls = true` in the stage's `terraform.tfvars`. Anyone who can intercept the connection then gets the key. The gateway also takes the key over HTTPS only, or through the ingress's TLS. For a gateway reached over plain HTTP, set the gateway module's `api_token_require_tls = false` (`develop/` does this, as its gateway is on loopback). The ingress's TLS reaches the gateway as an `X-Forwarded-Proto: https` header, which the gateway believes only when the module has an ingress. A pod that can reach the gateway's HTTP port could send that header too, and the NetworkPolicy admits only the ingress controller's namespace and the release's own namespace, so keep other workloads out of that namespace. The platform module's database, which shares it, can't open connections.

On 8.1 there is no `config` stage to run: the gateway seeds itself on start from `gateway/seed/seed.json`. The seeded users' password is `tofu output -raw demo_users_password` in `infra`.

### From CI

The `deploy` pipeline plans and applies both stages from GitHub Actions, on a manual run of the `index` workflow, with a GitHub environment's required reviewers approving the plan. See [`.github/WORKFLOWS.md`](../.github/WORKFLOWS.md#deploy) for the environments and secrets it needs.

## Tests

`tofu test` checks each module's validations and the values it renders, and the k3s `infra` stage's image checks and HTTPS-only ingress, against mock providers, so it needs no cluster:

```sh
tofu -chdir=cluster/modules/gateway init -backend=false && tofu -chdir=cluster/modules/gateway test
```

The same goes for `cluster/modules/platform`, `cluster/modules/resources` (whose `init` needs the provider mirror above) and `cluster/environments/k3s/infra`.
