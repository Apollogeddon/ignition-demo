variable "gateway_url" {
  description = "The develop gateway, as this machine reaches it"
  type        = string
  default     = "http://localhost:8088"
}

variable "ignition_token" {
  description = "Gateway API key (name:secret) with read and write access; or set IGNITION_TOKEN"
  type        = string
  default     = null
  sensitive   = true
}

variable "db_password" {
  description = "DB_PASSWORD from develop/.env"
  type        = string
  sensitive   = true
}
