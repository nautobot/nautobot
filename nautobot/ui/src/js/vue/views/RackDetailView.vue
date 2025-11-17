<template>
    <div class="rack-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="rack">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ rack.display || rack.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'rack-list' }"
                                    >Racks</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ rack.display || rack.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'rack-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Rack Information">
                        <KeyValueTable :data="rackInfo" />
                    </DetailCard>
                </div>
                <div class="col-md-6">
                    <DetailCard title="Location Information">
                        <KeyValueTable :data="locationInfo" />
                    </DetailCard>
                </div>
            </div>

            <div v-if="rack.comments" class="mt-4">
                <DetailCard title="Comments">
                    <p>{{ rack.comments }}</p>
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
    name: 'RackDetailView',
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
            rack: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        rackInfo() {
            if (!this.rack) return {};
            return {
                Name: this.rack.name || 'N/A',
                'Facility ID': this.rack.facility_id || 'N/A',
                Status: this.rack.status?.value || 'N/A',
                Role: this.rack.role?.display || 'N/A',
                Type: this.rack.type?.value || 'N/A',
                Width: this.rack.width?.value || 'N/A',
                'Height (U)': this.rack.u_height || 'N/A',
                'Descending Units': this.rack.desc_units ? 'Yes' : 'No',
                Serial: this.rack.serial || 'N/A',
                'Asset Tag': this.rack.asset_tag || 'N/A',
            };
        },
        locationInfo() {
            if (!this.rack) return {};
            return {
                Location: this.rack.location?.display || 'N/A',
                'Rack Group': this.rack.rack_group?.display || 'N/A',
                Tenant: this.rack.tenant?.display || 'N/A',
                'Device Count': this.rack.device_count || 0,
                'Power Feed Count': this.rack.power_feed_count || 0,
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadRack();
    },
    methods: {
        async loadRack() {
            this.loading = true;
            this.error = null;

            try {
                this.rack = await this.api.get(`/dcim/racks/${this.id}/`);
            } catch (err) {
                this.error = err.message || 'Failed to load rack';
                // eslint-disable-next-line no-console
                console.error('Error loading rack:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.rack-detail-view {
    padding: 1rem 0;
}
</style>
