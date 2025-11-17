<template>
    <div class="generic-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>{{ config.title }}</h1>
            <div>
                <router-link
                    :to="{ name: config.createRoute }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add {{ config.singularTitle }}
                </router-link>
                <button class="btn btn-secondary" @click="refreshItems">
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
                :items="items"
                :columns="config.columns"
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
import { inject, computed } from 'vue';
import { useRoute } from 'vue-router';
import DataTable from '../components/DataTable.vue';
import Pagination from '../components/Pagination.vue';
import { getViewConfig } from '../config/viewConfig.js';

export default {
    name: 'GenericListView',
    components: {
        DataTable,
        Pagination,
    },
    setup() {
        const api = inject('api');
        const route = useRoute();
        // Get config from route name
        const config = computed(() => getViewConfig(route.name || ''));
        
        return { api, config };
    },
    data() {
        return {
            items: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
        };
    },
    mounted() {
        this.loadItems();
    },
    watch: {
        // Reload when route changes (e.g., different model type)
        '$route.name'() {
            this.loadItems();
        },
    },
    methods: {
        async loadItems(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList(this.config.apiEndpoint, {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.items = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || `Failed to load ${this.config.title.toLowerCase()}`;
                // eslint-disable-next-line no-console
                console.error(`Error loading ${this.config.title.toLowerCase()}:`, err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(item) {
            this.$router.push({
                name: this.config.detailRoute,
                params: { id: item.id },
            });
        },
        handlePageChange(page) {
            this.loadItems(page);
        },
        refreshItems() {
            this.loadItems(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.generic-list-view {
    padding: 1rem 0;
}
</style>

