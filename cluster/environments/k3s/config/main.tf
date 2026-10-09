# The k3s reference environment, gateway side: configure the gateway that
# ../infra deployed, through its REST API.

data "terraform_remote_state" "infra" {
  backend = "local"
  config = {
    path = "${path.root}/../infra/terraform.tfstate"
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
