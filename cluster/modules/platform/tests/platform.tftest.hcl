# The platform module's validations, names and database backup, against mock
# providers: tofu -chdir=cluster/modules/platform test

mock_provider "kubernetes" {}
mock_provider "random" {}

variables {
  namespace   = "ignition"
  db_init_dir = "../../../database/init"
}

run "unprefixed_names_by_default" {
  command = plan
  assert {
    condition     = kubernetes_stateful_set_v1.db.metadata[0].name == "database" && output.db_host == "database.ignition.svc"
    error_message = "Without name, the database keeps its unprefixed name."
  }
  assert {
    condition     = kubernetes_stateful_set_v1.db.spec[0].template[0].spec[0].container[0].image == "docker.io/library/postgres:17.12"
    error_message = "The database image is not pinned to a minor release."
  }
}

run "prefixes_names" {
  command = plan
  variables {
    name     = "site-a"
    registry = { server = "ghcr.io", username = "u", password = "p" }
  }
  assert {
    condition = alltrue([
      kubernetes_stateful_set_v1.db.metadata[0].name == "site-a-database",
      kubernetes_secret_v1.db.metadata[0].name == "site-a-database",
      kubernetes_config_map_v1.db_init.metadata[0].name == "site-a-database-init",
      kubernetes_secret_v1.registry[0].metadata[0].name == "site-a-registry",
      kubernetes_cron_job_v1.db_backup[0].metadata[0].name == "site-a-database-backup",
      output.db_host == "site-a-database.ignition.svc",
    ])
    error_message = "name does not prefix every resource."
  }
  assert {
    condition     = kubernetes_stateful_set_v1.db.spec[0].selector[0].match_labels["app.kubernetes.io/name"] == "site-a-database"
    error_message = "Two deployments' databases would select each other's pods."
  }
}

run "name_must_be_a_dns_label" {
  command = plan
  variables {
    name = "Site A"
  }
  expect_failures = [var.name]
}

run "backs_up_the_database" {
  command = plan
  variables {
    storage_class = "local-path"
    db_backup     = { retention_days = 3 }
  }
  assert {
    condition     = strcontains(kubernetes_cron_job_v1.db_backup[0].spec[0].job_template[0].spec[0].template[0].spec[0].container[0].command[2], "-mmin +4320")
    error_message = "The backup job does not keep retention_days of dumps."
  }
  assert {
    condition     = strcontains(kubernetes_cron_job_v1.db_backup[0].spec[0].job_template[0].spec[0].template[0].spec[0].container[0].command[2], "until pg_isready")
    error_message = "The backup job must wait for the database, as a network policy can refuse a new pod for a few seconds."
  }
  assert {
    condition     = kubernetes_cron_job_v1.db_backup[0].spec[0].job_template[0].spec[0].template[0].spec[0].container[0].image == "docker.io/library/postgres:17.12"
    error_message = "The backup job's pg_dump must match the server's image."
  }
  assert {
    condition     = kubernetes_persistent_volume_claim_v1.db_backup[0].spec[0].storage_class_name == "local-path"
    error_message = "The backup volume does not fall back to storage_class."
  }
  assert {
    condition     = length(kubernetes_network_policy_v1.db.spec[0].ingress[0].from) == 2
    error_message = "The database's NetworkPolicy does not let the backup job in."
  }
}

run "no_backup_when_null" {
  command = plan
  variables {
    db_backup = null
  }
  assert {
    condition     = length(kubernetes_cron_job_v1.db_backup) == 0 && length(kubernetes_network_policy_v1.db.spec[0].ingress[0].from) == 1
    error_message = "db_backup = null still creates the backup job or lets it in."
  }
}

run "retention_of_at_least_a_day" {
  command = plan
  variables {
    db_backup = { retention_days = 0 }
  }
  expect_failures = [var.db_backup]
}
