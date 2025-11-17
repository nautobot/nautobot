<template>
    <div class="namespace-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Namespaces</h1>
            <div>
                <router-link
                    :to="{ name: 'namespace-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Namespace
                </router-link>
                <button class="btn btn-secondary" @click="refreshNamespaces">
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
                :items="namespaces"
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
    name: 'NamespaceListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            namespaces: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'name', label: 'Name', sortable: true },
                {
                    key: 'location',
                    label: 'Location',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'description',
                    label: 'Description',
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
        this.loadNamespaces();
    },
    methods: {
        async loadNamespaces(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/ipam/namespaces/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.namespaces = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load namespaces';
                // eslint-disable-next-line no-console
                console.error('Error loading namespaces:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(namespace) {
            this.$router.push({
                name: 'namespace-detail',
                params: { id: namespace.id },
            });
        },
        handlePageChange(page) {
            this.loadNamespaces(page);
        },
        refreshNamespaces() {
            this.loadNamespaces(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.namespace-list-view {
    padding: 1rem 0;
}
</style>
