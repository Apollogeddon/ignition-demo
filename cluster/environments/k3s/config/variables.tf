variable "gateway_url" {
  description = "Gateway URL to configure; null uses the infra stage's ingress URL"
  type        = string
  default     = null
}

variable "ignition_token" {
  description = "Gateway API key (name:secret) with read and write access; or set IGNITION_TOKEN"
  type        = string
  default     = null
  sensitive   = true
}

variable "allow_insecure_tls" {
  description = "Accept the gateway's certificate without verifying it (the demo issuer is a private CA)"
  type        = bool
  default     = true
}
