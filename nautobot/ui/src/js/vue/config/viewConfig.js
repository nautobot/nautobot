/**
 * View Configuration
 * 
 * Defines configuration for each model type used by generic views.
 * This centralizes all model-specific settings in one place.
 */

// Common formatters
const formatters = {
    contentTypes: (val) => {
        if (val == null) {
            return 'N/A';
        }
        const contentTypes = Array.isArray(val) ? val : [val];
        const filtered = contentTypes.filter((ct) => ct != null);
        if (filtered.length === 0) {
            return 'N/A';
        }
        return filtered
            .map((ct) => {
                if (typeof ct === 'string') {
                    return ct;
                }
                return ct.display ?? ct.model ?? String(ct);
            })
            .join(', ');
    },
    display: (val) => {
        if (val == null) return 'N/A';
        // Handle string values (sometimes APIs return strings directly)
        if (typeof val === 'string') {
            return val || 'N/A';
        }
        // Handle objects
        if (typeof val === 'object') {
            // Try display property first
            if (val.display !== undefined && val.display !== null && val.display !== '') {
                return val.display;
            }
            // Fallback to name
            if (val.name !== undefined && val.name !== null && val.name !== '') {
                return val.name;
            }
            // Fallback to id if available
            if (val.id !== undefined) {
                return String(val.id);
            }
        }
        return 'N/A';
    },
    value: (val) => {
        if (val == null) return 'N/A';
        // Handle string values
        if (typeof val === 'string') {
            return val || 'N/A';
        }
        // Handle objects
        if (typeof val === 'object') {
            if (val.value !== undefined && val.value !== null && val.value !== '') {
                return val.value;
            }
            // Fallback to display
            if (val.display !== undefined && val.display !== null && val.display !== '') {
                return val.display;
            }
            // Fallback to name
            if (val.name !== undefined && val.name !== null && val.name !== '') {
                return val.name;
            }
        }
        return 'N/A';
    },
    address: (val) => {
        if (val == null) return 'N/A';
        // Handle string values
        if (typeof val === 'string') {
            return val || 'N/A';
        }
        // Handle objects
        if (typeof val === 'object') {
            if (val.address !== undefined && val.address !== null && val.address !== '') {
                return val.address;
            }
            // Fallback to display
            if (val.display !== undefined && val.display !== null && val.display !== '') {
                return val.display;
            }
        }
        return 'N/A';
    },
    default: (val) => {
        if (val == null) return 'N/A';
        // For objects, try to get a meaningful display value
        if (typeof val === 'object' && !Array.isArray(val)) {
            return val.display ?? val.name ?? val.value ?? (val.id !== undefined ? String(val.id) : 'N/A');
        }
        // For arrays, join them
        if (Array.isArray(val)) {
            if (val.length === 0) return 'N/A';
            return val.map(item => {
                if (typeof item === 'object' && item !== null) {
                    return item.display ?? item.name ?? item.value ?? String(item);
                }
                return String(item);
            }).join(', ');
        }
        // For primitives, return as-is (empty string is valid)
        return val;
    },
};

