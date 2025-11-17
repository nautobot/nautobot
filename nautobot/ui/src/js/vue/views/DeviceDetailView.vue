<template>
    <div class="device-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="device">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ device.name || device.display }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link to="/devices">Devices</router-link>
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ device.name || device.display }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <button
                        class="btn btn-secondary me-2"
                        @click="$router.back()"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back
                    </button>
                    <button class="btn btn-primary" @click="refreshDevice">
                        <i class="mdi mdi-refresh"></i> Refresh
                    </button>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Device Information">
                        <KeyValueTable :data="deviceInfo" />
                    </DetailCard>
                </div>

                <div class="col-md-6">
                    <DetailCard title="Network Information">
                        <KeyValueTable :data="networkInfo" />
                    </DetailCard>
                </div>
            </div>

            <div class="row mt-4">
                <div class="col-12">
                    <DetailCard title="Additional Details">
                        <pre class="bg-light p-3 rounded">{{
                            JSON.stringify(device, null, 2)
                        }}</pre>
                    </DetailCard>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { inject, computed } from 'vue';
import DetailCard from '../components/DetailCard.vue';
import KeyValueTable from '../components/KeyValueTable.vue';

export default {
    name: 'DeviceDetailView',
    components: {
        DetailCard,
        KeyValueTable,
    },
    props: {
        id: {
            type: [String, Number],
            required: true,
        },
    },
    data() {
        return {
            device: null,
            loading: false,
            error: null,
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    computed: {
        deviceInfo() {
            if (!this.device) return {};
            return {
                'Device Type': this.device.device_type?.display || 'N/A',
                Location: this.device.location?.display || 'N/A',
                Status: this.device.status?.value || 'N/A',
                Role: this.device.role?.display || 'N/A',
                Platform: this.device.platform?.display || 'N/A',
            };
        },
        networkInfo() {
            if (!this.device) return {};
            return {
                'Primary IPv4': this.device.primary_ip4?.address || 'N/A',
                'Primary IPv6': this.device.primary_ip6?.address || 'N/A',
                'Serial Number': this.device.serial || 'N/A',
                'Asset Tag': this.device.asset_tag || 'N/A',
            };
        },
    },
    mounted() {
        this.loadDevice();
    },
    watch: {
        id() {
            this.loadDevice();
        },
    },
    methods: {
        async loadDevice() {
            this.loading = true;
            this.error = null;

            try {
                this.device = await this.api.get(`/dcim/devices/${this.id}/`);
            } catch (err) {
                this.error = err.message || 'Failed to load device';
                console.error('Error loading device:', err);
            } finally {
                this.loading = false;
            }
        },
        refreshDevice() {
            this.loadDevice();
        },
    },
};
</script>

<style scoped>
.device-detail-view {
    padding: 1rem 0;
}
</style>
