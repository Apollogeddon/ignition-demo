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
