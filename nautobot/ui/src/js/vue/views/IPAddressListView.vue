<template>
    <div class="ip-address-list-view">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>IP Addresses</h1>
            <div>
                <router-link
                    :to="{ name: 'ip-address-create' }"
                    class="btn btn-primary me-2"
                >
                    <i class="mdi mdi-plus"></i> Add IP Address
                </router-link>
                <button class="btn btn-secondary" @click="refreshIPAddresses">
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
                :items="ipAddresses"
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
    name: 'IPAddressListView',
    components: {
        DataTable,
        Pagination,
    },
    data() {
        return {
            ipAddresses: [],
            loading: false,
            error: null,
            pagination: null,
            pageSize: 50,
            columns: [
                {
                    key: 'address',
                    label: 'Address',
                    formatter: (val) => val || 'N/A',
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
                {
                    key: 'dns_name',
                    label: 'DNS Name',
                    formatter: (val) => val || 'N/A',
                },
                {
                    key: 'parent',
                    label: 'Parent Prefix',
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
        this.loadIPAddresses();
    },
    methods: {
        async loadIPAddresses(page = 1) {
            this.loading = true;
            this.error = null;

            try {
                const offset = (page - 1) * this.pageSize;
                const response = await this.api.getList('/ipam/ip-addresses/', {
                    limit: this.pageSize,
                    offset,
                    depth: 1, // Include nested objects with display fields
                });
                this.ipAddresses = response.results || [];

                if (response.count !== undefined) {
                    this.pagination = {
                        currentPage: page,
                        totalPages: Math.ceil(response.count / this.pageSize),
                        totalCount: response.count,
                    };
                }
            } catch (err) {
                this.error = err.message || 'Failed to load IP addresses';
                // eslint-disable-next-line no-console
                console.error('Error loading IP addresses:', err);
            } finally {
                this.loading = false;
            }
        },
        handleRowClick(ipAddress) {
            this.$router.push({
                name: 'ip-address-detail',
                params: { id: ipAddress.id },
            });
        },
        handlePageChange(page) {
            this.loadIPAddresses(page);
        },
        refreshIPAddresses() {
            this.loadIPAddresses(this.pagination?.currentPage || 1);
        },
    },
};
</script>

<style scoped>
.ip-address-list-view {
    padding: 1rem 0;
}
</style>
