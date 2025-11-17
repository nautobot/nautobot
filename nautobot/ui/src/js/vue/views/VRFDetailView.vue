<template>
    <div class="vrf-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="vrf">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ vrf.display || vrf.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'vrf-list' }"
                                    >VRFs</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ vrf.display || vrf.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'vrf-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="VRF Information">
                        <KeyValueTable :data="vrfInfo" />
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
    name: 'VRFDetailView',
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
            vrf: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        vrfInfo() {
            if (!this.vrf) return {};
            return {
                Name: this.vrf.name || 'N/A',
                'Route Distinguisher': this.vrf.rd || 'N/A',
                Namespace: this.vrf.namespace?.display || 'N/A',
                Status: this.vrf.status?.value || 'N/A',
                Tenant: this.vrf.tenant?.display || 'N/A',
            };
        },
        assignmentInfo() {
            if (!this.vrf) return {};
            return {
                Description: this.vrf.description || 'N/A',
                'Device Count': this.vrf.device_count || 0,
                'Prefix Count': this.vrf.prefix_count || 0,
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadVRF();
    },
    methods: {
        async loadVRF() {
            this.loading = true;
            this.error = null;

            try {
                this.vrf = await this.api.get(`/ipam/vrfs/${this.id}/`);
            } catch (err) {
                this.error = err.message || 'Failed to load VRF';
                // eslint-disable-next-line no-console
                console.error('Error loading VRF:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.vrf-detail-view {
    padding: 1rem 0;
}
</style>
