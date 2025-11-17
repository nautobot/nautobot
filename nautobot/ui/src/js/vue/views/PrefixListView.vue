<template>
    <div class="prefix-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Prefixes</h1>
            <div>
                <router-link
                    :to="{ name: 'prefix-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Prefix
                </router-link>
                <button class="btn btn-secondary" @click="refreshPrefixes">
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
                :items="prefixes"
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
    name: 'PrefixListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            prefixes: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'prefix', label: 'Prefix', sortable: true },
                {
                    key: 'vrf',
                    label: 'VRF',
                    formatter: (val) => val?.display || 'Global',
                },
                {
                    key: 'status',
                    label: 'Status',
                    formatter: (val) => val?.value || 'N/A',
                },
                {
                    key: 'role',
                    label: 'Role',
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
        this.loadPrefixes();
    },
    methods: {
        async loadPrefixes(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                // Convert page number to offset/limit for Nautobot API
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/ipam/prefixes/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.prefixes = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load prefixes';
                // eslint-disable-next-line no-console
                console.error('Error loading prefixes:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(prefix) {
            this.$router.push({
                name: 'prefix-detail',
                params: { id: prefix.id },
            });
        },
        handlePageChange(page) {
            this.loadPrefixes(page);
        },
        refreshPrefixes() {
            this.loadPrefixes(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.prefix-list-view {
    padding: 1rem 0;
}
</style>
