terraform {
  required_version = ">= 1.8"
  required_providers {
    ignition = {
      # not on a registry yet: see cluster/README.md for installing a release
      source  = "apollogeddon/ignition"
      version = "~> 1.1"
    }
  }
}

provider "ignition" {
  host  = var.gateway_url
  token = var.ignition_token
}
