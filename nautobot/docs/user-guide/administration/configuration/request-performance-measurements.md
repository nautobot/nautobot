# Request Performance Measurements

+++ 3.3.0

Nautobot can measure the performance of a request.

This is useful for benchmarking, and for determining potential areas of optimization for requests.

Performance measurements are disabled by default.

## Settings

To enable a performance measurement, change any of these settings to `True`

| Setting                                      | Environment Variable                              | Measures                                    |
|----------------------------------------------|---------------------------------------------------|----------------------------------------------|
| [`REQUEST_TOTAL_DURATION_HEADER_ENABLED`](settings.md#request_total_duration_header_enabled) | `NAUTOBOT_REQUEST_TOTAL_DURATION_HEADER_ENABLED` | Total wall clock time spent processing the request. |
| [`REQUEST_DB_DURATION_HEADER_ENABLED`](settings.md#request_db_duration_header_enabled)       | `NAUTOBOT_REQUEST_DB_DURATION_HEADER_ENABLED`    | Time spent executing SQL during the request, and the number of queries. |

## Response Headers

When a performance measurement is enabled, Nautobot will add a `Server-Timing` field to the response header. This follows the [W3C Server Timing specification](https://www.w3.org/TR/server-timing/).

The `Server-Timing` header value is a comma-delimited (`,`) list of performance measurements. Each performance measurement is a semicolon-delimited (`;`) set of attributes:

```no-highlight
name;dur=DURATION;desc="DESCRIPTION"
```

| Name   | Description                                                         |
|--------|---------------------------------------------------------------------|
| `name` | Measurement name                                                    |
| `dur`  | Measurement duration in milliseconds, rounded to two decimal places |
| `desc` | Measurement description.                                            |

!!! note
    Django Debug Toolbar also reports its timings in the `Server-Timing` header. If request measurements and Django Debug Toolbar are both enabled, both write to the same header. They do not overwrite each other, but you may see duplicated measurement names.

### Measurement Examples

| Name    | Description                                                             |
|---------|-------------------------------------------------------------------------|
| `total` | Total request duration.                                                 |
| `db`    | Database query duration. The description reports the number of queries. |

Example header with both measurements enabled:

```no-highlight
Server-Timing: total;dur=33.76;desc="Total request duration", db;dur=4.55;desc="11 database queries"
```

The header is added to every response, not just API responses. Browsers show it in the network tab of their developer tools.

## Curl Example

```no-highlight
curl --verbose \
     --output /dev/null \
     --header 'Accept: application/json' \
     --header 'Authorization: Token 0123456789abcdef0123456789abcdef01234567' \
     'http://localhost:8080/api/extras/statuses/?limit=1'
```

```no-highlight
< HTTP/1.1 200 OK
< Content-Type: application/json
< API-Version: 3.3
< Content-Length: 1085
< Server-Timing: total;dur=33.76;desc="Total request duration", db;dur=4.55;desc="11 database queries"
```

## Monitoring

When a measurement is enabled, its measurements are also exported to Prometheus.

Metrics generated using these measurements are labeled with the requesting user's hashed token. See [Prometheus Metrics](../guides/prometheus-metrics.md).
