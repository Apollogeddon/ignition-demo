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
  }
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.3"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig
  config_context = var.kube_context
}

provider "helm" {
  kubernetes = {
    config_path    = var.kubeconfig
    config_context = var.kube_context
  }
}
