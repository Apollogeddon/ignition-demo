variable "database" {
  description = "The demo database the gateway connects to"
  type = object({
    host     = string
    port     = optional(number, 5432)
    name     = string
    user     = string
    password = string
  })
  sensitive = true
}

variable "connection_name" {
  description = "Name of the gateway's database connection (the projects' named queries use it)"
  type        = string
  default     = "demo"
}

variable "alarm_journal" {
  description = "Store alarm events in the demo database; null for no journal"
  type = object({
    name         = optional(string, "demo")
    table        = optional(string, "alarm_events")
    min_priority = optional(string, "Low")
  })
  default = {}
}

variable "user_source" {
  description = "Internal user source (and an identity provider using it) for the project's users; null for none"
  type = object({
    name        = optional(string, "demo")
    description = optional(string, "Demo operators and engineers")
  })
  default = {}
}

variable "audit_profile" {
  description = "Audit profile in the demo database (logins and configuration changes); null for none"
  type = object({
    name           = optional(string, "logins")
    table          = optional(string, "audit_events")
    retention_days = optional(number, 90)
  })
  default = {}
}

variable "smtp" {
  description = "Outgoing mail for alarm notifications (an SMTP profile and an email notification profile); null for none"
  type = object({
    name     = optional(string, "demo")
    hostname = optional(string, "localhost")
    port     = optional(number, 25)
  })
  default = {}
}
