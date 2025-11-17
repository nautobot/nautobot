<template>
    <div class="platform-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Platforms</h1>
            <div>
                <router-link
                    :to="{ name: 'platform-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Platform
                </router-link>
                <button class="btn btn-secondary" @click="refreshPlatforms">
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
                :items="platforms"
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
    name: 'PlatformListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            platforms: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                { key: 'name', label: 'Name', sortable: true },
                {
                    key: 'manufacturer',
                    label: 'Manufacturer',
                    formatter: (val) => val?.display || 'N/A',
                },
                {
                    key: 'network_driver',
                    label: 'Network Driver',
                    formatter: (val) => val || 'N/A',
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
        this.loadPlatforms();
    },
    methods: {
        async loadPlatforms(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/dcim/platforms/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.platforms = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load platforms';
                // eslint-disable-next-line no-console
                console.error('Error loading platforms:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(platform) {
            this.$router.push({
                name: 'platform-detail',
                params: { id: platform.id },
            });
        },
        handlePageChange(page) {
            this.loadPlatforms(page);
        },
        refreshPlatforms() {
            this.loadPlatforms(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.platform-list-view {
    padding: 1rem 0;
}
</style>
