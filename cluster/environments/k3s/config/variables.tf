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
