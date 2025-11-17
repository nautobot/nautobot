<template>
    <div class="vrf-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>VRFs</h1>
            <div>
                <router-link
                    :to="{ name: 'vrf-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add VRF
                </router-link>
                <button class="btn btn-secondary" @click="refreshVRFs">
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
                :items="vrfs"
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
    name: 'VRFListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            vrfs: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'name', label: 'Name', sortable: true },
                {
                    key: 'rd',
                    label: 'Route Distinguisher',
                    formatter: (val) => val || 'N/A',
                },
                {
                    key: 'namespace',
                    label: 'Namespace',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'status',
                    label: 'Status',
                    formatter: (val) => val?.value || 'N/A',
                },
                {
                    key: 'tenant',
                    label: 'Tenant',
                    formatter: (val) => val?.display || 'N/A',
                },
            ],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadVRFs();
    },
    methods: {
        async loadVRFs(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/ipam/vrfs/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.vrfs = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load VRFs';
                // eslint-disable-next-line no-console
                console.error('Error loading VRFs:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(vrf) {
            this.$router.push({
                name: 'vrf-detail',
                params: { id: vrf.id },
            });
        },
        handlePageChange(page) {
            this.loadVRFs(page);
        },
        refreshVRFs() {
            this.loadVRFs(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.vrf-list-view {
    padding: 1rem 0;
}
</style>
