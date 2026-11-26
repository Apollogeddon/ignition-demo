# The resources module's optional blocks, against a mock ignition provider:
# tofu -chdir=cluster/modules/resources test

mock_provider "ignition" {}

variables {
  database = {
    host     = "database.ignition.svc"
    name     = "demo"
    user     = "demo"
    password = "secret"
  }
}

run "only_the_connection_by_default" {
  command = plan
  assert {
    condition = alltrue([
      length(ignition_alarm_journal.demo) == 0,
      length(ignition_historian_provider.demo) == 0,
      length(ignition_user_source.demo) == 0,
      length(ignition_identity_provider.demo) == 0,
      length(ignition_audit_profile.logins) == 0,
      length(ignition_smtp_profile.demo) == 0,
      length(ignition_alarm_notification_profile.email) == 0,
    ])
    error_message = "A fresh deploy creates optional resources nobody asked for."
  }
  assert {
    condition     = ignition_database_connection.demo.connect_url == "jdbc:postgresql://database.ignition.svc:5432/demo"
    error_message = "The connection URL is wrong."
  }
}

run "every_block_with_its_defaults" {
  command = plan
  variables {
    alarm_journal = {}
    historian     = {}
    user_source   = {}
    audit_profile = {}
    smtp          = {}
  }
  assert {
    condition = alltrue([
      ignition_alarm_journal.demo[0].table_name == "alarm_events",
      ignition_historian_provider.demo[0].name == "demo",
      ignition_historian_provider.demo[0].pruning_age == 12,
      ignition_identity_provider.demo[0].user_source == "demo",
      ignition_audit_profile.logins[0].retention_days == 90,
      ignition_smtp_profile.demo[0].hostname == "localhost",
      ignition_alarm_notification_profile.email[0].email_config.email_profile == "demo",
    ])
    error_message = "{} does not create the block with its defaults."
  }
}

run "historian_pruning_at_least_a_month" {
  command = plan
  variables {
    historian = { pruning_months = 0 }
  }
  expect_failures = [var.historian]
}
