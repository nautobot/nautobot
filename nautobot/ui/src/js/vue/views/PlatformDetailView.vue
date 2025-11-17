<template>
    <div class="platform-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="platform">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ platform.display || platform.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'platform-list' }"
                                    >Platforms</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ platform.display || platform.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'platform-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Platform Information">
                        <KeyValueTable :data="platformInfo" />
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
    name: 'PlatformDetailView',
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
            platform: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        platformInfo() {
            if (!this.platform) return {};
            return {
                Name: this.platform.name || 'N/A',
                Manufacturer: this.platform.manufacturer?.display || 'N/A',
                'Network Driver': this.platform.network_driver || 'N/A',
                'NAPALM Driver': this.platform.napalm_driver || 'N/A',
                Description: this.platform.description || 'N/A',
                'Device Count': this.platform.device_count || 0,
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadPlatform();
    },
    methods: {
        async loadPlatform() {
            this.loading = true;
            this.error = null;

            try {
                this.platform = await this.api.get(
                    `/dcim/platforms/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load platform';
                // eslint-disable-next-line no-console
                console.error('Error loading platform:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.platform-detail-view {
    padding: 1rem 0;
}
</style>
