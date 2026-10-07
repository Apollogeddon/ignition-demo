terraform {
  required_version = ">= 1.8"
  required_providers {
    ignition = {
      # not on a registry yet: see deploy/README.md for installing it
      source = "apollogeddon/ignition"
    }
  }
}
