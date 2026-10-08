# Configure the develop gateway (Ignition 8.3) with the same module the cluster
# uses, so a connection or journal is defined once for every environment.

module "gateway_config" {
  source = "../../cluster/modules/gateway-config"

  database = {
    # the gateway reaches the database by its Compose service name
    host     = "database"
    name     = "demo"
    user     = "demo"
    password = var.db_password
  }
}
