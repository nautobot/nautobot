/**
 * Nautobot Vue 3 Application Entry Point
 *
 * This is the main entry point for the Vue 3 frontend application.
 * It can be used as a standalone SPA or integrated into existing Django templates.
 */

import { createApp } from 'vue';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';
import routes from './routes.js';
import { apiClient } from './services/api.js';

// Import Bootstrap CSS (already available globally, but ensure it's loaded)
import 'bootstrap/dist/css/bootstrap.min.css';

// Create Vue Router instance
const router = createRouter({
  history: createWebHistory(window.nautobot?.basePath || '/'),
  routes,
});

// Create Vue app instance
const app = createApp(App);

// Provide API client to all components
app.provide('api', apiClient);

// Provide router
app.use(router);

// Mount the app
// This can mount to a specific element in Django templates or create a full SPA
const mountElement = document.getElementById('nautobot-vue-app');
if (mountElement) {
  app.mount(mountElement);
} else {
  // For development/testing: create a mount point if it doesn't exist
  const div = document.createElement('div');
  div.id = 'nautobot-vue-app';
  document.body.appendChild(div);
  app.mount(div);
}

// Export app instance for potential external use
window.nautobotVue = app;

export default app;
