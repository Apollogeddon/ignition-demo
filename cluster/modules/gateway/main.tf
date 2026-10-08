# The Ignition gateway: the ignition-failover chart running the demo image,
# with the settings this repository treats as best practice.

locals {
  projects_dir = "/usr/local/bin/ignition/assets/projects"

  values = {
    applicationName = var.name
    image = {
      repository       = var.image_repository
      tag              = var.image_tag
      pullPolicy       = var.image_pull_policy
      imagePullSecrets = [for name in var.image_pull_secrets : { name = name }]
    }
    certManager = {
      issuer = { name = var.issuer.name, kind = var.issuer.kind }
      # a running gateway does not re-read renewed certificates: restart the
      # pair (Backup first) when they change
      restartOnRenewal = { enabled = var.redundancy }
    }
    affinity = { enabled = var.redundancy, type = "soft" }
    ignition = {
      args = [
        "-m", tostring(var.memory_mb),
        "-n", "$(GATEWAY_SYSTEM_NAME)",
        "--",
        "gateway.useProxyForwardedHeader=true",
        # projects come from the image, not the data volume (see gateway/)
        "-Dignition.projects.dir=${local.projects_dir}",
        "-Dignition.projects.scanFrequency=60",
      ]
      secrets = merge({
        GATEWAY_ADMIN_USERNAME         = "admin"
        GATEWAY_ADMIN_PASSWORD         = local.admin_password
        IGNITION_GAN_KEYSTORE_PASSWORD = random_password.keystore["gan"].result
        IGNITION_WEB_KEYSTORE_PASSWORD = random_password.keystore["web"].result
      }, local.gateway_environment)
      redundancy = { enabled = var.redundancy }
      # user traffic only ever reaches the Active gateway
      activeRouting = { enabled = var.redundancy }
      service       = { type = "ClusterIP" }
      resources = {
        requests = { cpu = "500m", memory = "${var.memory_mb + 512}Mi" }
        limits   = { cpu = "2", memory = "${var.memory_mb * 2}Mi" }
      }
      startupProbe = { enabled = true }
      networkPolicy = {
        enabled = true
        extraIngress = var.ingress == null ? [] : [{
          from = [{
            namespaceSelector = {
              matchLabels = { "kubernetes.io/metadata.name" = var.ingress.namespace }
            }
          }]
        }]
      }
      ingress = {
        enabled     = var.ingress != null
        className   = try(var.ingress.class_name, "")
        annotations = try(var.ingress.annotations, {})
        hosts       = var.ingress == null ? [] : [{ host = var.ingress.host, paths = [{ path = "/", pathType = "Prefix" }] }]
        tls = try(var.ingress.tls_secret, null) == null ? [] : [{
          hosts      = [var.ingress.host]
          secretName = var.ingress.tls_secret
        }]
      }
      emptyDirSizeLimit = { logs = "512Mi", temp = "1Gi", dotIgnition = "256Mi" }
    }
  }
}

resource "random_password" "admin" {
  count   = var.admin_password == null ? 1 : 0
  length  = 20
  special = false
}

# 8.3: an API key the gateway installs from GATEWAY_API_TOKEN on start (see
# gateway/api-token.sh), for the ignition provider; 32 random bytes, base64url
resource "random_bytes" "api_token" {
  count  = var.ignition_version == "8.3" ? 1 : 0
  length = 32
}

locals {
  api_token           = var.ignition_version == "8.3" ? "${var.api_token_name}:${replace(replace(replace(random_bytes.api_token[0].base64, "+", "-"), "/", "_"), "=", "")}" : null
  gateway_environment = var.ignition_version == "8.3" ? { GATEWAY_API_TOKEN = local.api_token } : var.seed_environment
}

resource "random_password" "keystore" {
  for_each = toset(["gan", "web"])
  length   = 20
  special  = false
}

locals {
  admin_password = coalesce(var.admin_password, try(random_password.admin[0].result, null))
}

resource "helm_release" "gateway" {
  name       = var.name
  namespace  = var.namespace
  repository = "https://apollogeddon.github.io/ignition-helm"
  chart      = "ignition-failover"
  version    = var.chart_version

  values = [yamlencode(local.values), yamlencode(var.values)]

  # a redundant pair commissions, syncs and only then reports Ready
  timeout = 1200
  wait    = true
}
