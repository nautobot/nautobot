<template>
    <div class="device-type-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Device Types</h1>
            <div>
                <router-link
                    :to="{ name: 'device-type-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Device Type
                </router-link>
                <button class="btn btn-secondary" @click="refreshDeviceTypes">
                    <i class="mdi mdi-refresh"></i> Refresh
                </button>
            </div>
        </div>

        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else>
            <DataTable
                :items="deviceTypes"
                :columns="columns"
                :loading="loading"
                @row-click="handleRowClick"
            />

            <Pagination
                v-if="pagination"
                :current-page="pagination.currentPage"
                :total-pages="pagination.totalPages"
                :total-count="pagination.totalCount"
                @page-change="handlePageChange"
            />
        </div>
    </div>
</template>

<script>
import { inject } from 'vue';
import DataTable from '../components/DataTable.vue';
import Pagination from '../components/Pagination.vue';

export default {
    name: 'DeviceTypeListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            deviceTypes: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'model', label: 'Model', sortable: true },
                {
                    key: 'manufacturer',
                    label: 'Manufacturer',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'device_family',
                    label: 'Device Family',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'u_height',
                    label: 'Height (U)',
                },
                {
                    key: 'device_count',
                    label: 'Devices',
                },
            ],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadDeviceTypes();
    },
    methods: {
        async loadDeviceTypes(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/dcim/device-types/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.deviceTypes = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load device types';
                // eslint-disable-next-line no-console
                console.error('Error loading device types:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(deviceType) {
            this.$router.push({
                name: 'device-type-detail',
                params: { id: deviceType.id },
            });
        },
        handlePageChange(page) {
            this.loadDeviceTypes(page);
        },
        refreshDeviceTypes() {
            this.loadDeviceTypes(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.device-type-list-view {
    padding: 1rem 0;
}
</style>
