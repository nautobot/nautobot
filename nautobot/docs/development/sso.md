# SSO Development Environment With Keycloak

SSO in local development environments can be less than clear to setup at times. By simply defining `invoke.yml` and running `invoke provision-sso` Nautobot now provides a development environment with SSO fully configured and working.

## Keycloak Containers

Keycloak is run in the same docker-compose project as Nautobot and has it own set of environment variables & docker-compose file. This is done to ensure you are able to have two separate instances of Postgres, one for Nautobot and one for Keycloak. This is solely meant for local development and testing, this is not a production ready reference for deploying Keycloak for SSO.

### Update invoke.yml

The `invoke.yml` file must be updated to add `development/docker-compose.keycloak.yml` to the docker-compose project and to enable OIDC. These setting are solely for local development inside the Nautobot repository and is not applicable to any other deployment.

* enable_oidc - Stringified boolean value that must be set to `"True"` for the `nautobot_config.py` load the SSO configuration.
* sso_host - This is the base url for Keycloak that is accessible for the user, default value is for running the development environment on `localhost` only overload if performing remote development.
* nautobot_host - This is the base url for Nautobot that is accessible for the user, default value is for running the development environment on `localhost` only overload if performing remote development.
* compose_files - List of docker-compose files needed for nautobot deployment.

#### Example invoke.yml

Example running development environment on localhost.

```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.postgres.yml"
    - "docker-compose.dev.yml"
    - "docker-compose.keycloak.yml"
  enable_oidc: "True"
```

Example running development environment on remote host.

```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.postgres.yml"
    - "docker-compose.dev.yml"
    - "docker-compose.keycloak.yml"
  enable_oidc: "True"
  sso_host: "http://192.168.0.2:8087"
  nautobot_host: "http://192.168.0.2:8080"
```

### Provisioning Keycloak

Initial configuration of Keycloak is done via a templated JSON file that is generated via `invoke provision-sso`. This must be done before starting Keycloak and Nautobot, it is recommended to start with all services down to ensure services are provisioned correctly. Defining `invoke.yml` is required before attempting to provision the local SSO environment.

```bash
➜ invoke stop           # ensure all services are stopped
➜ invoke provision-sso  # generate Keycloak configuration
➜ invoke start          # start services
```

## Validating Setup

Once all steps are completed Nautobot should now have the `Continue to SSO` button on the login screen and should immediately redirect the user to sign in with Keycloak.

### Keycloak Login Credentials

Keycloak admin console is reachable via `http://localhost:8087/` with user `admin` and password `admin`. The below users are pre-configured within Keycloak, at this time their permissions are not directly mapped to any permissions provided by default by Nautobot. This will be a later enhancement to the local development environment.

| Username         | Password  |
+------------------+-----------+
| nautobot_unpriv  | unpriv123 |
| nautonot_admin   | admin123  |
| nautobot_auditor | audit123  |
