# The k3s reference environment, cluster side: the platform (namespace and
# database) and the gateway. ../config then configures the running gateway.

locals {
  gateway_name = "ignition"
  # 8.1 has no REST API: its gateway creates the demo connection on startup
  # (8.3 gets it from ../config)
  legacy_gateway = startswith(var.image_tag, "8.1")
}

module "platform" {
  source = "../../../modules/platform"

  namespace   = var.namespace
  db_init_dir = "${path.root}/../../../../db/init"
  # the gateway's pods, by the chart's name label
  db_client_labels = { "app.kubernetes.io/name" = local.gateway_name }
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
  image_repository   = var.image_repository
  image_tag          = var.image_tag
  image_pull_policy  = var.image_pull_policy
  image_pull_secrets = module.platform.image_pull_secrets
  startup_datasources = local.legacy_gateway ? {
    demo = {
      url      = "jdbc:postgresql://${module.platform.db_host}:${module.platform.db_port}/${module.platform.db_name}"
      user     = module.platform.db_user
      password = module.platform.db_password
    }
  } : {}
  redundancy = var.redundancy
  issuer     = { name = var.issuer_name }
  ingress = {
    host       = var.hostname
    class_name = "traefik"
    namespace  = "kube-system"
    tls_secret = "ignition-ingress-tls"
    annotations = {
      "cert-manager.io/cluster-issuer" = var.issuer_name
    }
  }
}
