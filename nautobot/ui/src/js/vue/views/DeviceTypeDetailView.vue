<template>
    <div class="device-type-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="deviceType">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ deviceType.display || deviceType.model }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'device-type-list' }"
                                    >Device Types</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ deviceType.display || deviceType.model }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'device-type-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Device Type Information">
                        <KeyValueTable :data="deviceTypeInfo" />
                    </DetailCard>
                </div>
                <div class="col-md-6">
                    <DetailCard title="Physical Specifications">
                        <KeyValueTable :data="physicalSpecs" />
                    </DetailCard>
                </div>
            </div>

            <div v-if="deviceType.comments" class="mt-4">
                <DetailCard title="Comments">
                    <p>{{ deviceType.comments }}</p>
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
    name: 'DeviceTypeDetailView',
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
            deviceType: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        deviceTypeInfo() {
            if (!this.deviceType) return {};
            return {
                Model: this.deviceType.model || 'N/A',
                Manufacturer: this.deviceType.manufacturer?.display || 'N/A',
                'Device Family':
                    this.deviceType.device_family?.display || 'N/A',
                'Part Number': this.deviceType.part_number || 'N/A',
                'Device Count': this.deviceType.device_count || 0,
            };
        },
        physicalSpecs() {
            if (!this.deviceType) return {};
            return {
                'Height (U)': this.deviceType.u_height || 'N/A',
                'Is Full Depth': this.deviceType.is_full_depth ? 'Yes' : 'No',
                'Subdevice Role':
                    this.deviceType.subdevice_role?.value || 'N/A',
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadDeviceType();
    },
    methods: {
        async loadDeviceType() {
            this.loading = true;
            this.error = null;

            try {
                this.deviceType = await this.api.get(
                    `/dcim/device-types/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load device type';
                // eslint-disable-next-line no-console
                console.error('Error loading device type:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.device-type-detail-view {
    padding: 1rem 0;
}
</style>
