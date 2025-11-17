<template>
    <div class="status-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Statuses</h1>
            <div>
                <router-link
                    :to="{ name: 'status-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Status
                </router-link>
                <button class="btn btn-secondary" @click="refreshStatuses">
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
                :items="statuses"
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
    name: 'StatusListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            statuses: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'name', label: 'Name', sortable: true },
                {
                    key: 'content_types',
                    label: 'Content Types',
                    formatter: (val) => {
                        // Handle null/undefined
                        if (!val) {
                            return 'N/A';
                        }
                        // Ensure val is an array
                        const contentTypes = Array.isArray(val) ? val : [val];
                        // Filter out any null/undefined values and format
                        return contentTypes
                            .filter((ct) => ct != null)
                            .map((ct) => {
                                // ContentTypeField returns strings like "app_label.model"
                                if (typeof ct === 'string') {
                                    return ct;
                                }
                                // Fallback for nested objects (if API changes in future)
                                return ct.display || ct.model || String(ct);
                            })
                            .join(', ') || 'N/A';
                    },
                },
            ],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadStatuses();
    },
    methods: {
        async loadStatuses(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/extras/statuses/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.statuses = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load statuses';
                // eslint-disable-next-line no-console
                console.error('Error loading statuses:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(status) {
            this.$router.push({
                name: 'status-detail',
                params: { id: status.id },
            });
        },
        handlePageChange(page) {
            this.loadStatuses(page);
        },
        refreshStatuses() {
            this.loadStatuses(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.status-list-view {
    padding: 1rem 0;
}
</style>
