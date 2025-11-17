<template>
    <div class="interface-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Interfaces</h1>
            <div>
                <router-link
                    :to="{ name: 'interface-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Interface
                </router-link>
                <button class="btn btn-secondary" @click="refreshInterfaces">
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
                :items="interfaces"
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
    name: 'InterfaceListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            interfaces: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'name', label: 'Name', sortable: true },
                {
                    key: 'device',
                    label: 'Device',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'type',
                    label: 'Type',
                    formatter: (val) => val?.value || 'N/A',
                },
                {
                    key: 'status',
                    label: 'Status',
                    formatter: (val) => val?.value || 'N/A',
                },
                {
                    key: 'enabled',
                    label: 'Enabled',
                    formatter: (val) => (val ? 'Yes' : 'No'),
                },
                {
                    key: 'mac_address',
                    label: 'MAC Address',
                    formatter: (val) => val || 'N/A',
                },
            ],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadInterfaces();
    },
    methods: {
        async loadInterfaces(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/dcim/interfaces/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.interfaces = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load interfaces';
                // eslint-disable-next-line no-console
                console.error('Error loading interfaces:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(interfaceItem) {
            this.$router.push({
                name: 'interface-detail',
                params: { id: interfaceItem.id },
            });
        },
        handlePageChange(page) {
            this.loadInterfaces(page);
        },
        refreshInterfaces() {
            this.loadInterfaces(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.interface-list-view {
    padding: 1rem 0;
}
</style>
