variable "namespace" {
  description = "Namespace for the gateway and its database"
  type        = string
}

variable "create_namespace" {
  description = "Create the namespace (with restricted Pod Security enforced); false to use an existing one"
  type        = bool
  default     = true
}

variable "db_init_dir" {
  description = "Folder of *.sql files run, in name order, when the database is first created"
  type        = string
}

variable "db_image" {
  description = "PostgreSQL image, pinned to a minor release; the backup CronJob runs it too, so its pg_dump matches the server"
  type        = string
  default     = "docker.io/library/postgres:17.12"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "demo"
}

variable "db_user" {
  description = "Database user"
  type        = string
  default     = "demo"
}

variable "db_password" {
  description = "Database password; generated when null"
  type        = string
  default     = null
  sensitive   = true
}

variable "db_storage" {
  description = "Database volume size"
  type        = string
  default     = "2Gi"
}

variable "storage_class" {
  description = "StorageClass for the database volume (and its backups, unless db_backup sets one); null uses the cluster default"
  type        = string
  default     = null
}

variable "db_client_labels" {
  description = "Pod labels allowed to connect to the database (the gateway pods)"
  type        = map(string)
  default     = { "app.kubernetes.io/name" = "ignition" }
}

variable "registry" {
  description = "Credentials for a private image registry, stored as a pull secret (e.g. GHCR with a read:packages token); null for public images"
  type = object({
    server   = string
    username = string
    password = string
  })
  default   = null
  sensitive = true
}

variable "db_backup" {
  description = "A CronJob that pg_dumps the database into a volume of its own, keeping retention_days of dumps; null for none"
  type = object({
    schedule       = optional(string, "23 2 * * *")
    retention_days = optional(number, 7)
    storage        = optional(string, "5Gi")
    storage_class  = optional(string)
  })
  default = {}

  validation {
    condition     = var.db_backup == null || try(var.db_backup.retention_days >= 1, false)
    error_message = "db_backup.retention_days must be at least 1."
  }
}
