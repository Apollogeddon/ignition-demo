terraform {
  required_version = ">= 1.8"
  required_providers {
    ignition = {
      # not on a registry: see cluster/README.md for installing it from its network mirror
      source  = "apollogeddon/ignition"
      version = "~> 1.2"
    }
  }
}

provider "ignition" {
  host  = var.gateway_url
  token = var.ignition_token
}
