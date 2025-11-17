<template>
    <div class="location-type-list-view">
        <div
            class="align-items-center d-flex gap-8 justify-content-end mb-16 d-print-none"
        >
            <div class="btn-group">
                <router-link
                    :to="{ name: 'location-type-create' }"
                    class="btn btn-primary"
                >
                    <span class="mdi mdi-plus-thick" aria-hidden="true"></span>
                    Add Location Type
                </router-link>
                <button
                    type="button"
                    id="actions-dropdown"
                    class="btn btn-primary dropdown-toggle"
                    data-bs-toggle="dropdown"
                >
                    <span class="visually-hidden">Toggle Dropdown</span>
                    <span class="mdi mdi-chevron-down"></span>
                </button>
                <ul class="dropdown-menu dropdown-menu-end" role="menu">
                    <li>
                        <button
                            class="dropdown-item"
                            @click="refreshLocationTypes"
                        >
                            <span class="mdi mdi-refresh"></span> Refresh
                        </button>
                    </li>
                </ul>
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
            <div class="card">
                <div class="card-body">
                    <DataTable
                        :items="locationTypes"
                        :columns="columns"
                        :loading="loading"
                        @row-click="handleRowClick"
                    />
                </div>
                <div v-if="pagination" class="card-footer">
                    <Pagination
                        :current-page="pagination.currentPage"
                        :total-pages="pagination.totalPages"
                        :total-count="pagination.totalCount"
                        @page-change="handlePageChange"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { inject } from 'vue';
import DataTable from '../components/DataTable.vue';
import Pagination from '../components/Pagination.vue';

export default {
    name: 'LocationTypeListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            locationTypes: [],
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
                    key: 'nestable',
                    label: 'Nestable',
                    formatter: (val) => (val ? 'Yes' : 'No'),
                },
                {
                    key: 'location_count',
                    label: 'Locations',
                },
            ],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadLocationTypes();
    },
    methods: {
        async loadLocationTypes(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList(
                    '/dcim/location-types/',
                    {
                        limit: this.pageSize,
                        offset,
                        depth: 1, // Include nested objects with display fields
                    },
                );
                this.locationTypes = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load location types';
                // eslint-disable-next-line no-console
                console.error('Error loading location types:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(locationType) {
            this.$router.push({
                name: 'location-type-detail',
                params: { id: locationType.id },
            });
        },
        handlePageChange(page) {
            this.loadLocationTypes(page);
        },
        refreshLocationTypes() {
            this.loadLocationTypes(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.location-type-list-view {
    padding: 1rem 0;
}
</style>
