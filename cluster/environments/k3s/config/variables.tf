variable "state_passphrase" {
  description = "Passphrase the state and plans are encrypted with (at least 16 characters); set TF_VAR_state_passphrase rather than a file. Both stages use the same one"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.state_passphrase) >= 16
    error_message = "state_passphrase must be at least 16 characters."
  }
}

variable "infra_state" {
  description = "Where the infra stage keeps its state: the values of its backend.hcl"
  type = object({
    secret_suffix  = optional(string, "ignition-infra")
    namespace      = optional(string, "tofu-state")
    config_path    = optional(string, "~/.kube/config")
    config_context = optional(string, "default")
  })
  default = {}
}

variable "gateway_url" {
  description = "Gateway URL to configure; null uses the infra stage's ingress URL"
  type        = string
  default     = null
}

variable "ignition_token" {
  description = "Gateway API key (name:secret); null uses the key the infra stage generated"
  type        = string
  default     = null
  sensitive   = true
}

variable "allow_insecure_tls" {
  description = "Accept the gateway's certificate without verifying it, which exposes the API key to anyone who can intercept; for a throwaway local cluster only (cluster/README.md)"
  type        = bool
  default     = false
}