// View configurations for each model type
export const viewConfigs = {
    status: {
        apiEndpoint: '/extras/statuses/',
        listRoute: 'status-list',
        detailRoute: 'status-detail',
        createRoute: 'status-create',
        title: 'Statuses',
        singularTitle: 'Status',
        columns: [
            { key: 'name', label: 'Name', sortable: true },
            {
                key: 'content_types',
                label: 'Content Types',
                formatter: formatters.contentTypes,
            },
        ],
        detailFields: (item) => ({
            Name: item.name ?? 'N/A',
            'Content Types': formatters.contentTypes(item.content_types),
        }),
        createFields: [
            {
                id: 'name',
                label: 'Name',
                type: 'text',
                required: true,
                placeholder: 'Status name',
            },
            {
                id: 'color',
                label: 'Color',
                type: 'color',
            },
            {
                id: 'description',
                label: 'Description',
                type: 'textarea',
                placeholder: 'Status description',
            },
            {
                id: 'content_types',
                label: 'Content Type(s)',
                type: 'multiselect',
                required: true,
                optionsEndpoint: '/extras/content-types/',
                optionsParams: { feature: 'statuses' },
                optionsMapper: (ct) => ({
                    value: `${ct.app_label}.${ct.model}`,
                    label: ct.display || ct.app_labeled_name,
                }),
            },
        ],
        createPayloadMapper: (formData) => {
            const payload = {
                name: formData.name,
                content_types: formData.content_types,
            };
            if (formData.description) {
                payload.description = formData.description;
            }
            if (formData.color) {
                payload.color = formData.color.replace(/^#/, '');
            }
            return payload;
        },
    },
    role: {
        apiEndpoint: '/extras/roles/',
        listRoute: 'role-list',
        detailRoute: 'role-detail',
        createRoute: 'role-create',
        title: 'Roles',
        singularTitle: 'Role',
        columns: [
            { key: 'name', label: 'Name', sortable: true },
            {
                key: 'description',
                label: 'Description',
                formatter: formatters.default,
            },
            {
                key: 'content_types',
                label: 'Content Types',
                formatter: formatters.contentTypes,
            },
        ],
        detailFields: (item) => ({
            Name: item.name ?? 'N/A',
            Description: item.description ?? 'N/A',
            'Content Types': formatters.contentTypes(item.content_types),
        }),
        createFields: [
            {
                id: 'name',
                label: 'Name',
                type: 'text',
                required: true,
                placeholder: 'Role name',
            },
            {
                id: 'weight',
                label: 'Weight',
                type: 'number',
                placeholder: '100',
                helpText: 'Higher weights appear first in lists',
            },
            {
                id: 'color',
                label: 'Color',
                type: 'color',
            },
            {
                id: 'description',
                label: 'Description',
                type: 'textarea',
                placeholder: 'Role description',
            },
            {
                id: 'content_types',
                label: 'Content Type(s)',
                type: 'multiselect',
                optionsEndpoint: '/extras/content-types/',
                optionsMapper: (ct) => ({
                    value: `${ct.app_label}.${ct.model}`,
                    label: ct.display || ct.app_labeled_name,
                }),
            },
        ],
        createPayloadMapper: (formData) => {
            const payload = {
                name: formData.name,
            };
            if (formData.description) {
                payload.description = formData.description;
            }
            if (formData.weight) {
                payload.weight = parseInt(formData.weight, 10);
            }
            if (formData.color) {
                payload.color = formData.color.replace(/^#/, '');
            }
            if (formData.content_types && formData.content_types.length > 0) {
                payload.content_types = formData.content_types;
            }
            return payload;
        },
    },
    device: {
        apiEndpoint: '/dcim/devices/',
        listRoute: 'device-list',
        detailRoute: 'device-detail',
        createRoute: 'device-create',
        title: 'Devices',
        singularTitle: 'Device',
        columns: [
            { key: 'name', label: 'Name', sortable: true },
            {
                key: 'device_type',
                label: 'Device Type',
                formatter: formatters.display,
            },
            {
                key: 'location',
                label: 'Location',
                formatter: formatters.display,
            },
            {
                key: 'status',
                label: 'Status',
                formatter: formatters.value,
            },
            {
                key: 'primary_ip4',
                label: 'Primary IP',
                formatter: formatters.address,
            },
        ],
        detailFields: (item) => ({
            Name: item.name ?? 'N/A',
            'Device Type': formatters.display(item.device_type),
            Location: formatters.display(item.location),
            Status: formatters.value(item.status),
            'Primary IP': formatters.address(item.primary_ip4),
        }),
        createFields: [], // TODO: Add device create fields
        createPayloadMapper: (formData) => formData,
    },
    // Add more model configurations as needed
};

/**
 * Map route names to model types (for routes that don't match model type exactly)
 */
const routeNameToModelType = {
    'device-type': 'deviceType',
    'location-type': 'locationType',
    'vlan-group': 'vlanGroup',
    'ip-address': 'ipAddress',
    // Add more mappings as needed
};

/**
 * Convert route name to model type
 * @param {string} routeName - The route name (e.g., 'status-list', 'device-type-list')
 * @returns {string} Model type (e.g., 'status', 'deviceType')
 */
function routeNameToModelTypeConverter(routeName) {
    // Remove '-list', '-detail', '-create' suffixes
    const baseName = routeName.replace(/-list$|-detail$|-create$/, '');
    // Check if there's a mapping for this route name
    return routeNameToModelType[baseName] || baseName;
}

/**
 * Get view configuration for a model type
 * @param {string} routeName - The route name (e.g., 'status-list', 'device-type-list')
 * @returns {object} View configuration object
 */
export function getViewConfig(routeName) {
    const modelType = routeNameToModelTypeConverter(routeName);
    const config = viewConfigs[modelType];
    if (!config) {
        throw new Error(`No view configuration found for route: ${routeName} (model type: ${modelType})`);
    }
    return config;
}

/**
 * Get all available model types
 * @returns {string[]} Array of model type names
 */
export function getAvailableModelTypes() {
    return Object.keys(viewConfigs);
}

