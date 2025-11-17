# Nautobot Vue 3 Frontend

This directory contains the Vue 3 frontend application for Nautobot. The Vue app can be used as a standalone Single Page Application (SPA) or integrated into existing Django templates.

## Structure

```
vue/
├── main.js              # Application entry point
├── App.vue              # Root component
├── routes.js            # Vue Router configuration
├── components/          # Reusable Vue components
│   ├── DataTable.vue
│   ├── Pagination.vue
│   ├── DetailCard.vue
│   └── KeyValueTable.vue
├── views/               # Page components
│   ├── HomeView.vue
│   ├── DeviceListView.vue
│   ├── DeviceDetailView.vue
│   ├── LocationListView.vue
│   ├── LocationDetailView.vue
│   ├── PrefixListView.vue
│   └── PrefixDetailView.vue
└── services/            # API and service layer
    └── api.js           # REST API client
```

## Installation

1. Install dependencies:

```bash
cd nautobot/ui
npm install
```

2. Build the Vue application:

```bash
npm run build
```

## Usage

### As a Standalone SPA

To use Vue as a full SPA, create a Django template that mounts the Vue app:

```html
{% load static %}
<!DOCTYPE html>
<html>
    <head>
        <title>Nautobot Vue</title>
        <link
            rel="stylesheet"
            href="{% static 'dist/css/nautobot-vue.css' %}"
        />
    </head>
    <body>
        <div id="nautobot-vue-app"></div>

        <script>
            window.nautobot = {
                apiPath: '{% url "api-root" %}',
                csrfToken: '{{ csrf_token }}',
                basePath: '/',
            };
        </script>
        <script src="{% static 'dist/js/vue-libraries.js' %}"></script>
        <script src="{% static 'dist/js/nautobot-vue.js' %}"></script>
    </body>
</html>
```

### Integrated into Django Templates

You can also mount Vue components within existing Django templates:

```html
{% load static %}
<div id="device-list-vue-app"></div>

<script>
    window.nautobot = {
        apiPath: '{% url "api-root" %}',
        csrfToken: '{{ csrf_token }}',
    };
</script>
<script src="{% static 'dist/js/vue-libraries.js' %}"></script>
<script src="{% static 'dist/js/nautobot-vue.js' %}"></script>
```

## API Client

The API client (`services/api.js`) provides methods for interacting with the Django REST Framework API:

```javascript
import { apiClient } from './services/api';

// GET request
const devices = await apiClient.get('/dcim/devices/');

// POST request
const newDevice = await apiClient.post('/dcim/devices/', {
    name: 'router1',
    device_type: 1,
    location: 1,
});

// Paginated list
const response = await apiClient.getList('/dcim/devices/', { page: 1 });
```

## Development

### Watch Mode

To rebuild automatically on file changes:

```bash
npm run build:watch
```

### Adding New Routes

Edit `routes.js` to add new routes:

```javascript
{
  path: '/new-route',
  name: 'new-route',
  component: NewView,
}
```

### Creating New Components

Create new Vue components in the `components/` directory:

```vue
<template>
    <div class="my-component">
        <!-- Component template -->
    </div>
</template>

<script>
export default {
    name: 'MyComponent',
    // Component logic
};
</script>

<style scoped>
/* Component styles */
</style>
```

## Integration with Django

The Vue app integrates with Django through:

1. **REST API**: Uses Django REST Framework endpoints
2. **CSRF Protection**: Automatically includes CSRF tokens in requests
3. **Authentication**: Uses Django session authentication (cookies)
4. **Templates**: Can be embedded in Django templates

## Features

- ✅ Vue 3 Composition API support
- ✅ Vue Router for navigation
- ✅ Bootstrap 5 styling
- ✅ REST API integration
- ✅ CSRF token handling
- ✅ Pagination support
- ✅ Loading states
- ✅ Error handling
- ✅ Responsive design

## Future Enhancements

- [ ] Add form components for create/edit
- [ ] Add filtering and search
- [ ] Add bulk actions
- [ ] Add real-time updates via WebSockets
- [ ] Add GraphQL support
- [ ] Add unit tests
- [ ] Add TypeScript support
