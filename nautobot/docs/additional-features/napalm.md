# NAPALM

Nautobot supports integration with the [NAPALM automation](https://github.com/napalm-automation/napalm/) library. NAPALM allows Nautobot to serve a proxy for operational data, fetching live data from network devices and returning it to a requester via its REST API. Note that Nautobot does not store any NAPALM data locally.

!!! note
    To enable this integration, the NAPALM library must be installed. See [installation steps](../../installation/nautobot/#napalm) for more information.

Below is an example REST API request and response:

```no-highlight
GET /api/dcim/devices/1/napalm/?method=get_environment

{
    "get_environment": {
        ...
    }
}
```

!!! note
    To make NAPALM requests via the Nautobot REST API, a Nautobot user must have assigned a permission granting the `napalm_read` action for the device object type.

## Authentication

By default, the [`NAPALM_USERNAME`](../../configuration/optional-settings/#napalm_username) and [`NAPALM_PASSWORD`](../../configuration/optional-settings/#napalm_password) configuration parameters are used for NAPALM authentication. They can be overridden for an individual API call by specifying the `X-NAPALM-Username` and `X-NAPALM-Password` headers.

```
$ curl "http://localhost/api/dcim/devices/1/napalm/?method=get_environment" \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; indent=4" \
-H "X-NAPALM-Username: foo" \
-H "X-NAPALM-Password: bar"
```

## Method Support

The list of supported NAPALM methods depends on the [NAPALM driver](https://napalm.readthedocs.io/en/latest/support/index.html#general-support-matrix) configured for the platform of a device. Because there is no granular mechanism in place for limiting potentially disruptive requests, Nautobot supports only read-only [get](https://napalm.readthedocs.io/en/latest/support/index.html#getters-support-matrix) methods.

## Multiple Methods

It is possible to request the output of multiple NAPALM methods in a single API request by passing multiple `method` parameters. For example:

```no-highlight
GET /api/dcim/devices/1/napalm/?method=get_ntp_servers&method=get_ntp_peers

{
    "get_ntp_servers": {
        ...
    },
    "get_ntp_peers": {
        ...
    }
}
```

## Optional Arguments

The behavior of NAPALM drivers can be adjusted according to the [optional arguments](https://napalm.readthedocs.io/en/latest/support/index.html#optional-arguments). Nautobot exposes those arguments using headers prefixed with `X-NAPALM-`. For example, the SSH port is changed to 2222 in this API call:

```
$ curl "http://localhost/api/dcim/devices/1/napalm/?method=get_environment" \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; indent=4" \
-H "X-NAPALM-port: 2222"
```
