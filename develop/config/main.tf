# Configure the develop gateway (Ignition 8.3) with the same module the cluster
# uses, so a connection or journal is defined once for every environment.

module "resources" {
  source = "../../cluster/modules/resources"

  database = {
    # the gateway reaches the database by its Compose service name
    host     = "database"
    name     = "demo"
    user     = "demo"
    password = var.db_password
  }
}

# the module was called gateway_config: move existing state instead of recreating it
moved {
  from = module.gateway_config
  to   = module.resources
}
