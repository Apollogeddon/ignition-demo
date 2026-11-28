output "database_connection" {
  description = "Name of the gateway's database connection"
  value       = ignition_database_connection.demo.name
}

output "historian" {
  description = "Name of the gateway's tag historian, or null when it has none"
  value       = try(ignition_historian_provider.demo[0].name, null)
}
