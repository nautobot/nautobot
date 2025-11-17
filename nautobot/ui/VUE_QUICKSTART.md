# Vue 3 Frontend - Quick Start Guide

## Viewing the Vue Interface

After building the Vue app, you can access it at:

**URL:** `http://your-nautobot-url/vue/`

For example:
- Local development: `http://localhost:8000/vue/`
- Production: `https://your-domain.com/vue/`

## Prerequisites

1. **Build the Vue app:**
   ```bash
   cd nautobot/ui
   npm install
   npm run build
   ```

2. **Ensure Django can serve static files:**
   The Vue app files will be in `nautobot/project-static/dist/` after building.

3. **Run Nautobot:**
   ```bash
   nautobot-server runserver
   ```

## What You'll See

The Vue interface includes:

- **Home Page** (`/vue/`) - Landing page with navigation cards
- **Devices** (`/vue/devices`) - List and detail views for devices
- **Locations** (`/vue/locations`) - List and detail views for locations  
- **Prefixes** (`/vue/prefixes`) - List and detail views for IP prefixes

## Features

- ✅ Full Single Page Application (SPA) with Vue Router
- ✅ REST API integration with Django REST Framework
- ✅ CSRF token handling
- ✅ Bootstrap 5 styling (consistent with Nautobot)
- ✅ Responsive design
- ✅ Loading states and error handling

## Troubleshooting

### Vue app not loading

1. **Check that files were built:**
   ```bash
   ls -la nautobot/project-static/dist/js/nautobot-vue.js
   ls -la nautobot/project-static/dist/js/vue-libraries.js
   ```

2. **Check browser console** for JavaScript errors

3. **Verify API path** - The Vue app needs access to `/api/` endpoint

4. **Check CSRF token** - Ensure you're logged into Nautobot

### API errors

- Ensure you're authenticated (logged in)
- Check that Django REST Framework is enabled
- Verify API endpoints are accessible at `/api/`

### Build errors

- Ensure Node.js version >= 22
- Run `npm install` to install dependencies
- Check `npm run build` output for errors

## Next Steps

- Customize components in `nautobot/ui/src/js/vue/components/`
- Add new routes in `nautobot/ui/src/js/vue/routes.js`
- Create new views in `nautobot/ui/src/js/vue/views/`
- Extend API client in `nautobot/ui/src/js/vue/services/api.js`

For more details, see `VUE_SETUP.md`.

