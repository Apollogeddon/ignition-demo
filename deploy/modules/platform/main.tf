# The platform the gateway runs on: its namespace and the demo PostgreSQL
# database, initialised from db/init on first start.

locals {
  namespace = var.create_namespace ? kubernetes_namespace_v1.this[0].metadata[0].name : var.namespace
  labels = {
    "app.kubernetes.io/name"       = "database"
    "app.kubernetes.io/part-of"    = "ignition-demo"
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
      "app.kubernetes.io/part-of"          = "ignition-demo"
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
          readiness_probe {
            exec {
              command = ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""]
            }
            period_seconds = 5
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

# Only the gateways may reach the database
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
    policy_types = ["Ingress"]
    ingress {
      from {
        pod_selector {
          match_labels = var.db_client_labels
        }
      }
      ports {
        port     = "5432"
        protocol = "TCP"
      }
    }
  }
}
