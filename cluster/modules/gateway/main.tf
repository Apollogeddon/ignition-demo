# The Ignition gateway: the ignition-failover chart running the demo image,
# with the settings this repository treats as best practice.

locals {
  projects_dir = "/usr/local/bin/ignition/assets/projects"

  values = {
    applicationName = var.name
    # the chart's own EULA switch (validated by accept_eula); a chart before it has
    # no values schema, so the key is simply unused there
    acceptEula = var.accept_eula
    image = {
      repository = var.image_repository
      # the chart renders repository:tag, so a digest rides on the tag
      tag              = var.image_digest == null ? var.image_tag : "${var.image_tag}@${var.image_digest}"
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
      args = concat([
        "-m", tostring(var.memory_mb),
        "-n", "$(GATEWAY_SYSTEM_NAME)",
        "--",
        ], var.ingress == null ? [] : [
        # the gateway believes X-Forwarded-Proto from whoever reaches its HTTP port, so
        # only with an ingress, and the NetworkPolicy keeps that to the ingress's namespace
        # and the release's own (see api_token_require_tls)
        "gateway.useProxyForwardedHeader=true",
        ], [
        # projects come from the image, not the data volume (see gateway/)
        "-Dignition.projects.dir=${local.projects_dir}",
        "-Dignition.projects.scanFrequency=60",
      ])
      redundancy = { enabled = var.redundancy }
      # user traffic only ever reaches the Active gateway
      activeRouting = { enabled = var.redundancy }
      service       = { type = "ClusterIP" }
      resources = {
        requests = { cpu = "500m", memory = "${var.memory_mb + 512}Mi" }
        limits   = { cpu = "2", memory = "${var.memory_mb * 2}Mi" }
      }
      # the chart's health checks, stated so a chart default can't drop them:
      # readiness waits for the gateway to be running (and, with active routing,
      # a Backup in sync), liveness restarts a gateway that stops answering, and
      # the startup probe holds both off through a slow first start
      readinessProbe = { enabled = true }
      livenessProbe  = { enabled = true }
      startupProbe   = { enabled = true }
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
      persistence = {
        size = var.persistence.size
        # "" is the chart's default: the cluster's default StorageClass
        storageClassName = var.persistence.storage_class == null ? "" : var.persistence.storage_class
      }
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
  api_token = var.ignition_version == "8.3" ? "${var.api_token_name}:${replace(replace(replace(random_bytes.api_token[0].base64, "+", "-"), "/", "_"), "=", "")}" : null
  gateway_environment = var.ignition_version == "8.3" ? {
    GATEWAY_API_TOKEN             = local.api_token
    GATEWAY_API_TOKEN_REQUIRE_TLS = tostring(var.api_token_require_tls)
  } : var.seed_environment
}

resource "random_password" "keystore" {
  for_each = toset(["gan", "web"])
  length   = 20
  special  = false
}

locals {
  admin_password = coalesce(var.admin_password, try(random_password.admin[0].result, null))

  # The gateway's secret environment: passwords, licensing, and the API key (8.3)
  # or the seed's variables (8.1)
  secret_environment = merge(
    {
      GATEWAY_ADMIN_USERNAME         = "admin"
      GATEWAY_ADMIN_PASSWORD         = local.admin_password
      IGNITION_GAN_KEYSTORE_PASSWORD = random_password.keystore["gan"].result
      IGNITION_WEB_KEYSTORE_PASSWORD = random_password.keystore["web"].result
    },
    # the variables the Ignition image reads to activate a license on start
    var.license_key == null ? {} : { IGNITION_LICENSE_KEY = var.license_key },
    var.activation_token == null ? {} : { IGNITION_ACTIVATION_TOKEN = var.activation_token },
    local.gateway_environment,
  )

  # From chart 5 (or a local chart) the gateway reads a Secret this module owns
  # (ignition.existingSecret), which External Secrets can replace; an earlier chart
  # renders its own from ignition.secrets, with the same values
  existing_secret = var.chart_path != null || tonumber(regex("^[0-9]+", var.chart_version)) >= 5
  secret_name     = local.existing_secret ? "${var.name}-gateway" : "${var.name}-secrets"
  secret_values = (local.existing_secret
    ? yamlencode({ ignition = { existingSecret = local.secret_name } })
    : yamlencode({ ignition = { secrets = local.secret_environment } })
  )
}

resource "kubernetes_secret_v1" "gateway" {
  count = local.existing_secret ? 1 : 0
  metadata {
    name      = local.secret_name
    namespace = var.namespace
    labels = {
      "app.kubernetes.io/part-of"    = "ignition"
      "app.kubernetes.io/managed-by" = "opentofu"
    }
  }
  data = local.secret_environment
}

# A local chart (chart_path) is upgraded only when its version changes, so an
# edit at the same version would plan no change: a hash of its files, and of
# the file:// dependencies it builds from (the ignition-helm checkout's
# charts/common), goes in the release's description, whose change upgrades it.
# Left out: charts/ (built from those dependencies on each install and upgrade),
# Chart.lock (rewritten by that build), and the unrendered tests/ and ci/.
locals {
  chart_manifest = var.chart_path == null ? null : try(yamldecode(file("${var.chart_path}/Chart.yaml")), null)
  chart_sources = local.chart_manifest == null ? {} : merge(
    { for dep in try(local.chart_manifest.dependencies, []) :
      dep.name => "${var.chart_path}/${trimprefix(dep.repository, "file://")}"
      if startswith(try(dep.repository, ""), "file://")
    },
    { "." = var.chart_path },
  )
  chart_digest = local.chart_manifest == null ? null : sha256(join("\n", flatten([
    for name, dir in local.chart_sources : [
      for file in sort(fileset(dir, "**")) : "${name}/${file} ${filesha256("${dir}/${file}")}"
      if !can(regex("^(charts/|tests/|ci/|Chart\\.lock$)", file))
    ]
  ])))
}

resource "helm_release" "gateway" {
  name      = var.name
  namespace = var.namespace
  # a local chart (chart_path) for an unreleased chart, else the published one
  repository = var.chart_path == null ? "https://apollogeddon.github.io/ignition-helm" : null
  chart      = coalesce(var.chart_path, "ignition-failover")
  version    = var.chart_path == null ? var.chart_version : null
  # a local chart's file:// dependencies are built from their sources, so an
  # edit to charts/common deploys without a helm dependency build first
  dependency_update = var.chart_path != null
  description       = local.chart_digest == null ? null : "chart_path sha256:${local.chart_digest}"

  values = [yamlencode(local.values), local.secret_values, yamlencode(var.values)]
  # the chart's gateways start with the Secret's environment
  depends_on = [kubernetes_secret_v1.gateway]

  # A redundant pair commissions, syncs and only then reports Ready. atomic
  # uninstalls a first install that fails or times out, which OpenTofu doesn't
  # record, so the next apply installs again instead of failing on a name still
  # in use; a failed upgrade rolls back to the last release, and cleanup_on_fail
  # removes what it added (cluster/README.md, "A failed install").
  timeout         = var.timeout
  wait            = true
  atomic          = var.atomic
  cleanup_on_fail = true

  lifecycle {
    precondition {
      condition     = var.chart_path == null || local.chart_manifest != null
      error_message = "chart_path must be a chart directory with a Chart.yaml, such as an ignition-helm checkout's charts/failover."
    }
    # The gateway would refuse the API key over the ingress, so the first
    # resources apply would fail with 401/403 instead
    precondition {
      condition     = !(var.ignition_version == "8.3" && var.api_token_require_tls && var.ingress != null && try(var.ingress.tls_secret, null) == null)
      error_message = "api_token_require_tls is true, so the gateway only takes its API key over HTTPS, but the ingress has no tls_secret: set ingress.tls_secret, or api_token_require_tls = false for a gateway reached over plain HTTP."
    }
  }
}

# The chart has no pod annotations and doesn't watch existingSecret, so a changed
# Secret (a rotated password, a new license key) would wait for the next restart:
# a hash of it on the pod template rolls the gateways (Backup first) instead. The
# first apply adds it, which restarts the new gateways once.
resource "kubernetes_annotations" "secret_checksum" {
  count       = local.existing_secret ? 1 : 0
  api_version = "apps/v1"
  kind        = "StatefulSet"
  metadata {
    name      = var.name
    namespace = var.namespace
  }
  template_annotations = {
    "checksum/secret" = nonsensitive(sha256(jsonencode(local.secret_environment)))
  }
  depends_on = [helm_release.gateway]
}

# The chart's NetworkPolicy covers the gateways. Its other pods (the
# active-routing labeller and the certificate-renewal CronJob) only call out,
# to the Kubernetes API and the gateways, so nothing may connect to them.
resource "kubernetes_network_policy_v1" "helpers" {
  metadata {
    name      = "${var.name}-helpers"
    namespace = var.namespace
    labels = {
      "app.kubernetes.io/part-of"    = "ignition"
      "app.kubernetes.io/managed-by" = "opentofu"
    }
  }
  spec {
    pod_selector {
      match_labels = { "app.kubernetes.io/instance" = var.name }
      match_expressions {
        key      = "app.kubernetes.io/name"
        operator = "NotIn"
        values   = [var.name]
      }
    }
    policy_types = ["Ingress"]
  }
}

# Backups (8.3): the gateway's own backup, through its REST API with the module's
# API key, into a volume of their own. 8.1 has no REST API, so none there.

locals {
  backup = var.ignition_version == "8.3" && var.backup != null
  backup_url = try(coalesce(
    try(var.backup.url, null),
    try(var.ingress.tls_secret, null) != null ? "https://${var.ingress.host}" : null,
    var.api_token_require_tls ? null : "http://${var.redundancy ? "${var.name}-active" : var.name}.${var.namespace}.svc:8088",
  ), null)
  backup_labels = {
    "app.kubernetes.io/name"       = "${var.name}-backup"
    "app.kubernetes.io/instance"   = var.name
    "app.kubernetes.io/part-of"    = "ignition"
    "app.kubernetes.io/managed-by" = "opentofu"
  }
}

resource "kubernetes_persistent_volume_claim_v1" "backup" {
  count = local.backup ? 1 : 0
  metadata {
    name      = "${var.name}-backup"
    namespace = var.namespace
    labels    = local.backup_labels
  }
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = var.backup.storage_class
    resources {
      requests = { storage = var.backup.storage }
    }
  }
  # a WaitForFirstConsumer class (k3s's local-path) binds on the first backup
  wait_until_bound = false
}

resource "kubernetes_cron_job_v1" "backup" {
  count = local.backup ? 1 : 0
  metadata {
    name      = "${var.name}-backup"
    namespace = var.namespace
    labels    = local.backup_labels
  }
  spec {
    schedule                      = var.backup.schedule
    concurrency_policy            = "Forbid"
    successful_jobs_history_limit = 1
    failed_jobs_history_limit     = 3
    job_template {
      metadata {
        labels = local.backup_labels
      }
      spec {
        backoff_limit = 2
        template {
          metadata {
            labels = local.backup_labels
          }
          spec {
            restart_policy                  = "Never"
            automount_service_account_token = false
            security_context {
              run_as_user     = 65532
              run_as_group    = 65532
              fs_group        = 65532
              run_as_non_root = true
              seccomp_profile {
                type = "RuntimeDefault"
              }
            }
            container {
              name  = "backup"
              image = var.backup.image
              env {
                name  = "GATEWAY_URL"
                value = local.backup_url
              }
              env {
                name = "GATEWAY_API_TOKEN"
                value_from {
                  secret_key_ref {
                    name = local.secret_name
                    key  = "GATEWAY_API_TOKEN"
                  }
                }
              }
              # written under a temporary name and renamed once complete, so a
              # failed run never leaves a truncated backup to restore. curl retries
              # a refused connection (a network policy can hold a new pod for a few
              # seconds) and a transient answer such as a 503 during a failover.
              command = ["sh", "-ec", <<-EOT
                rm -f /backups/*.partial
                f="/backups/gateway-$(date -u +%Y%m%dT%H%M%SZ).gwbk"
                set -- -sSf --max-time 900 --retry 6 --retry-delay 10 --retry-connrefused -o "$f.partial" -H "X-Ignition-API-Token: $GATEWAY_API_TOKEN"
                if [ -s /ca/ca.crt ]; then set -- "$@" --cacert /ca/ca.crt; fi
                curl "$@" "$GATEWAY_URL/data/api/v1/backup"
                mv "$f.partial" "$f"
                find /backups -name '*.gwbk' -mmin +${var.backup.retention_days * 1440} -print -delete
                ls -l /backups
              EOT
              ]
              resources {
                requests = { cpu = "10m", memory = "32Mi" }
                limits   = { cpu = "200m", memory = "128Mi" }
              }
              security_context {
                allow_privilege_escalation = false
                # the provider sends an unset runAsNonRoot as false, which the restricted profile refuses
                run_as_non_root           = true
                read_only_root_filesystem = true
                capabilities {
                  drop = ["ALL"]
                }
              }
              volume_mount {
                name       = "backups"
                mount_path = "/backups"
              }
              dynamic "volume_mount" {
                for_each = try(var.ingress.tls_secret, null) == null ? [] : [1]
                content {
                  name       = "ca"
                  mount_path = "/ca"
                  read_only  = true
                }
              }
            }
            volume {
              name = "backups"
              persistent_volume_claim {
                claim_name = kubernetes_persistent_volume_claim_v1.backup[0].metadata[0].name
              }
            }
            # the ingress certificate's CA, for a private issuer; optional, as a
            # public one's Secret has no ca.crt
            dynamic "volume" {
              for_each = try(var.ingress.tls_secret, null) == null ? [] : [var.ingress.tls_secret]
              content {
                name = "ca"
                secret {
                  secret_name = volume.value
                  optional    = true
                  items {
                    key  = "ca.crt"
                    path = "ca.crt"
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  # the API key's Secret is the chart's own before chart 5
  depends_on = [helm_release.gateway]

  lifecycle {
    precondition {
      condition     = local.backup_url != null
      error_message = "The backup job needs the gateway's URL: with api_token_require_tls the gateway only takes the API key over HTTPS, and the ingress has none. Set backup.url, or backup = null."
    }
  }
}
