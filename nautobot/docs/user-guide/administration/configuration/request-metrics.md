# Request Metrics

+++ 3.3.0

Nautobot can measure how long each request takes and report the timings back in the response. This is useful for benchmarking a request, or for finding out whether a slow request is spending its time in the database.

Request metrics are off by default. Each metric is enabled on its own.

## Settings

| Setting                                      | Environment Variable                              | Measures                                    |
|----------------------------------------------|---------------------------------------------------|----------------------------------------------|
| [`REQUEST_TOTAL_DURATION_HEADER_ENABLED`](settings.md#request_total_duration_header_enabled) | `NAUTOBOT_REQUEST_TOTAL_DURATION_HEADER_ENABLED` | Total wall clock time spent processing the request. |
| [`REQUEST_DB_DURATION_HEADER_ENABLED`](settings.md#request_db_duration_header_enabled)       | `NAUTOBOT_REQUEST_DB_DURATION_HEADER_ENABLED`    | Time spent executing SQL during the request, and the number of queries. |

Set either to `True` to enable it.

## The `Server-Timing` Header

When a metric is enabled, Nautobot adds it to the `Server-Timing` response header. This follows the [W3C Server Timing specification](https://www.w3.org/TR/server-timing/).

The header value is a comma-delimited (`,`) list of metrics. Each metric is a semicolon-delimited (`;`) set of attributes:

```no-highlight
name;dur=DURATION;desc="DESCRIPTION"
```

`dur` is the duration in milliseconds, rounded to two decimal places.

| Name    | Description                              |
|---------|-------------------------------------------|
| `total` | Total request duration.                   |
| `db`    | Database query duration. The description reports the number of queries. |

Example header with both metrics enabled:

```no-highlight
Server-Timing: total;dur=33.76;desc="Total request duration", db;dur=4.55;desc="11 database queries"
```

The header is added to every response, not just API responses. Browsers show it in the network tab of their developer tools.

## Example

```no-highlight
curl --verbose --output /dev/null \
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

!!! note
    Django Debug Toolbar also reports its timings in the `Server-Timing` header. If request metrics and Django Debug Toolbar are both enabled, both write to the header. They do not overwrite each other, but you may see duplicated metric names.

## Monitoring

When a metric is enabled, its durations are also exported as Prometheus histograms, labeled by a hash of the requesting token. See [Prometheus Metrics](../guides/prometheus-metrics.md).

To limit how much work a client can ask Nautobot to do, see [Rate Limiting](rate-limiting.md).
