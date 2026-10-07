# The k3s reference environment, cluster side: the platform (namespace and
# database) and the gateway. ../config then configures the running gateway.

locals {
  gateway_name = "ignition"
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
  redundancy         = var.redundancy
  issuer             = { name = var.issuer_name }
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
