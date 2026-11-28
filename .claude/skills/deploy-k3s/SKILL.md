---
name: deploy-k3s
description: Walk the k3s reference environment (cluster/environments/k3s) through state, encryption, the image, the infra stage and the config stage, as cluster/README.md describes, and troubleshoot a failed deploy. Use when the user asks to deploy to, upgrade or debug the k3s cluster.
disable-model-invocation: true
---

`cluster/README.md` ("Deploying to k3s") is the source of truth: re-read it if it has changed. Confirm each checklist item with the user. **Stop and ask before every `apply`, `kubectl create/apply/delete` or `init -migrate-state`**, show the plan first, and never read or print `terraform.tfvars`, `backend.hcl`, the state or the passphrase.

## Checklist

1. **Prerequisites:** OpenTofu ≥ 1.8 (CI uses 1.13.1), a kubeconfig context (`kube_context`, default `default`), cert-manager with a ClusterIssuer (`issuer_name`, default `cluster-issuer`), and Traefik with its CRDs. Check them read-only: `kubectl --context <ctx> get clusterissuer`, and `kubectl get crd middlewares.traefik.io`.
2. **State namespace:** `kubectl create namespace tofu-state` (ask first).
3. **backend.hcl:** `cp backend.hcl.example backend.hcl` in `infra/` and `config/`. If the user changes infra's `secret_suffix`/`namespace`, `config`'s `infra_state` must match it.
4. **Passphrase:** the user runs `export TF_VAR_state_passphrase=...` (at least 16 characters, the same for both stages) in their own shell. Never write it to a file. Losing it loses the state.
5. **Image:** a release tag `<ignition version>-<release>` (not `latest` or `-main`), optionally with `image_digest` from `images-<version>.txt`. For a local build:
   1. `docker build -f gateway/Dockerfile -t localhost/ignition-gateway:8.3-dev .`
   2. `docker save` the image, then `sudo k3s ctr images import` it on the node.
   3. Set `image_pull_policy = "Never"`.
6. **tfvars:** `cp k3s.example.tfvars terraform.tfvars` in `infra/`. The **user** sets `accept_eula = true` after reading the EULA: never set it for them. They also set `image_tag` and `hostname` (resolvable from their machine and from inside the cluster; `<ip>.nip.io` works), and pass licensing as `TF_VAR_license_key`/`TF_VAR_activation_token`. Set `chart_path` only for an unreleased chart; the module builds its `file://` dependencies itself.
7. **Infra:**

   ```sh
   tofu -chdir=cluster/environments/k3s/infra init -backend-config=backend.hcl
   tofu -chdir=cluster/environments/k3s/infra plan -out=infra.tfplan   # review with the user
   tofu -chdir=cluster/environments/k3s/infra apply infra.tfplan       # only on their go-ahead
   ```

8. **Config (8.3 only):** install the Ignition provider through its network mirror in `~/.tofurc` or `TF_CLI_CONFIG_FILE`. For a private CA, set `SSL_CERT_FILE` to the system bundle with the CA appended (`cat /etc/ssl/certs/ca-certificates.crt my-ca.crt > ca-bundle.pem`). `allow_insecure_tls = true` is for a throwaway cluster only. Then `init -backend-config=backend.hcl`, `plan`, ask, `apply`. On 8.1 the seed configures the gateway: there's no config stage.
9. **Report** the URL (`https://<hostname>`). The user can read the admin password with `tofu output -raw admin_password`, and on 8.1 the seeded users' with `demo_users_password`. Let them run it, so the passwords stay out of the transcript.

## Troubleshooting

- **Pod Security rejects a pod** (`violates PodSecurity "restricted"`, e.g. the database or a CronJob): set `run_as_non_root = true` on every container and pod, with restricted's other settings, as kubernetes provider 3.5 sends an unset one as `false`. Add it in the module, with a `tofu test` assertion.
- **`ErrImageNeverPull`:** with `image_pull_policy = "Never"`, the node's containerd has no image named exactly `image_repository:image_tag` (`localhost/ignition-gateway:8.3-dev`). Check with `sudo k3s ctr images ls | grep ignition-gateway`, and import it on every node that can run the pod.
- **`no matches for kind "Middleware"`** at plan: the Traefik CRDs (`traefik.io/v1alpha1`) are missing. Install Traefik's CRDs, or set `http_redirect = false` to leave port 80 unrouted.
- **The config apply gets 401/403:** the key goes over HTTPS only. Check that the ingress has TLS, that the gateway restarted once after commissioning (the key's grants), and that `config` read infra's state with the same passphrase.
- **State locked:** another apply holds the Lease. Only use `tofu force-unlock` once the user confirms that nothing else is running.
- **x509 errors from the provider:** the `SSL_CERT_FILE` bundle (step 8).
