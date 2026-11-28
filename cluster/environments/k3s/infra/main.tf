# The k3s reference environment, cluster side: the platform (namespace and
# database) and the gateway. ../config then configures the running gateway.

locals {
  gateway_name = "ignition"
  # the image tag starts with its Ignition version (8.3.10-2.0.1, 8.1-dev), which
  # image_tag's validation ensures
  ignition_version = regex("^8\\.[13]", var.image_tag)
}

# 8.1: the password of the demo users the seed creates
resource "random_password" "demo_users" {
  length  = 20
  special = false
}

module "platform" {
  source = "../../../modules/platform"

  namespace   = var.namespace
  db_init_dir = "${path.root}/../../../../database/init"
  # the gateway's pods, by the chart's name label
  db_client_labels = { "app.kubernetes.io/name" = local.gateway_name }
  storage_class    = var.storage_class
  registry = var.ghcr_token == null ? null : {
    server   = "ghcr.io"
    username = var.ghcr_username
    password = var.ghcr_token
  }
}

module "gateway" {
  source = "../../../modules/gateway"

  namespace          = module.platform.namespace
  name               = local.gateway_name
  accept_eula        = var.accept_eula
  chart_path         = var.chart_path
  timeout            = var.gateway_timeout
  atomic             = var.gateway_atomic
  admin_password     = var.admin_password
  license_key        = var.license_key
  activation_token   = var.activation_token
  image_repository   = var.image_repository
  image_tag          = var.image_tag
  image_digest       = var.image_digest
  image_pull_policy  = var.image_pull_policy
  image_pull_secrets = module.platform.image_pull_secrets
  ignition_version   = local.ignition_version
  # 8.1: variables of the seed spec (gateway/seed/seed.json); 8.3 is
  # configured by ../config through the REST API instead
  seed_environment = {
    GATEWAY_DB_DEMO_URL      = "jdbc:postgresql://${module.platform.db_host}:${module.platform.db_port}/${module.platform.db_name}"
    GATEWAY_DB_DEMO_USER     = module.platform.db_user
    GATEWAY_DB_DEMO_PASSWORD = module.platform.db_password
    DEMO_USERS_PASSWORD      = random_password.demo_users.result
  }
  redundancy  = var.redundancy
  persistence = { storage_class = var.storage_class }
  # nightly .gwbk downloads through the ingress (see the module's backup input)
  backup = { storage_class = var.storage_class }
  issuer = { name = var.issuer_name }
  ingress = {
    host       = var.hostname
    class_name = "traefik"
    namespace  = "kube-system"
    tls_secret = "ignition-ingress-tls"
    annotations = merge({
      "cert-manager.io/cluster-issuer" = var.issuer_name
      # HTTPS only: Traefik serves an Ingress on every entrypoint unless told
      # otherwise, so plain HTTP would reach the gateway (and its logins) too
      "traefik.ingress.kubernetes.io/router.entrypoints" = "websecure"
      "traefik.ingress.kubernetes.io/router.tls"         = "true"
    }, var.ingress_annotations)
  }
}

# Plain HTTP only redirects to HTTPS: a Traefik Middleware, and an Ingress on the
# web entrypoint that applies it (its backend is never reached)
resource "kubernetes_manifest" "https_redirect" {
  count = var.http_redirect ? 1 : 0
  manifest = {
    apiVersion = "traefik.io/v1alpha1"
    kind       = "Middleware"
    metadata = {
      name      = "${local.gateway_name}-https-redirect"
      namespace = module.platform.namespace
    }
    spec = {
      redirectScheme = { scheme = "https", permanent = true }
    }
  }
}

resource "kubernetes_ingress_v1" "http_redirect" {
  count = var.http_redirect ? 1 : 0
  metadata {
    name      = "${local.gateway_name}-http-redirect"
    namespace = module.platform.namespace
    annotations = {
      "traefik.ingress.kubernetes.io/router.entrypoints" = "web"
      "traefik.ingress.kubernetes.io/router.middlewares" = "${module.platform.namespace}-${kubernetes_manifest.https_redirect[0].manifest.metadata.name}@kubernetescrd"
    }
  }
  spec {
    ingress_class_name = "traefik"
    rule {
      host = var.hostname
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = module.gateway.service
              port {
                number = 8088
              }
            }
          }
        }
      }
    }
  }
}
