<template>
    <div class="manufacturer-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="manufacturer">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ manufacturer.display || manufacturer.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'manufacturer-list' }"
                                    >Manufacturers</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ manufacturer.display || manufacturer.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'manufacturer-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Manufacturer Information">
                        <KeyValueTable :data="manufacturerInfo" />
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
    name: 'ManufacturerDetailView',
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
            manufacturer: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        manufacturerInfo() {
            if (!this.manufacturer) return {};
            return {
                Name: this.manufacturer.name || 'N/A',
                Description: this.manufacturer.description || 'N/A',
                'Device Type Count': this.manufacturer.device_type_count || 0,
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadManufacturer();
    },
    methods: {
        async loadManufacturer() {
            this.loading = true;
            this.error = null;

            try {
                this.manufacturer = await this.api.get(
                    `/dcim/manufacturers/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load manufacturer';
                // eslint-disable-next-line no-console
                console.error('Error loading manufacturer:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.manufacturer-detail-view {
    padding: 1rem 0;
}
</style>
