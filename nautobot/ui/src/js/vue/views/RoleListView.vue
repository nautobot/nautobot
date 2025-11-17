<template>
    <div class="role-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Roles</h1>
            <div>
                <router-link
                    :to="{ name: 'role-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Role
                </router-link>
                <button class="btn btn-secondary" @click="refreshRoles">
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
                :items="roles"
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
    name: 'RoleListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            roles: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'name', label: 'Name', sortable: true },
                {
                    key: 'description',
                    label: 'Description',
                    formatter: (val) => val || 'N/A',
                },
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
        this.loadRoles();
    },
    methods: {
        async loadRoles(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/extras/roles/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.roles = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load roles';
                // eslint-disable-next-line no-console
                console.error('Error loading roles:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(role) {
            this.$router.push({
                name: 'role-detail',
                params: { id: role.id },
            });
        },
        handlePageChange(page) {
            this.loadRoles(page);
        },
        refreshRoles() {
            this.loadRoles(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.role-list-view {
    padding: 1rem 0;
}
</style>
