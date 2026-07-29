#!/usr/bin/env bash
# Reproduce / verify the OTLP-gRPC + uWSGI-prefork + django-silk-profiling worker SEGFAULT.
#
# See development/OTEL_SEGFAULT_REPRO.md for the full setup (compose override, nautobot_config.py
# profiling toggles, observability stack). This script only drives traffic and inspects the uWSGI
# `nautobot` container logs for worker segfaults (signal 11), printing a pass/fail summary.
#
# Usage:
#   development/otel_segfault_repro.sh [-n REQUESTS] [-u URL]
#
# Environment toggles (answer the two open questions):
#   --no-collector   documented reminder to stop the `otel` service first (see below); the channel is
#                    still constructed, so the unpatched build is expected to crash even with nothing
#                    listening on 4317.
#   --lazy-apps      reminder to start the stack with REPRO_LAZY_APPS=true so uWSGI loads the app per
#                    worker after fork.
#
# Exit status: 0 if no worker segfault was observed during the run (PASS), 1 if one or more workers
# segfaulted (FAIL / reproduced).
set -euo pipefail

REQUESTS=24
# Any non-/health/ endpoint that django-silk will profile. /login/ is unauthenticated and returns 200.
URL="http://localhost:8080/login/"
CONTAINER_GREP="nautobot"  # matches the uWSGI web container name (e.g. nautobot-3-3-nautobot-1)

while [ $# -gt 0 ]; do
  case "$1" in
    -n) REQUESTS="$2"; shift 2 ;;
    -u) URL="$2"; shift 2 ;;
    --no-collector) echo "NOTE: stop the collector first: docker compose stop otel"; shift ;;
    --lazy-apps) echo "NOTE: (re)start the stack with REPRO_LAZY_APPS=true to enable uWSGI --lazy-apps"; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Match the uWSGI web container across compose project-name variants, e.g. nautobot-3-2-nautobot-1
# (the web service is named "nautobot"; exclude celery_worker/celery_beat/ui_build/db/redis/etc.).
container="$(docker ps --format '{{.Names}}' | grep -E "${CONTAINER_GREP}.*-nautobot-[0-9]+$" | head -1 || true)"
if [ -z "${container}" ]; then
  echo "ERROR: could not find the running uWSGI 'nautobot' container. Is the stack up with the" >&2
  echo "       docker-compose.otel-segfault-repro.yml override added to invoke.yml compose_files?" >&2
  exit 2
fi
echo "Driving ${REQUESTS} requests at ${URL} (container: ${container}) ..."

# Baseline: count segfault lines already in the log so we only measure this run.
segfault_re='signal 11|SIGSEGV|Segmentation fault|segfault'
before="$(docker logs "${container}" 2>&1 | grep -Ec "${segfault_re}" || true)"

ok=0
for i in $(seq 1 "${REQUESTS}"); do
  code="$(curl -s -o /dev/null -w '%{http_code}' "${URL}" || echo "000")"
  if [ "${code}" = "200" ]; then ok=$((ok + 1)); fi
  printf 'request %2d/%d -> HTTP %s\n' "${i}" "${REQUESTS}" "${code}"
done

# Give uWSGI a moment to log the worker crash/respawn.
sleep 2
after="$(docker logs "${container}" 2>&1 | grep -Ec "${segfault_re}" || true)"
segfaults=$((after - before))

echo "----------------------------------------"
echo "HTTP 200 responses: ${ok}/${REQUESTS}"
echo "Worker segfaults observed this run: ${segfaults}"
if [ "${segfaults}" -gt 0 ]; then
  echo "RESULT: FAIL - reproduced the segfault (worker signal 11). Recent crash lines:"
  docker logs "${container}" 2>&1 | grep -E "${segfault_re}" | tail -5
  exit 1
fi
echo "RESULT: PASS - no worker segfault observed (fix working, or conditions not all met)."
exit 0
