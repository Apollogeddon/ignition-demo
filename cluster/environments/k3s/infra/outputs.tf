output "gateway_url" {
  description = "Gateway web UI"
  value       = module.gateway.url
}

output "gateway_internal_url" {
  description = "In-cluster URL of the Active gateway"
  value       = module.gateway.internal_url
}

output "gateway_pod_urls" {
  description = "In-cluster URL of each gateway pod"
  value       = module.gateway.pod_urls
}

output "admin_password" {
  description = "Gateway admin password (tofu output -raw admin_password)"
  value       = module.gateway.admin_password
  sensitive   = true
}

output "database" {
  description = "Database connection details, as the gateways reach it"
  value = {
    host     = module.platform.db_host
    port     = module.platform.db_port
    name     = module.platform.db_name
    user     = module.platform.db_user
    password = module.platform.db_password
  }
  sensitive = true
}
