<template>
    <div class="interface-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="interfaceItem">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ interfaceItem.display || interfaceItem.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'interface-list' }"
                                    >Interfaces</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{
                                    interfaceItem.display || interfaceItem.name
                                }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'interface-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Interface Information">
                        <KeyValueTable :data="interfaceInfo" />
                    </DetailCard>
                </div>
                <div class="col-md-6">
                    <DetailCard title="Device Information">
                        <KeyValueTable :data="deviceInfo" />
                    </DetailCard>
                </div>
            </div>

            <div v-if="interfaceItem.description" class="mt-4">
                <DetailCard title="Description">
                    <p>{{ interfaceItem.description }}</p>
                </DetailCard>
            </div>
        </div>
    </div>
</template>

<script>
import { inject } from 'vue';
import DetailCard from '../components/DetailCard.vue';
import KeyValueTable from '../components/KeyValueTable.vue';

export default {
    name: 'InterfaceDetailView',
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
            interfaceItem: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        interfaceInfo() {
            if (!this.interfaceItem) return {};
            return {
                Name: this.interfaceItem.name || 'N/A',
                Type: this.interfaceItem.type?.value || 'N/A',
                Status: this.interfaceItem.status?.value || 'N/A',
                Enabled: this.interfaceItem.enabled ? 'Yes' : 'No',
                'MAC Address': this.interfaceItem.mac_address || 'N/A',
                MTU: this.interfaceItem.mtu || 'N/A',
                Mode: this.interfaceItem.mode?.value || 'N/A',
                Role: this.interfaceItem.role?.display || 'N/A',
                'Management Only': this.interfaceItem.mgmt_only ? 'Yes' : 'No',
            };
        },
        deviceInfo() {
            if (!this.interfaceItem) return {};
            return {
                Device: this.interfaceItem.device?.display || 'N/A',
                Module: this.interfaceItem.module?.display || 'N/A',
                'IP Address Count': this.interfaceItem.ip_address_count || 0,
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadInterface();
    },
    methods: {
        async loadInterface() {
            this.loading = true;
            this.error = null;

            try {
                this.interfaceItem = await this.api.get(
                    `/dcim/interfaces/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load interface';
                // eslint-disable-next-line no-console
                console.error('Error loading interface:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.interface-detail-view {
    padding: 1rem 0;
}
</style>
