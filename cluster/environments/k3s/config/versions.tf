terraform {
  required_version = ">= 1.8"
  required_providers {
    ignition = {
      source = "apollogeddon/ignition"
    }
  }
}

provider "ignition" {
  host               = coalesce(var.gateway_url, data.terraform_remote_state.infra.outputs.gateway_url)
  token              = var.ignition_token
  allow_insecure_tls = var.allow_insecure_tls
}
