<template>
    <div class="manufacturer-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Manufacturers</h1>
            <div>
                <router-link
                    :to="{ name: 'manufacturer-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add Manufacturer
                </router-link>
                <button class="btn btn-secondary" @click="refreshManufacturers">
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
                :items="manufacturers"
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
    name: 'ManufacturerListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            manufacturers: [],
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
                    key: 'device_type_count',
                    label: 'Device Types',
                },
            ],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadManufacturers();
    },
    methods: {
        async loadManufacturers(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList(
                    '/dcim/manufacturers/',
                    {
                        limit: this.pageSize,
                        offset,
                        depth: 1, // Include nested objects with display fields
                    },
                );
                this.manufacturers = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load manufacturers';
                // eslint-disable-next-line no-console
                console.error('Error loading manufacturers:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(manufacturer) {
            this.$router.push({
                name: 'manufacturer-detail',
                params: { id: manufacturer.id },
            });
        },
        handlePageChange(page) {
            this.loadManufacturers(page);
        },
        refreshManufacturers() {
            this.loadManufacturers(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.manufacturer-list-view {
    padding: 1rem 0;
}
</style>
