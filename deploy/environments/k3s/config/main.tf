# The k3s reference environment, gateway side: configure the gateway that
# ../infra deployed, through its REST API.

data "terraform_remote_state" "infra" {
  backend = "local"
  config = {
    path = "${path.root}/../infra/terraform.tfstate"
  }
}

module "gateway_config" {
  source = "../../../modules/gateway-config"

  database = data.terraform_remote_state.infra.outputs.database
}
