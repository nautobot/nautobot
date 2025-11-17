<template>
    <div class="location-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="location">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ location.name || location.display }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link to="/locations"
                                    >Locations</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ location.name || location.display }}
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
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Location Information">
                        <KeyValueTable :data="locationInfo" />
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
    name: 'LocationDetailView',
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
            location: null,
            loading: false,
            error: null,
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    computed: {
        locationInfo() {
            if (!this.location) return {};
            return {
                'Location Type': this.location.location_type?.display || 'N/A',
                Status: this.location.status?.value || 'N/A',
                Parent: this.location.parent?.display || 'N/A',
                Description: this.location.description || 'N/A',
            };
        },
    },
    mounted() {
        this.loadLocation();
    },
    watch: {
        id() {
            this.loadLocation();
        },
    },
    methods: {
        async loadLocation() {
            this.loading = true;
            this.error = null;

            try {
                this.location = await this.api.get(
                    `/dcim/locations/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load location';
                console.error('Error loading location:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.location-detail-view {
    padding: 1rem 0;
}
</style>
