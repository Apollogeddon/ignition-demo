# The k3s reference environment, gateway side: configure the gateway that
# ../infra deployed, through its REST API.

# the infra stage's state, from the same backend (and decrypted with the same
# passphrase: see versions.tf)
data "terraform_remote_state" "infra" {
  backend = "kubernetes"
  config = {
    secret_suffix  = var.infra_state.secret_suffix
    namespace      = var.infra_state.namespace
    config_path    = var.infra_state.config_path
    config_context = var.infra_state.config_context
  }
}

module "resources" {
  source = "../../../modules/resources"

  database = data.terraform_remote_state.infra.outputs.database
}

# the module was called gateway_config: move existing state instead of recreating it
moved {
  from = module.gateway_config
  to   = module.resources
}
