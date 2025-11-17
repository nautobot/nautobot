<template>
    <div class="device-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Devices</h1>
            <div>
                <router-link
                    :to="{ name: 'device-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Device
                </router-link>
                <button class="btn btn-secondary" @click="refreshDevices">
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
                :items="devices"
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
    name: 'DeviceListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            devices: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50, // Default page size for Nautobot API
            columns: [
                { key: 'name', label: 'Name', sortable: true },
                {
                    key: 'device_type',
                    label: 'Device Type',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'location',
                    label: 'Location',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'status',
                    label: 'Status',
                    formatter: (val) => val?.value || 'N/A',
                },
                {
                    key: 'primary_ip4',
                    label: 'Primary IP',
                    formatter: (val) => val?.address || 'N/A',
                },
            ],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadDevices();
    },
    methods: {
        async loadDevices(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                // Convert page number to offset/limit for Nautobot API
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/dcim/devices/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.devices = response.results || [];

                // Extract pagination info from response
                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load devices';
                // eslint-disable-next-line no-console
                console.error('Error loading devices:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(device) {
            this.$router.push({
                name: 'device-detail',
                params: { id: device.id },
            });
        },
        handlePageChange(page) {
            this.loadDevices(page);
        },
        refreshDevices() {
            this.loadDevices(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.device-list-view {
    padding: 1rem 0;
}
</style>
