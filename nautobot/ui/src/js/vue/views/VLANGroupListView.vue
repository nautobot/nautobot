<template>
    <div class="vlan-group-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>VLAN Groups</h1>
            <div>
                <router-link
                    :to="{ name: 'vlan-group-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add VLAN Group
                </router-link>
                <button class="btn btn-secondary" @click="refreshVLANGroups">
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
                :items="vlanGroups"
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
    name: 'VLANGroupListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            vlanGroups: [],
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
                    key: 'range',
                    label: 'VLAN Range',
                    formatter: (val) => val || 'N/A',
                },
                {
                    key: 'vlan_count',
                    label: 'VLANs',
                },
            ],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadVLANGroups();
    },
    methods: {
        async loadVLANGroups(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/ipam/vlan-groups/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.vlanGroups = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load VLAN groups';
                // eslint-disable-next-line no-console
                console.error('Error loading VLAN groups:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(vlanGroup) {
            this.$router.push({
                name: 'vlan-group-detail',
                params: { id: vlanGroup.id },
            });
        },
        handlePageChange(page) {
            this.loadVLANGroups(page);
        },
        refreshVLANGroups() {
            this.loadVLANGroups(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.vlan-group-list-view {
    padding: 1rem 0;
}
</style>
