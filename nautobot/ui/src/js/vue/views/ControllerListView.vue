<template>
    <div class="controller-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Controllers</h1>
            <div>
                <router-link
                    :to="{ name: 'controller-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Controller
                </router-link>
                <button class="btn btn-secondary" @click="refreshControllers">
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
                :items="controllers"
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
    name: 'ControllerListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            controllers: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'name', label: 'Name', sortable: true },
                {
                    key: 'status',
                    label: 'Status',
                    formatter: (val) => val?.value || 'N/A',
                },
                {
                    key: 'location',
                    label: 'Location',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'platform',
                    label: 'Platform',
                    formatter: (val) => val?.display || 'N/A',
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
        this.loadControllers();
    },
    methods: {
        async loadControllers(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/dcim/controllers/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.controllers = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load controllers';
                // eslint-disable-next-line no-console
                console.error('Error loading controllers:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(controller) {
            this.$router.push({
                name: 'controller-detail',
                params: { id: controller.id },
            });
        },
        handlePageChange(page) {
            this.loadControllers(page);
        },
        refreshControllers() {
            this.loadControllers(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.controller-list-view {
    padding: 1rem 0;
}
</style>
