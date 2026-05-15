# SLAs and SLOs

Threshold-based alerts page when a single observation crosses a line. SLO-based alerts page when the rate of failure consumes an error budget faster than expected — a fundamentally different framing that correlates better with user-perceived service quality. This page covers when to reach for that framing in a Nautobot deployment, which signals make good Service Level Indicators, how to set starting values, and how to write burn-rate alerts against Nautobot's exposed metrics.

!!! note "Living section"
    The starting SLO values, candidate SLIs, and burn-rate recipes here are recommendations based on production deployments we have seen — refine them against your own baseline and operational tolerances. Contributions from your environment are welcome.

## SLA vs SLO vs SLI

The three terms are often used interchangeably but mean different things:

- **SLI (Service Level Indicator)** — the *measurement*. A concrete number describing how the service performed: "% of Job runs that succeeded over the last 30 days," or "p99 latency of API `GET` requests over 5 minutes."
- **SLO (Service Level Objective)** — the *target* you operate against internally: "99% of Job runs in any 30-day window succeed." Drives engineering and operational decisions; not customer-facing.
- **SLA (Service Level Agreement)** — the *contractual commitment* to a customer or downstream consumer, typically with financial consequences for misses. Almost always weaker (more permissive) than the corresponding internal SLO, so a small SLO miss does not immediately become a contract breach.

A typical maturity progression is SLI → SLO → SLA. Most Nautobot operators will not write an SLA; they will define SLIs and operate against SLOs internally to make capacity, reliability, and feature-velocity tradeoffs explicit.

## Candidate SLIs for Nautobot

Pick two or three of these to start — not all are worth tracking for every deployment. The metric column references series exposed by Nautobot's `/metrics` endpoint or the backing-store exporters covered in [Prometheus Metrics](./prometheus-metrics.md) and [Backing Stores](./backing-stores.md).

