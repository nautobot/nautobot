# Vue 3 Frontend Setup Guide

This document provides instructions for setting up and using the Vue 3 frontend in Nautobot.

## Overview

A Vue 3 frontend has been added to Nautobot that can work alongside the existing Django template-based UI. The Vue app provides:

- Modern, reactive UI components
- Single Page Application (SPA) capabilities
- Integration with Django REST Framework API
- Bootstrap 5 styling (consistent with Nautobot)
- Progressive enhancement (can be embedded in Django templates)

## Installation

1. **Install dependencies:**

```bash
cd nautobot/ui
npm install
```

This will install:
- Vue 3.5.13
- Vue Router 4.5.0
- Vue Loader and related build tools
- Babel for JavaScript transpilation

2. **Build the Vue application:**

```bash
npm run build
```

This creates:
- `nautobot/project-static/dist/js/nautobot-vue.js` - Main Vue app bundle
- `nautobot/project-static/dist/js/vue-libraries.js` - Vue and dependencies
- `nautobot/project-static/dist/css/nautobot-vue.css` - Vue component styles

## Project Structure

```
nautobot/ui/src/js/vue/
├── main.js                 # Entry point - initializes Vue app
├── App.vue                 # Root component
├── routes.js               # Vue Router routes
├── components/             # Reusable components
│   ├── DataTable.vue      # Table component for lists
│   ├── Pagination.vue     # Pagination controls
│   ├── DetailCard.vue     # Card wrapper for detail views
│   └── KeyValueTable.vue  # Key-value display table
├── views/                  # Page-level components
│   ├── HomeView.vue
│   ├── DeviceListView.vue
│   ├── DeviceDetailView.vue
│   ├── LocationListView.vue
│   ├── LocationDetailView.vue
│   ├── PrefixListView.vue
│   └── PrefixDetailView.vue
└── services/
    └── api.js              # REST API client
```

## Usage

### Option 1: Standalone SPA

Create a Django view that serves a template with the Vue app:

```python
# views.py
from django.shortcuts import render

def vue_app_view(request):
    return render(request, 'vue_app.html')
```

```html
<!-- templates/vue_app.html -->
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="{% static 'dist/css/nautobot-vue.css' %}">
</head>
<body>
    <div id="nautobot-vue-app"></div>
    
    <script>
        window.nautobot = {
            apiPath: '{% url "api-root" %}',
            csrfToken: '{{ csrf_token }}',
            basePath: '/'
        };
    </script>
    <script src="{% static 'dist/js/vue-libraries.js' %}"></script>
    <script src="{% static 'dist/js/nautobot-vue.js' %}"></script>
</body>
</html>
```

### Option 2: Embedded Components

Mount Vue components within existing Django templates:

```html
{% load static %}
<div class="row">
    <div class="col-md-8">
        <!-- Django template content -->
    </div>
    <div class="col-md-4">
        <div id="device-stats-vue"></div>
    </div>
</div>

<script>
    window.nautobot = {
        apiPath: '{% url "api-root" %}',
        csrfToken: '{{ csrf_token }}'
    };
</script>
<script src="{% static 'dist/js/vue-libraries.js' %}"></script>
<script src="{% static 'dist/js/nautobot-vue.js' %}"></script>
```

## API Integration

The Vue app uses a custom API client (`services/api.js`) that:

- Automatically includes CSRF tokens
- Handles authentication via cookies
- Provides methods: `get()`, `post()`, `put()`, `patch()`, `delete()`, `getList()`

Example usage in a Vue component:

```javascript
import { inject } from 'vue';

export default {
  setup() {
    const api = inject('api');
    
    const loadData = async () => {
      try {
        const devices = await api.getList('/dcim/devices/', { page: 1 });
        // Handle devices
      } catch (error) {
        console.error('Failed to load devices:', error);
      }
    };
    
    return { loadData };
  }
};
```

## Development

### Watch Mode

Rebuild automatically on file changes:

```bash
npm run build:watch
```

### Adding New Routes

Edit `src/js/vue/routes.js`:

```javascript
{
  path: '/new-route',
  name: 'new-route',
  component: NewViewComponent,
}
```

### Creating Components

Create new `.vue` files in `components/` or `views/`:

```vue
<template>
  <div class="my-component">
    <h1>{{ title }}</h1>
  </div>
</template>

<script>
export default {
  name: 'MyComponent',
  props: {
    title: String
  }
};
</script>

<style scoped>
.my-component {
  padding: 1rem;
}
</style>
```

## Current Features

✅ **List Views**: Device, Location, and Prefix list pages with pagination  
✅ **Detail Views**: Individual object detail pages  
✅ **Data Table**: Sortable, clickable table component  
✅ **Pagination**: Page navigation controls  
✅ **API Integration**: REST API client with CSRF support  
✅ **Bootstrap Styling**: Consistent with Nautobot design  
✅ **Error Handling**: Loading states and error messages  
✅ **Router**: Client-side routing with Vue Router  

## Next Steps

To extend the Vue frontend:

1. **Add Forms**: Create form components for create/edit operations
2. **Add Filtering**: Implement search and filter functionality
3. **Add Bulk Actions**: Enable bulk operations on list views
4. **Add More Models**: Extend to other Nautobot models (Circuits, Cables, etc.)
5. **Add Real-time Updates**: WebSocket integration for live updates
6. **Add Tests**: Unit tests for components and services

## Integration with Existing UI

The Vue app is designed to coexist with the existing Django template-based UI:

- Can be used for specific features while keeping Django templates for others
- Shares Bootstrap 5 styling
- Uses the same REST API endpoints
- Respects Django authentication and permissions

## Troubleshooting

### Build Errors

If you encounter build errors:

1. Ensure Node.js version >= 22 (check `package.json` devEngines)
2. Delete `node_modules` and `package-lock.json`, then run `npm install`
3. Check webpack configuration in `webpack.config.js`

### Runtime Errors

- Ensure `window.nautobot` is configured before loading Vue scripts
- Check browser console for API errors
- Verify CSRF token is included in requests
- Ensure API endpoints are accessible

### Vue App Not Mounting

- Verify `#nautobot-vue-app` element exists in DOM
- Check that Vue scripts are loaded after the mount element
- Ensure no JavaScript errors are blocking execution

## Resources

- [Vue 3 Documentation](https://vuejs.org/)
- [Vue Router Documentation](https://router.vuejs.org/)
- [Nautobot REST API Documentation](https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/rest-api/)

