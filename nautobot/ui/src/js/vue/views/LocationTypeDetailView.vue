<template>
    <div class="location-type-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="locationType">
            <div class="card mb-4">
                <div class="card-header">
                    <strong>Location Type</strong>
                </div>
                <div class="card-body">
                    <KeyValueTable :data="locationTypeInfo" />
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
    name: 'LocationTypeDetailView',
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
            locationType: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        locationTypeInfo() {
            if (!this.locationType) return {};
            return {
                Name: this.locationType.name || 'N/A',
                Description: this.locationType.description || 'N/A',
                Nestable: this.locationType.nestable ? 'Yes' : 'No',
                'Location Count': this.locationType.location_count || 0,
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadLocationType();
    },
    methods: {
        async loadLocationType() {
            this.loading = true;
            this.error = null;

            try {
                this.locationType = await this.api.get(
                    `/dcim/location-types/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load location type';
                // eslint-disable-next-line no-console
                console.error('Error loading location type:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.location-type-detail-view {
    padding: 1rem 0;
}
</style>
