<template>
    <table class="table table-sm">
        <tbody>
            <tr v-for="(value, key) in data" :key="key">
                <th scope="row" style="width: 30%">{{ key }}</th>
                <td>{{ formatValue(value) }}</td>
            </tr>
        </tbody>
    </table>
</template>

<script>
export default {
    name: 'KeyValueTable',
    props: {
        data: {
            type: Object,
            required: true,
            default: () => ({}),
        },
    },
    methods: {
        formatValue(value) {
            if (value === null || value === undefined) {
                return 'N/A';
            }
            if (typeof value === 'object' && !Array.isArray(value)) {
                // For objects, try to get a display value, but don't show N/A for empty strings
                return value.display ?? value.name ?? (value.value !== undefined ? value.value : JSON.stringify(value));
            }
            // For arrays, empty strings, numbers, etc., return as-is
            return value;
        },
    },
};
</script>

<style scoped>
.table th {
    font-weight: 600;
    color: #495057;
}
</style>
