<template>
    <div class="data-table">
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th
                            v-for="column in columns"
                            :key="column.key"
                            :class="{ sortable: column.sortable }"
                            @click="column.sortable && handleSort(column.key)"
                        >
                            {{ column.label }}
                            <i
                                v-if="column.sortable"
                                class="mdi"
                                :class="getSortIcon(column.key)"
                            ></i>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="(item, index) in items"
                        :key="item.id || index"
                        @click="handleRowClick(item)"
                        style="cursor: pointer"
                    >
                        <td v-for="column in columns" :key="column.key">
                            {{ formatCell(getValue(item, column.key), column) }}
                        </td>
                    </tr>
                    <tr v-if="items.length === 0">
                        <td
                            :colspan="columns.length"
                            class="text-center text-muted py-4"
                        >
                            No items found
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
export default {
    name: 'DataTable',
    props: {
        items: {
            type: Array,
            required: true,
            default: () => [],
        },
        columns: {
            type: Array,
            required: true,
        },
        loading: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            sortColumn: null,
            sortDirection: 'asc',
        };
    },
    methods: {
        /**
         * Safely get a value from an item using a key path
         * Supports both simple keys and nested paths (e.g., 'device_type' or 'device_type.display')
         */
        getValue(item, key) {
            if (!item || !key) {
                return undefined;
            }
            // If key contains a dot, it's a nested path
            if (key.includes('.')) {
                const keys = key.split('.');
                let value = item;
                for (const k of keys) {
                    if (value == null) {
                        return undefined;
                    }
                    value = value[k];
                }
                return value;
            }
            return item[key];
        },
        formatCell(value, column) {
            // If value is explicitly undefined (field doesn't exist), try to get it from the item
            // This handles cases where the API might not include the field
            if (value === undefined && column.key) {
                // Value should already be extracted, but this is a safety check
                // The actual extraction happens in the template
            }
            
            // Use formatter if provided
            if (column.formatter && typeof column.formatter === 'function') {
                return column.formatter(value);
            }
            
            // Handle null/undefined values
            if (value === null || value === undefined) {
                return 'N/A';
            }
            
            // Handle objects - try to extract display value
            if (typeof value === 'object' && !Array.isArray(value)) {
                // Try common display properties
                if (value.display !== undefined && value.display !== null) {
                    return value.display;
                }
                if (value.name !== undefined && value.name !== null) {
                    return value.name;
                }
                if (value.value !== undefined && value.value !== null) {
                    return value.value;
                }
                if (value.address !== undefined && value.address !== null) {
                    return value.address;
                }
                // If object has an id but no display, show the id
                if (value.id !== undefined) {
                    return value.id;
                }
                // Last resort: stringify (but this shouldn't happen in normal cases)
                return JSON.stringify(value);
            }
            
            // Handle arrays
            if (Array.isArray(value)) {
                if (value.length === 0) {
                    return 'N/A';
                }
                return value.map(item => {
                    if (typeof item === 'object' && item !== null) {
                        return item.display || item.name || item.value || String(item);
                    }
                    return String(item);
                }).join(', ');
            }
            
            // For primitive values, return as-is (empty string is valid, don't convert to N/A)
            return value;
        },
        handleSort(columnKey) {
            if (this.sortColumn === columnKey) {
                this.sortDirection =
                    this.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortColumn = columnKey;
                this.sortDirection = 'asc';
            }
            this.$emit('sort', {
                column: this.sortColumn,
                direction: this.sortDirection,
            });
        },
        getSortIcon(columnKey) {
            if (this.sortColumn !== columnKey) {
                return 'mdi-sort';
            }
            return this.sortDirection === 'asc'
                ? 'mdi-sort-ascending'
                : 'mdi-sort-descending';
        },
        handleRowClick(item) {
            this.$emit('row-click', item);
        },
    },
};
</script>

<style scoped>
.table th.sortable {
    cursor: pointer;
    user-select: none;
}

.table th.sortable:hover {
    background-color: rgba(0, 0, 0, 0.05);
}

.table th {
    position: relative;
    padding-right: 2rem;
}

.table th .mdi {
    position: absolute;
    right: 0.5rem;
    top: 50%;
    transform: translateY(-50%);
}
</style>
