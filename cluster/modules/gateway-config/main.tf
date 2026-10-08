# The gateway's own configuration, applied through its REST API: everything a
# project needs from the gateway that the image and the chart do not own.
#
# Not here on purpose: projects (the image owns them), redundancy and the
# Gateway Network (the chart owns them).

resource "ignition_database_connection" "demo" {
  name        = var.connection_name
  description = "Demo application database (managed by OpenTofu)"
  type        = "PostgreSQL"
  translator  = "POSTGRES"
  connect_url = "jdbc:postgresql://${var.database.host}:${var.database.port}/${var.database.name}"
  username    = var.database.user
  password    = var.database.password
}

resource "ignition_alarm_journal" "demo" {
  count        = var.alarm_journal == null ? 0 : 1
  name         = var.alarm_journal.name
  type         = "DATASOURCE"
  datasource   = ignition_database_connection.demo.name
  table_name   = var.alarm_journal.table
  min_priority = var.alarm_journal.min_priority
}
