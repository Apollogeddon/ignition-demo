output "namespace" {
  description = "Namespace holding the gateway and database"
  value       = local.namespace
}

output "db_host" {
  description = "Database host, as the gateways reach it"
  value       = "${kubernetes_service_v1.db.metadata[0].name}.${local.namespace}.svc"
}

output "db_port" {
  description = "Database port"
  value       = 5432
}

output "db_name" {
  description = "Database name"
  value       = var.db_name
}

output "db_user" {
  description = "Database user"
  value       = var.db_user
}

output "db_password" {
  description = "Database password"
  value       = kubernetes_secret_v1.db.data["POSTGRES_PASSWORD"]
  sensitive   = true
}

output "image_pull_secrets" {
  description = "Pull secret names for the gateway (empty for public images)"
  value       = [for s in kubernetes_secret_v1.registry : s.metadata[0].name]
}

output "db_backup_claim" {
  description = "PersistentVolumeClaim holding the database dumps; null without db_backup"
  value       = try(kubernetes_persistent_volume_claim_v1.db_backup[0].metadata[0].name, null)
}
