# The platform the gateway runs on: its namespace and the demo PostgreSQL
# database, initialised from database/init on first start.

locals {
  namespace = var.create_namespace ? kubernetes_namespace_v1.this[0].metadata[0].name : var.namespace
  labels = {
    "app.kubernetes.io/name"       = "database"
    "app.kubernetes.io/part-of"    = "ignition"
    "app.kubernetes.io/managed-by" = "opentofu"
  }
  init_files = { for f in fileset(var.db_init_dir, "*.sql") : f => file("${var.db_init_dir}/${f}") }
}

resource "kubernetes_namespace_v1" "this" {
  count = var.create_namespace ? 1 : 0
  metadata {
    name = var.namespace
    labels = {
      # the chart runs restricted-compliant pods; enforce it
      "pod-security.kubernetes.io/enforce" = "restricted"
      "app.kubernetes.io/part-of"          = "ignition"
    }
  }
}

resource "random_password" "db" {
  count   = var.db_password == null ? 1 : 0
  length  = 24
  special = false
}

resource "kubernetes_secret_v1" "db" {
  metadata {
    name      = "database"
    namespace = local.namespace
    labels    = local.labels
  }
  data = {
    POSTGRES_DB       = var.db_name
    POSTGRES_USER     = var.db_user
    POSTGRES_PASSWORD = coalesce(var.db_password, try(random_password.db[0].result, null))
  }
}

resource "kubernetes_config_map_v1" "db_init" {
  metadata {
    name      = "database-init"
    namespace = local.namespace
    labels    = local.labels
  }
  data = local.init_files
}