| SLI | Question it answers | Underlying metric |
|---|---|---|
| Job success rate | "Did automation actually work?" | `nautobot_worker_finished_jobs{status="SUCCESS"} / nautobot_worker_finished_jobs` |
| Web availability | "Could users and integrations reach Nautobot?" | `django_http_responses_total_by_status_total{status!~"5.."} / django_http_responses_total_by_status_total` |
| Web latency | "Was the UI or API fast enough to use?" | `django_http_requests_latency_seconds_by_view_method` histograms, p99 quantile |
| Beat schedule freshness | "Did scheduled automation fire on time?" | derived from `extras_scheduledjob.next_run_at` slippage (see [Celery and Jobs — Beat Schedule Drift](./celery-jobs.md#beat-schedule-drift)) |
| Backing-store availability | "Was the dependency stack healthy?" | `health_check_database_info` and `health_check_redis_backend_info` |

The two with the highest practical value for most deployments are **Job success rate** and **Web availability** — they map directly to user-perceived outcomes (the automation worked, or it didn't; the page loaded, or it didn't).

## Setting Initial SLOs

A workable starting SLO is one that is:

- **Achievable in steady state today.** Set it against your current p95 baseline plus a small headroom margin. An SLO you are already missing is demoralizing and uninformative.
- **Just tight enough to be uncomfortable when broken.** Setting it at the level you always hit does not drive action when you miss; setting it where you usually hit but sometimes miss drives investigation.
- **Aligned to a window that matches business context.** 30-day rolling windows are the standard default. Shorter windows (7 days) react faster but punish single bad days; longer windows (90 days) smooth out incidents but obscure recent regressions.

Starting values that have worked well for typical mid-size Nautobot deployments:

| SLI | Starting SLO |
|---|---|
| Job success rate | 99.0% over rolling 30 days |
| Web availability | 99.5% over rolling 30 days |
| Web latency (p99 `GET`) | < 2 seconds over rolling 30 days |
| Beat schedule freshness | 99% of scheduled fires within 5 minutes of `next_run_at` |

Calibrate against your own baseline before committing — see [Alerting — Calibrating Thresholds](./alerting.md#calibrating-thresholds) for the 7-day baseline recipe. The same procedure applies here, but you take the 5th percentile of your SLI (the floor of healthy operation), not the 95th percentile of a noise signal.

## Error Budget Alerting

An SLO defines an error budget — the amount of failure you are allowed in the window. For a 99% Job success SLO with 100,000 runs per month, the budget is 1,000 failed runs. The point is not to never use the budget; it is to spend it gradually and to notice when you are burning it abnormally fast.

The canonical pattern is the [multi-window, multi-burn-rate alert](https://sre.google/workbook/alerting-on-slos/) — fire when the failure rate over a short window and a long window simultaneously projects to consume the budget faster than allowed.

In PromQL, for the Job-success SLO with a 30-day window:

```promql
# Fast burn: alert if the last 1h would consume 100% of the
# 30-day budget in under 6h (14.4x burn rate).
(
  sum(rate(nautobot_worker_finished_jobs{status="FAILURE"}[1h]))
    / sum(rate(nautobot_worker_finished_jobs[1h]))
) > (14.4 * 0.01)
and
(
  sum(rate(nautobot_worker_finished_jobs{status="FAILURE"}[5m]))
    / sum(rate(nautobot_worker_finished_jobs[5m]))
) > (14.4 * 0.01)
```

Replace `0.01` with `1 - SLO` for any other SLO target. The `14.4x` constant — and the slower `1x` / `0.5x` companion alerts that warn before the budget is fully consumed — are documented in the [Prometheus SRE workbook](https://sre.google/workbook/alerting-on-slos/).

For Nautobot specifically, the most commonly useful burn-rate alerts are:

- **Job success rate burn** — built on `nautobot_worker_finished_jobs` as above.
- **Web availability burn** — substituting `django_http_responses_total_by_status_total{status=~"5.."}` for the failure counter and the corresponding total counter for the denominator.

## SLOs and Alerting Tiers

SLO-based alerts and threshold-based alerts (described in [Alerting](./alerting.md)) coexist. They answer different questions:

- **Threshold alerts** answer "is something broken right now?" — useful for total outages, infrastructure failures, and any condition where the response is "stop everything and investigate."
- **Burn-rate alerts** answer "are we degrading toward an SLO miss?" — useful for partial degradation, gradual reliability erosion, and capacity-driven failures.

The recommended pattern is:

- Keep Tier 1 / Tier 2 threshold alerts for outages and infrastructure conditions (database down, all workers stale, web 5xx flood). These never go away.
- Add burn-rate alerts for any SLO you commit to. They typically route to ticket or dashboard rather than pager — the response is "investigate during business hours and decide whether to slow feature work" — but a fast burn (14.4× and worse) is page-worthy because at that rate you will exhaust the budget within hours.

## Reporting and Iteration

The discipline behind SLOs is not only the alerts. It is the recurring review of:

- **What was the SLI value over the last window?** Did we hit the SLO?
- **How much of the error budget did we consume?** What incidents drove the consumption?
- **Is the SLO still right?** If you have never broken it, it might be too loose. If you break it every month, it might be too tight — or you might have a real reliability problem to invest in.

A monthly SLO review with the team, alongside the Tier 1 / Tier 2 incident retrospectives, closes the loop. A dedicated Grafana panel showing the current SLI value over the rolling window, the error-budget consumption percentage, and the burn rate over the last 1h and 6h makes the review concrete — see [Visualization — SLO Performance](./visualization.md#5-slo-performance) for the panel structure.

When an SLO is consistently missed, the response is rarely "make the SLO looser." More often it is one of:

- **Invest in reliability** — slow feature work until the budget recovers.
- **Improve the SLI** — the measurement may be too coarse (e.g., counting all Job classes together when one Job is dominating failures).
- **Decompose** — split into per-Job-class or per-tenant SLOs that route differently.
