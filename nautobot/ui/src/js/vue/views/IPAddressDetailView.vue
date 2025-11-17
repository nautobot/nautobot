<template>
    <div class="ip-address-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="ipAddress">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ ipAddress.display || ipAddress.address }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'ip-address-list' }"
                                    >IP Addresses</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ ipAddress.display || ipAddress.address }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'ip-address-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="IP Address Information">
                        <KeyValueTable :data="ipAddressInfo" />
                    </DetailCard>
                </div>
                <div class="col-md-6">
                    <DetailCard title="Assignment Information">
                        <KeyValueTable :data="assignmentInfo" />
                    </DetailCard>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { inject } from 'vue';
import DetailCard from '../components/DetailCard.vue';
import KeyValueTable from '../components/KeyValueTable.vue';

export default {
    name: 'IPAddressDetailView',
    components: {
        DetailCard,
        KeyValueTable,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            ipAddress: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        ipAddressInfo() {
            if (!this.ipAddress) return {};
            return {
                Address: this.ipAddress.address || 'N/A',
                'IP Version': this.ipAddress.ip_version || 'N/A',
                'Mask Length': this.ipAddress.mask_length || 'N/A',
                Status: this.ipAddress.status?.value || 'N/A',
                Role: this.ipAddress.role?.display || 'N/A',
                'DNS Name': this.ipAddress.dns_name || 'N/A',
            };
        },
        assignmentInfo() {
            if (!this.ipAddress) return {};
            return {
                'Parent Prefix': this.ipAddress.parent?.display || 'N/A',
                Namespace: this.ipAddress.namespace?.display || 'N/A',
                Description: this.ipAddress.description || 'N/A',
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadIPAddress();
    },
    methods: {
        async loadIPAddress() {
            this.loading = true;
            this.error = null;

            try {
                this.ipAddress = await this.api.get(
                    `/ipam/ip-addresses/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load IP address';
                // eslint-disable-next-line no-console
                console.error('Error loading IP address:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.ip-address-detail-view {
    padding: 1rem 0;
}
</style>
