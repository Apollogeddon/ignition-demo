# Cluster

OpenTofu modules that deploy the gateway image to Kubernetes and configure the running gateway, and one root module per environment. `k3s` is the reference environment.

| Module | What it manages |
| --- | --- |
| `modules/platform` | The namespace (restricted Pod Security) and the demo PostgreSQL database, initialised from `db/init` |
| `modules/gateway` | The [ignition-failover](https://github.com/apollogeddon/ignition-helm) Helm chart running the gateway image |
| `modules/gateway-config` | Gateway resources through the REST API (8.3): the database connection, alarm journal, user source and identity provider, login audit profile, and SMTP and email notification profiles |

Each environment is applied in two stages, because the Ignition provider can only connect once the gateway is running:

1. `environments/<env>/infra`: the platform and the gateway (kubernetes and helm providers).
2. `environments/<env>/config`: the gateway's configuration (Ignition provider). It reads the database details and the API key from the `infra` state.

## What the gateway module sets, and why

| Setting | Why |
| --- | --- |
| Redundancy with `activeRouting` | Users only ever reach the Active gateway; rolling updates wait for the Backup to sync |
| `restartOnRenewal` | A running gateway does not re-read renewed certificates; restart the pair, Backup first |
| Soft pod anti-affinity | Master and Backup on different nodes when there are several |
| `startupProbe` | Slow starts (e.g. a redundant state transfer) without a lax liveness probe |
| Generated admin and keystore passwords | No chart defaults in a deployed gateway |
| `emptyDir` size limits | A runaway log cannot fill the node |
| NetworkPolicy, with the ingress controller allowed in | Only the namespace and the ingress controller reach the gateway |
| `-Dignition.projects.dir` | Projects come from the image (see [`gateway/`](../gateway/README.md)) |
| A generated API key (8.3) | The `config` stage authenticates with it from the first start; nobody creates a key by hand |
| The seed environment (8.1) | The gateway seeds its own configuration (connection, users, journal, audit and so on) on start |

`ignition_version` (`8.1` or `8.3`) chooses between the last two. The k3s environment takes it from the image tag (`8.3.10-main`, `8.1.55-main`).

## The k3s reference environment

Prerequisites:

- OpenTofu 1.8 or later
- A kubeconfig context for the cluster (`kube_context`, default `default`, the name k3s gives it)
- cert-manager with a ClusterIssuer (`issuer_name`, default `cluster-issuer`)
- Traefik, k3s's default ingress controller

### 1. Choose the image

By default the environment pulls a published image from `ghcr.io/apollogeddon/ignition-gateway` (`image_repository`, with `image_pull_policy = "IfNotPresent"`). Set `image_tag` to a tag CI published, such as `8.3.10-main`, `8.1.55-main` or a release's `8.3.10-1.0.0`. If the package is private, also set `ghcr_username` and `ghcr_token` (a GitHub token with `read:packages`) to create a pull secret.

To run a locally built image instead, import it into k3s's containerd directly:

```sh
docker build -f gateway/Dockerfile -t localhost/ignition-gateway:dev .
docker save localhost/ignition-gateway:dev -o gateway.tar
# on the k3s host (in WSL the file is under /mnt/c/...)
sudo k3s ctr images import gateway.tar
```

Then set `image_repository = "localhost/ignition-gateway"`, `image_tag = "dev"` and `image_pull_policy = "Never"`. Name a local tag after its Ignition version (for example `8.1.55-dev`) when it isn't 8.3, as the environment reads the version from the tag.

### 2. Infra

```sh
cd cluster/environments/k3s/infra
cp k3s.example.tfvars terraform.tfvars   # set image_tag and hostname
tofu init
tofu apply
tofu output -raw admin_password
```

### 3. Config

The Ignition provider is not published to a registry yet. Build it from [ignition-tfpl](https://github.com/apollogeddon/ignition-tfpl) and point OpenTofu at it with a CLI configuration file:

```hcl
# ~/.tofurc (or a file named by TF_CLI_CONFIG_FILE)
provider_installation {
  dev_overrides {
    "apollogeddon/ignition" = "/path/to/folder/with/terraform-provider-ignition"
  }
  direct {}
}
```

The provider authenticates with the API key the `infra` stage generated, which the gateway installed for itself. `config` reads it from the `infra` state; set the `ignition_token` variable to use another:

```sh
cd cluster/environments/k3s/config
tofu init
tofu apply
```

On 8.1 there is no `config` stage to run: the gateway seeds itself on start from `gateway/seed/seed.json`. The seeded users' password is `tofu output -raw demo_users_password` in `infra`.
