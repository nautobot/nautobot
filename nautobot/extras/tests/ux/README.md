# UX tests

This folder holds Playwright tests that test the user interface of a running development instance. The Nautobot test runner (`invoke unittest`) does not run these tests, because this folder has no `__init__.py` file.

The tests read these environment variables:

| Variable | Value |
|---|---|
| `APP_URL` | The URL of the application, for example `http://localhost:8080` |
| `APP_USER`, `APP_PASSWORD` | The credentials of a superuser in the development environment |
| `AXE_SCRIPT` | The path of `axe.min.js`. If it is not set, the tests do not do the accessibility check |
| `ARTIFACTS_DIR` | The folder for the screenshots and the accessibility results. The tests make its subfolders |
| `APP_HOST_RESOLVER_RULES` | Optional. Chromium host resolver rules, for example `MAP localhost host.docker.internal`. Use it when `ALLOWED_HOSTS` accepts only `localhost` |

Run the tests in the official Playwright container:

```bash
docker run --rm --add-host=host.docker.internal:host-gateway \
  -v "$PWD/nautobot/extras/tests/ux:/work/tests" -v "<artifacts-dir>:/work/run" -w /work/tests \
  -e APP_URL="http://localhost:<port>" -e APP_HOST_RESOLVER_RULES="MAP localhost host.docker.internal" \
  -e APP_USER="<user>" -e APP_PASSWORD="<password>" \
  -e AXE_SCRIPT=/work/run/axe.min.js -e ARTIFACTS_DIR=/work/run \
  -e PYTHONDONTWRITEBYTECODE=1 \
  "mcr.microsoft.com/playwright/python:<version>-noble" \
  bash -c "pip install --quiet playwright==<version-without-v> pytest && python -m pytest -q -p no:cacheprovider ."
```
