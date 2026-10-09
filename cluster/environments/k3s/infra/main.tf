# The k3s reference environment, cluster side: the platform (namespace and
# database) and the gateway. ../config then configures the running gateway.

locals {
  gateway_name = "ignition"
  # the image tag starts with its Ignition version (8.3.10-main, 8.1.55-main)
  ignition_version = startswith(var.image_tag, "8.1") ? "8.1" : "8.3"
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
  ignition_version   = local.ignition_version
  # 8.1: variables of the seed spec (gateway/seed/seed.json); 8.3 is
  # configured by ../config through the REST API instead
  seed_environment = {
    GATEWAY_DB_DEMO_URL      = "jdbc:postgresql://${module.platform.db_host}:${module.platform.db_port}/${module.platform.db_name}"
    GATEWAY_DB_DEMO_USER     = module.platform.db_user
    GATEWAY_DB_DEMO_PASSWORD = module.platform.db_password
    DEMO_USERS_PASSWORD      = random_password.demo_users.result
  }
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
