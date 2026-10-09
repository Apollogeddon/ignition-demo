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

# The same configuration the 8.1 seed (gateway/seed/seed.json) creates, where
# the provider has a resource for it. Not covered here: security levels, the
# user source's roles and users, and the gateway's audit profile setting.

resource "ignition_user_source" "demo" {
  count       = var.user_source == null ? 0 : 1
  name        = var.user_source.name
  type        = "INTERNAL"
  description = var.user_source.description
}

resource "ignition_identity_provider" "demo" {
  count       = var.user_source == null ? 0 : 1
  name        = var.user_source.name
  type        = "internal"
  user_source = ignition_user_source.demo[0].name
}

resource "ignition_audit_profile" "logins" {
  count          = var.audit_profile == null ? 0 : 1
  name           = var.audit_profile.name
  type           = "database"
  database       = ignition_database_connection.demo.name
  table_name     = var.audit_profile.table
  retention_days = var.audit_profile.retention_days
  auto_create    = true
  prune_enabled  = true
}

resource "ignition_smtp_profile" "demo" {
  count    = var.smtp == null ? 0 : 1
  name     = var.smtp.name
  hostname = var.smtp.hostname
  port     = var.smtp.port
}

resource "ignition_alarm_notification_profile" "email" {
  count = var.smtp == null ? 0 : 1
  name  = "email"
  type  = "EmailNotificationProfileType"
  email_config {
    use_smtp_profile = true
    email_profile    = ignition_smtp_profile.demo[0].name
    # 8.3 requires a host and port even when the SMTP profile is used
    hostname = var.smtp.hostname
    port     = var.smtp.port
  }
}
