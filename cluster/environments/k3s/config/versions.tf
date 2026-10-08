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
  token              = try(coalesce(var.ignition_token, data.terraform_remote_state.infra.outputs.api_token), null)
  allow_insecure_tls = var.allow_insecure_tls
}
