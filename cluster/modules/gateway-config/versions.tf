terraform {
  required_version = ">= 1.8"
  required_providers {
    ignition = {
      # not on a registry: see cluster/README.md for installing it from its network mirror
      source  = "apollogeddon/ignition"
      version = "~> 1.1"
    }
  }
}
