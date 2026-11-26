terraform {
  required_version = ">= 1.8"

  # State in a Secret in the cluster, locked with a Lease, through a partial
  # configuration: tofu init -backend-config=backend.hcl (see backend.hcl.example)
  backend "kubernetes" {}

  # State and plans are encrypted with a key derived from state_passphrase
  # (TF_VAR_state_passphrase), as both hold every password. Not enforced, so that
  # migrating unencrypted state can add an unencrypted fallback through
  # TF_ENCRYPTION, for that one run only (cluster/README.md).
  encryption {
    key_provider "pbkdf2" "state" {
      passphrase = var.state_passphrase
    }
    method "aes_gcm" "state" {
      keys = key_provider.pbkdf2.state
    }
    state {
      method = method.aes_gcm.state
    }
    plan {
      method = method.aes_gcm.state
    }
    # the infra stage's state, encrypted with the same passphrase
    remote_state_data_sources {
      default {
        method = method.aes_gcm.state
      }
    }
  }
  required_providers {
    ignition = {
      source  = "apollogeddon/ignition"
      version = "~> 1.2.4"
    }
  }
}

provider "ignition" {
  host               = coalesce(var.gateway_url, data.terraform_remote_state.infra.outputs.gateway_url)
  token              = try(coalesce(var.ignition_token, data.terraform_remote_state.infra.outputs.api_token), null)
  allow_insecure_tls = var.allow_insecure_tls
}
