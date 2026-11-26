variable "state_passphrase" {
  description = "Passphrase the state and plans are encrypted with (at least 16 characters); set TF_VAR_state_passphrase rather than a file. Both stages use the same one"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.state_passphrase) >= 16
    error_message = "state_passphrase must be at least 16 characters."
  }
}

variable "kubeconfig" {
  description = "kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubeconfig context of the k3s cluster"
  type        = string
  default     = "default"
}

variable "namespace" {
  description = "Namespace for the demo"
  type        = string
  default     = "ignition"
}

variable "image_repository" {
  description = "Gateway image repository"
  type        = string
  default     = "ghcr.io/apollogeddon/ignition-gateway"
}

variable "image_tag" {
  description = "Gateway image tag, starting with its Ignition version: a release's <ignition version>-<release version>, a commit's <ignition version>-sha-<commit>, or a local <ignition version>-<name>"
  type        = string

  validation {
    condition     = can(regex("^8\\.[13](\\.[0-9]+)?-[A-Za-z0-9_.-]+$", var.image_tag))
    error_message = "image_tag must start with its Ignition version (8.1 or 8.3, e.g. 8.3.10-2.0.1 or 8.1-dev), which chooses how the gateway is configured."
  }
  validation {
    condition     = !can(regex("(^|-)(latest|main)$", var.image_tag))
    error_message = "image_tag must not be a moving tag (latest, <ignition version>-main), which CI re-pushes on every merge: use a release's tag, a commit's sha- tag, or pin image_digest."
  }
}

variable "image_digest" {
  description = "Digest (sha256:...) pinning image_tag, e.g. from a release's images-<version>.txt; null for the tag alone"
  type        = string
  default     = null
}

variable "image_pull_policy" {
  description = "IfNotPresent for a registry; Never for an image imported into k3s directly (see cluster/README.md)"
  type        = string
  default     = "IfNotPresent"
}

variable "ghcr_token" {
  description = "GitHub token with read:packages, when the GHCR package is private; null for a public package"
  type        = string
  default     = null
  sensitive   = true
}

variable "ghcr_username" {
  description = "GitHub user owning ghcr_token"
  type        = string
  default     = null
}

variable "hostname" {
  description = "Host name for the gateway web UI (through traefik)"
  type        = string
}

variable "issuer_name" {
  description = "cert-manager ClusterIssuer for the gateway and ingress certificates"
  type        = string
  default     = "cluster-issuer"
}

variable "redundancy" {
  description = "Run a redundant Master/Backup pair"
  type        = bool
  default     = true
}

variable "accept_eula" {
  description = "Accept the Ignition EULA (https://inductiveautomation.com/ignition/license); the gateway module requires true"
  type        = bool
}
