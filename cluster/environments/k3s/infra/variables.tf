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

variable "ingress_annotations" {
  description = "Extra annotations for the gateway's Ingress, merged over the environment's (cert-manager's issuer, and Traefik's websecure entrypoint with TLS)"
  type        = map(string)
  default     = {}
}

variable "http_redirect" {
  description = "Redirect plain HTTP to HTTPS, with a Traefik Middleware and an Ingress on the web entrypoint; false leaves port 80 unrouted"
  type        = bool
  default     = true
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

variable "admin_password" {
  description = "Gateway admin password; null generates one (tofu output -raw admin_password)"
  type        = string
  default     = null
  sensitive   = true
}

variable "license_key" {
  description = "Ignition license key the gateway activates on start; null to license it by hand or run a trial"
  type        = string
  default     = null
  sensitive   = true
}

variable "activation_token" {
  description = "Activation token for a leased license key; null for none"
  type        = string
  default     = null
  sensitive   = true
}

variable "storage_class" {
  description = "StorageClass for the gateways' and the database's volumes and their backups; null uses the cluster default (k3s's local-path)"
  type        = string
  default     = null
}