resource "kubernetes_stateful_set_v1" "db" {
  metadata {
    name      = "database"
    namespace = local.namespace
    labels    = local.labels
  }
  spec {
    service_name = "database"
    replicas     = 1
    selector {
      match_labels = local.labels
    }
    template {
      metadata {
        labels = local.labels
        annotations = {
          # init scripts only run on an empty volume; still roll the pod so a
          # changed script is at least visible
          "checksum/init" = sha256(jsonencode(local.init_files))
        }
      }
      spec {
        security_context {
          run_as_user     = 999
          run_as_group    = 999
          fs_group        = 999
          run_as_non_root = true
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name  = "postgres"
          image = var.db_image
          env_from {
            secret_ref {
              name = kubernetes_secret_v1.db.metadata[0].name
            }
          }
          env {
            name  = "PGDATA"
            value = "/var/lib/postgresql/data/pgdata"
          }
          port {
            name           = "postgres"
            container_port = 5432
          }
          # a first start runs the init scripts and restarts the server: the
          # startup probe gives it time, then liveness restarts a hung server
          startup_probe {
            exec {
              command = ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""]
            }
            period_seconds    = 5
            failure_threshold = 60
          }
          readiness_probe {
            exec {
              command = ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""]
            }
            period_seconds = 5
          }
          liveness_probe {
            exec {
              command = ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""]
            }
            period_seconds    = 10
            timeout_seconds   = 5
            failure_threshold = 6
          }
          resources {
            requests = { cpu = "100m", memory = "256Mi" }
            limits   = { cpu = "1", memory = "512Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
          }
          volume_mount {
            name       = "init"
            mount_path = "/docker-entrypoint-initdb.d"
            read_only  = true
          }
          volume_mount {
            name       = "run"
            mount_path = "/var/run/postgresql"
          }
        }
        volume {
          name = "init"
          config_map {
            name = kubernetes_config_map_v1.db_init.metadata[0].name
          }
        }
        volume {
          name = "run"
          empty_dir {}
        }
      }
    }
    volume_claim_template {
      metadata {
        name = "data"
      }
      spec {
        access_modes       = ["ReadWriteOnce"]
        storage_class_name = var.storage_class
        resources {
          requests = { storage = var.db_storage }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "db" {
  metadata {
    name      = "database"
    namespace = local.namespace
    labels    = local.labels
  }
  spec {
    selector = local.labels
    port {
      name        = "postgres"
      port        = 5432
      target_port = "postgres"
    }
  }
}

# Only the gateways (and the backup job) may reach the database, and it reaches
# nothing: it shares the gateways' namespace, whose pods the gateways trust for
# X-Forwarded-Proto
resource "kubernetes_network_policy_v1" "db" {
  metadata {
    name      = "database"
    namespace = local.namespace
    labels    = local.labels
  }
  spec {
    pod_selector {
      match_labels = local.labels
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        pod_selector {
          match_labels = var.db_client_labels
        }
      }
      dynamic "from" {
        for_each = var.db_backup == null ? [] : [local.backup_labels]
        content {
          pod_selector {
            match_labels = from.value
          }
        }
      }
      ports {
        port     = "5432"
        protocol = "TCP"
      }
    }
  }
}

# Pull secret for a private registry (e.g. a private GHCR package)
resource "kubernetes_secret_v1" "registry" {
  count = nonsensitive(var.registry == null) ? 0 : 1
  metadata {
    name      = "registry"
    namespace = local.namespace
    labels    = local.labels
  }
  type = "kubernetes.io/dockerconfigjson"
  data = {
    ".dockerconfigjson" = jsonencode({
      auths = {
        (var.registry.server) = {
          auth = base64encode("${var.registry.username}:${var.registry.password}")
        }
      }
    })
  }
}

# Backups: a nightly pg_dump (custom format, for pg_restore) into a volume of its
# own, keeping db_backup.retention_days of them

locals {
  backup_labels = merge(local.labels, { "app.kubernetes.io/name" = "database-backup" })
}

resource "kubernetes_persistent_volume_claim_v1" "db_backup" {
  count = var.db_backup == null ? 0 : 1
  metadata {
    name      = "database-backup"
    namespace = local.namespace
    labels    = local.backup_labels
  }
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = try(coalesce(var.db_backup.storage_class, var.storage_class), null)
    resources {
      requests = { storage = var.db_backup.storage }
    }
  }
  # a WaitForFirstConsumer class (k3s's local-path) binds on the first backup
  wait_until_bound = false
}

resource "kubernetes_cron_job_v1" "db_backup" {
  count = var.db_backup == null ? 0 : 1
  metadata {
    name      = "database-backup"
    namespace = local.namespace
    labels    = local.backup_labels
  }
  spec {
    schedule                      = var.db_backup.schedule
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
              run_as_user     = 999
              run_as_group    = 999
              fs_group        = 999
              run_as_non_root = true
              seccomp_profile {
                type = "RuntimeDefault"
              }
            }
            container {
              name  = "pg-dump"
              image = var.db_image
              env_from {
                secret_ref {
                  name = kubernetes_secret_v1.db.metadata[0].name
                }
              }
              env {
                name  = "PGHOST"
                value = kubernetes_service_v1.db.metadata[0].name
              }
              # a dump is written under a temporary name and renamed once complete,
              # so a failed run never leaves a truncated dump to restore
              command = ["sh", "-ec", <<-EOT
                rm -f /backups/*.partial
                f="/backups/$POSTGRES_DB-$(date -u +%Y%m%dT%H%M%SZ).dump"
                PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$f.partial"
                mv "$f.partial" "$f"
                find /backups -name '*.dump' -mmin +${var.db_backup.retention_days * 1440} -print -delete
                ls -l /backups
              EOT
              ]
              resources {
                requests = { cpu = "50m", memory = "64Mi" }
                limits   = { cpu = "500m", memory = "256Mi" }
              }
              security_context {
                allow_privilege_escalation = false
                read_only_root_filesystem  = true
                capabilities {
                  drop = ["ALL"]
                }
              }
              volume_mount {
                name       = "backups"
                mount_path = "/backups"
              }
            }
            volume {
              name = "backups"
              persistent_volume_claim {
                claim_name = kubernetes_persistent_volume_claim_v1.db_backup[0].metadata[0].name
              }
            }
          }
        }
      }
    }
  }
}

# The backup job only calls out, to the database
resource "kubernetes_network_policy_v1" "db_backup" {
  count = var.db_backup == null ? 0 : 1
  metadata {
    name      = "database-backup"
    namespace = local.namespace
    labels    = local.backup_labels
  }
  spec {
    pod_selector {
      match_labels = local.backup_labels
    }
    policy_types = ["Ingress"]
  }
}
