---
title: Cluster
description: OpenTofu modules that deploy and configure the gateway on Kubernetes.
---

`cluster/` holds OpenTofu modules and one root module per environment. `k3s` is the reference environment.

| Module | What it manages |
| --- | --- |
| `modules/platform` | The namespace (restricted Pod Security) and the demo PostgreSQL database, initialised from `db/init` |
| `modules/gateway` | The [ignition-failover](https://apollogeddon.github.io/ignition-helm/) chart running the gateway image |
| `modules/gateway-config` | Gateway resources through the REST API: the database connection and alarm journal |

Each environment is applied in two stages, because the Ignition provider can only connect once the gateway is running:

1. `environments/<env>/infra`: the platform and the gateway (kubernetes and helm providers)
2. `environments/<env>/config`: the gateway's configuration (Ignition provider); it reads the database details from the `infra` state

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
| `-Dignition.projects.dir` | Projects come from the image (see [Gateway Image](../gateway-image/)) |

## Deploying to k3s

Prerequisites: OpenTofu 1.8+, the `Ubuntu-k3s` kube context, cert-manager with the `ignition-cluster-issuer` ClusterIssuer, and traefik (k3s's default ingress controller).

### 1. Build the image and load it into k3s

The reference cluster has no registry, so the image is imported into k3s's containerd directly and pulled with `imagePullPolicy: Never`:

```sh
docker build -f gateway/Dockerfile -t localhost/ignition-gateway:dev .
docker save localhost/ignition-gateway:dev -o gateway.tar
# on the k3s host (in WSL the file is under /mnt/c/...)
sudo k3s ctr images import gateway.tar
```

With a registry, push the image there instead and set `image_repository` and `image_pull_policy = "IfNotPresent"`.

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

The provider authenticates with a gateway API key that has read and write access (create one in the gateway web UI's API key settings):

```sh
cd cluster/environments/k3s/config
export IGNITION_TOKEN='<name>:<secret>'
tofu apply
```
