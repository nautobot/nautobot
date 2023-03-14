# SSO Development Environment With Keycloak

SSO in local development environments can be less than clear to setup at times. By simply using the `docker-compose.keycloak.yml` Docker compose file, Nautobot now provides a development environment with SSO fully configured and working.

## Keycloak Containers

Keycloak is run in the same docker-compose project as Nautobot and has its own set of environment variables & docker-compose file. This is done to ensure you are able to have two separate instances of Postgres, one for Nautobot and one for Keycloak. This is solely meant for local development and testing, this is not a production ready reference for deploying Keycloak for SSO.

### Update invoke.yml

The `invoke.yml` file must be updated to add `development/docker-compose.keycloak.yml` to the docker-compose project and to enable OIDC. These setting are solely for local development inside the Nautobot repository and is not applicable to any other deployment.

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
```

## Validating Setup

Once all steps are completed Nautobot should now have the `Continue to SSO` button on the login screen and should immediately redirect the user to sign in with Keycloak.

### Keycloak Login Credentials

Keycloak admin console is reachable via `http://localhost:8087/admin/` with user `admin` and password `admin`. The below users are pre-configured within Keycloak, at this time their permissions are not directly mapped to any permissions provided by default by Nautobot. This will be a later enhancement to the local development environment.

| Username         | Password  |
+------------------+-----------+
| nautobot_unpriv  | unpriv123 |
| nautobot_admin   | admin123  |
| nautobot_auditor | audit123  |
