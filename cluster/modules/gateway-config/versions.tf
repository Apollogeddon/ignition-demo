terraform {
  required_version = ">= 1.8"
  required_providers {
    ignition = {
      # not on a registry yet: see cluster/README.md for installing it
      source = "apollogeddon/ignition"
    }
  }
}
