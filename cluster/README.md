# Cluster

OpenTofu modules that deploy the gateway image to Kubernetes and configure the running gateway, and one root module per environment. `k3s` is the reference environment.

| Module | What it manages |
| --- | --- |
| `modules/platform` | The namespace (restricted Pod Security) and the demo PostgreSQL database, initialised from `database/init`, with startup, readiness and liveness probes, resource limits and a NetworkPolicy that only lets the gateways in |
| `modules/gateway` | The [ignition-failover](https://github.com/apollogeddon/ignition-helm) Helm chart running the gateway image |
| `modules/resources` | Gateway resources through the REST API (8.3): the database connection, alarm journal, user source and identity provider, login audit profile, and SMTP and email notification profiles |

Each environment is applied in two stages, because the Ignition provider can only connect once the gateway is running:

1. `environments/<env>/infra`: the platform and the gateway (kubernetes and helm providers).
2. `environments/<env>/config`: the gateway's configuration (Ignition provider). It reads the database details and the API key from the `infra` state.

## What the gateway module sets, and why

| Setting | Why |
| --- | --- |
| Redundancy with `activeRouting` | Users only ever reach the Active gateway; rolling updates wait for the Backup to sync |
| `restartOnRenewal` | A running gateway does not re-read renewed certificates; restart the pair, Backup first |
| Soft pod anti-affinity | Master and Backup on different nodes when there are several |
| Readiness, liveness and startup probes | Readiness holds traffic until the gateway runs, liveness restarts one that stops answering, and the startup probe covers slow starts (e.g. a redundant state transfer) without a lax liveness probe |
| Resource requests and limits | Sized from `memory_mb` for the gateway; the chart's own for its init containers, labeller and CronJobs |
| Generated admin and keystore passwords | No chart defaults in a deployed gateway |
| `emptyDir` size limits | A runaway log cannot fill the node |
| NetworkPolicy, with the ingress controller allowed in | Only the namespace and the ingress controller reach the gateway |
| A deny-all NetworkPolicy for the chart's other pods | The active-routing labeller and certificate-renewal job only call out, so nothing may connect to them |
| `-Dignition.projects.dir` | Projects come from the image (see [`gateway/`](../gateway/README.md)) |
| A generated API key (8.3) | The `config` stage authenticates with it from the first start; nobody creates a key by hand |
| The seed environment (8.1) | The gateway seeds its own configuration (connection, users, journal, audit and so on) on start |

`ignition_version` (`8.1` or `8.3`) chooses between the last two. The k3s environment takes it from the image tag (its `8.1` or `8.3` prefix).

## Module inputs

### `platform`

| Input | What it sets | Default |
| --- | --- | --- |
| `namespace` | Namespace for the gateway and its database | required |
| `create_namespace` | Create the namespace, with restricted Pod Security enforced; `false` uses an existing one | `true` |
| `db_init_dir` | Folder of `*.sql` files run, in name order, when the database is first created | required |
| `db_image` | PostgreSQL image | the module's |
| `db_name`, `db_user` | Database name and user | `demo` |
| `db_password` | Database password (sensitive) | generated |
| `db_storage` | Database volume size | `2Gi` |
| `storage_class` | StorageClass for the database volume | the cluster default |
| `db_client_labels` | Pod labels allowed to connect to the database (the gateway pods) | `app.kubernetes.io/name = ignition` |
| `registry` | Credentials for a private image registry, stored as a pull secret (sensitive) | none |

### `gateway`

| Input | What it sets | Default |
| --- | --- | --- |
| `namespace` | Namespace to install into (created by the platform module) | required |
| `name` | The chart's `applicationName`, used for its resources and pod labels | `ignition` |
| `chart_version` | The Helm chart version to install | the module's |
| `image_repository`, `image_tag` | The gateway image; one tag fully describes the projects it runs | required |
| `image_pull_policy` | `Never` for images imported straight into the nodes | `IfNotPresent` |
| `image_pull_secrets` | Pull secret names for a private registry | `[]` |
| `admin_password` | Gateway admin password (sensitive) | generated |
| `redundancy` | A Master/Backup pair with active routing and certificate-renewal restarts | `true` |
| `issuer` | cert-manager issuer for the Gateway Network and web certificates | required |
| `ingress` | Ingress for the gateway web UI | none |
| `memory_mb` | Gateway JVM max heap in MB; the container limit is twice this | `1024` |
| `values` | Extra chart values, merged last | `{}` |
| `ignition_version` | `8.1` or `8.3`: 8.3 gets an API key for the `resources` module, 8.1 a seed environment | `8.3` |
| `api_token_name` | Name of the generated API key (8.3) | `iac` |
| `api_token_require_tls` | Take the API key over HTTPS only, or through the ingress's TLS (8.3) | `true` |
| `seed_environment` | Environment variables for the 8.1 seed spec (`gateway/seed/seed.json`) (sensitive) | `{}` |

### `resources`

| Input | What it sets | Default |
| --- | --- | --- |
| `database` | The demo database the gateway connects to (sensitive) | required |
| `connection_name` | Name of the gateway's database connection, which the projects' named queries use | `demo` |
| `alarm_journal` | Store alarm events in the demo database; `null` for no journal | `{}` |
| `user_source` | An internal user source, and an identity provider using it, for the project's users; `null` for none | `{}` |
| `audit_profile` | An audit profile in the demo database (logins and configuration changes); `null` for none | `{}` |
| `smtp` | Outgoing mail for alarm notifications: an SMTP profile and an email notification profile; `null` for none | `{}` |

### The k3s stages

| Stage | Input | What it sets | Default |
| --- | --- | --- | --- |
| `infra` | `kubeconfig`, `kube_context` | The kubeconfig file and the k3s cluster's context | `~/.kube/config`, `default` |
| `infra` | `namespace` | Namespace for the demo | `ignition` |
| `infra` | `image_repository`, `image_tag`, `image_pull_policy` | The gateway image (see [Choose the image](#1-choose-the-image)) | `ghcr.io/apollogeddon/ignition-gateway`, required, `IfNotPresent` |
| `infra` | `ghcr_username`, `ghcr_token` | A GitHub user and token with `read:packages`, for a private GHCR package | none |
| `infra` | `hostname` | Host name for the gateway web UI, through Traefik | required |
| `infra` | `issuer_name` | cert-manager ClusterIssuer for the gateway and ingress certificates | `cluster-issuer` |
| `infra` | `redundancy` | A redundant Master/Backup pair | `true` |
| `config` | `gateway_url` | Gateway URL to configure | the `infra` stage's ingress URL |
| `config` | `ignition_token` | Gateway API key (`name:secret`) (sensitive) | the key the `infra` stage generated |
| `config` | `allow_insecure_tls` | Accept the gateway's certificate without verifying it; for a throwaway local cluster only | `false` |

## The k3s reference environment

Prerequisites:

- OpenTofu
- A kubeconfig context for the cluster (`kube_context`, default `default`, the name k3s gives it)
- cert-manager with a ClusterIssuer (`issuer_name`, default `cluster-issuer`)
- Traefik, k3s's default ingress controller

### 1. Choose the image

By default the environment pulls a published image from `ghcr.io/apollogeddon/ignition-gateway` (`image_repository`, with `image_pull_policy = "IfNotPresent"`). Set `image_tag` to a tag CI published, such as `<ignition version>-main` or a release's `<ignition version>-<release version>`. If the package is private, also set `ghcr_username` and `ghcr_token` (a GitHub token with `read:packages`) to create a pull secret.

To run a locally built image instead, import it into k3s's containerd directly:

```sh
docker build -f gateway/Dockerfile -t localhost/ignition-gateway:dev .
docker save localhost/ignition-gateway:dev -o gateway.tar
# on the k3s host (in WSL the file is under /mnt/c/...)
sudo k3s ctr images import gateway.tar
```

Then set `image_repository = "localhost/ignition-gateway"`, `image_tag = "dev"` and `image_pull_policy = "Never"`. Name a local tag after its Ignition version (for example `8.1-dev`) when it isn't 8.3, as the environment reads the version from the tag.

### 2. Infra

```sh
cd cluster/environments/k3s/infra
cp k3s.example.tfvars terraform.tfvars   # set image_tag and hostname
tofu init
tofu apply
tofu output -raw admin_password
```

### 3. Config

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

The provider authenticates with the API key the `infra` stage generated, which the gateway installed for itself. `config` reads it from the `infra` state; set the `ignition_token` variable to use another:

```sh
cd cluster/environments/k3s/config
tofu init
tofu apply
```

The provider checks the gateway's certificate, and the API key it sends is a gateway administrator's, so keep the check on. The ingress certificate comes from your ClusterIssuer: if that's a private CA, give OpenTofu its certificate. On Linux, point `SSL_CERT_FILE` at a bundle that holds the system CAs and yours (on macOS and Windows, add the CA to the system's trust store):

```sh
cat /etc/ssl/certs/ca-certificates.crt my-ca.crt > ca-bundle.pem
export SSL_CERT_FILE="$PWD/ca-bundle.pem"
```

On a throwaway local cluster you can skip the check instead with `allow_insecure_tls = true` in the stage's `terraform.tfvars`. Anyone who can intercept the connection then gets the key. The gateway also takes the key over HTTPS only, or through the ingress's TLS. For a gateway reached over plain HTTP, set the gateway module's `api_token_require_tls = false` (`develop/` does this, as its gateway is on loopback). The ingress's TLS reaches the gateway as an `X-Forwarded-Proto: https` header, which the gateway believes only when the module has an ingress. A pod that can reach the gateway's HTTP port could send that header too, and the NetworkPolicy admits only the ingress controller's namespace and the release's own namespace, so keep other workloads out of that namespace. The platform module's database, which shares it, can't open connections.

On 8.1 there is no `config` stage to run: the gateway seeds itself on start from `gateway/seed/seed.json`. The seeded users' password is `tofu output -raw demo_users_password` in `infra`.
