# Health Check Monitor

## Overview

The `HealthCheckMonitor` model defines the mechanism used to verify the availability and responsiveness of pool members or pools. These monitors determine whether traffic should be sent to a given backend based on the result of periodic checks.
The HealthCheckMonitor model provides the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the health check monitor. |
| `interval` | integer | No | Time in seconds between each check. |
| `retry` | integer | No | Number of failures before considering the target down. |
| `timeout` | integer | No | Time in seconds to wait for a response before marking as failed. |
| `port` | integer | No | Port to check against. Optional depending on health check type. |
| `health_check_type` | choice | No | Type of check. Possible values are "Ping", "TCP", "DNS", "HTTP", "HTTPS", "Custom". |
| `tenant` | ForeignKey to Tenant | No | Optional tenant assignment. |

## Details

Health checks can be applied at the Pool or Pool Member level. If a Pool Member has its own monitor, it takes precedence over the monitor defined on the Pool.

- Health check monitors must be created before they can be assigned.
- Different check types (e.g., Ping, TCP, HTTP) may require different port configurations.
- If `port` is not defined, some vendors may fall back to the service port defined on the pool member or use a protocol-specific default.
