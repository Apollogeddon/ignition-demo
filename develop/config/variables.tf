variable "gateway_url" {
  description = "The develop gateway, as this machine reaches it"
  type        = string
  default     = "http://localhost:8088"
}

variable "ignition_token" {
  description = "GATEWAY_API_TOKEN from develop/.env (name:secret); or set IGNITION_TOKEN"
  type        = string
  default     = null
  sensitive   = true
}

variable "db_password" {
  description = "DB_PASSWORD from develop/.env"
  type        = string
  sensitive   = true
}
