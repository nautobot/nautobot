# Developing the Bootstrap 3 UI

## Introduction

Nautobot's current primary UI is based on [Bootstrap 3](https://getbootstrap.com/docs/3.4/). Since Nautobot 2.1.0, this UI has used a Nautobot-specific custom Bootstrap theme built in the [`nautobot-bootstrap`](https://github.com/nautobot/nautobot-bootstrap/) GitHub repository and then customized further in the main [`nautobot`](https://github.com/nautobot/nautobot/) GitHub repository.

## Theme Files

- `nautobot/project-static/bootstrap-3.4.1-dist/css/` - the base Nautobot-themed Bootstrap CSS definitions, directly as compiled from `nautobot-bootstrap`. _These should never be edited manually, only recompiled from `nautobot-bootstrap` and copied as-is into `nautobot`._
- `nautobot/project-static/css/base.css` - Overrides and extensions of the base CSS theme for Nautobot. Can be edited as needed.
- `nautobot/project-static/css/dark.css` - Additional overrides and extensions specifically for the "dark mode" theme. Can be edited as needed.

## Previewing the theme

When `settings.DEBUG` is set to `True`, an authenticated Nautobot user can access the URL `/theme-preview/` to retrieve a templated view that showcases many of the different Nautobot UI elements. While not necessarily comprehensive, this view is designed to provide an overview of the current theme more conveniently than clicking around to various specific pages in the UI. Feel free to add more example content into this view as needed.
