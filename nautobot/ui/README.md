# Nautobot v2 UI Prototype

## Running it

Install and compile dependencies (note that you'll only use `--npm-install` on initial setup):

```no-highlight
nautobot-server build_ui --npm-install
```

Start Nautobot on port `8080/tcp`:

```no-highlight
nautobot-server runserver 0.0.0.0:8080 --insecure
```

## Running test

To run all UI test suites, run:

```no-highlight
invoke unittest-ui
```

## Debugging Startup/Build Failures

Nautobot will attempt to build the UI on startup when running `post_upgrade` but during development the React project may fail to build, never allowing the Node.JS container from starting. In that situation, skip running the `post_upgrade` until the React app can start. In container workflows that will mean setting the `NAUTOBOT_DOCKER_SKIP_INIT` environment variable to `True`.
