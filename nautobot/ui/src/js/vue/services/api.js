/**
 * API Client for Nautobot REST API
 *
 * Provides a centralized API client for interacting with Django REST Framework endpoints
 */

class ApiClient {
  constructor() {
    // Get API path from global variable set by Django template
    this.baseURL = window.nautobot?.apiPath || '/api';
    this.csrfToken = window.nautobot?.csrfToken || '';
  }

  /**
   * Get CSRF token from cookies or meta tag
   */
  getCsrfToken() {
    if (this.csrfToken) {
      return this.csrfToken;
    }
    const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
    if (cookieMatch) {
      return cookieMatch[1];
    }
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.content : '';
  }

  /**
   * Build full URL
   */
  buildURL(endpoint) {
    if (endpoint.startsWith('http')) {
      return endpoint;
    }
    // Remove leading slash from endpoint to avoid double slashes
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    // Ensure baseURL ends with / and doesn't have double slashes
    const cleanBaseURL = this.baseURL.endsWith('/') ? this.baseURL.slice(0, -1) : this.baseURL;
    return `${cleanBaseURL}/${cleanEndpoint}`;
  }

  /**
   * Make HTTP request
   */
  async request(requestConfig) {
    const { data, endpoint, method, ...requestOptions } = requestConfig;
    const url = this.buildURL(endpoint);
    const headers = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...requestOptions.headers,
    };

    // Add CSRF token for non-GET requests
    if (method !== 'GET' && method !== 'HEAD') {
      headers['X-CSRFToken'] = this.getCsrfToken();
    }

    const config = {
      credentials: 'same-origin', // Include cookies for CSRF
      headers,
      method,
      ...requestOptions,
    };

    if (data && method !== 'GET') {
      config.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        error.response = { data: errorData, status: response.status };
        throw error;
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      return await response.text();
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('API request failed:', error);
      throw error;
    }
  }

  /**
   * GET request
   */
  async get(endpoint, options = {}) {
    return await this.request({ endpoint, method: 'GET', ...options });
  }

  /**
   * POST request
   */
  async post(endpoint, data, options = {}) {
    return await this.request({ data, endpoint, method: 'POST', ...options });
  }

  /**
   * PUT request
   */
  async put(endpoint, data, options = {}) {
    return await this.request({ data, endpoint, method: 'PUT', ...options });
  }

  /**
   * PATCH request
   */
  async patch(endpoint, data, options = {}) {
    return await this.request({ data, endpoint, method: 'PATCH', ...options });
  }

  /**
   * DELETE request
   */
  async delete(endpoint, options = {}) {
    return await this.request({ endpoint, method: 'DELETE', ...options });
  }

  /**
   * Get paginated list
   */
  async getList(endpoint, params = {}) {
    // Build query string from params, handling arrays properly
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        // For arrays, append each value with the same key name
        value.forEach((item) => {
          searchParams.append(key, item);
        });
      } else if (value !== null && value !== undefined) {
        searchParams.append(key, value);
      }
    });
    const queryString = searchParams.toString();
    // Append query string to endpoint if present
    const fullEndpoint = queryString ? `${endpoint}${endpoint.includes('?') ? '&' : '?'}${queryString}` : endpoint;
    return await this.get(fullEndpoint);
  }
}

export const apiClient = new ApiClient();
