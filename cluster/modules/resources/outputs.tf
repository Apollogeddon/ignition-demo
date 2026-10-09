output "database_connection" {
  description = "Name of the gateway's database connection"
  value       = ignition_database_connection.demo.name
}
