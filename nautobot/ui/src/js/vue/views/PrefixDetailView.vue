<template>
    <div class="prefix-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="prefix">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ prefix.prefix || prefix.display }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link to="/prefixes"
                                    >Prefixes</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ prefix.prefix || prefix.display }}
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
                    <DetailCard title="Prefix Information">
                        <KeyValueTable :data="prefixInfo" />
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
    name: 'PrefixDetailView',
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
            prefix: null,
            loading: false,
            error: null,
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    computed: {
        prefixInfo() {
            if (!this.prefix) return {};
            return {
                Prefix: this.prefix.prefix || 'N/A',
                VRF: this.prefix.vrf?.display || 'Global',
                Status: this.prefix.status?.value || 'N/A',
                Role: this.prefix.role?.display || 'N/A',
                Description: this.prefix.description || 'N/A',
            };
        },
    },
    mounted() {
        this.loadPrefix();
    },
    watch: {
        id() {
            this.loadPrefix();
        },
    },
    methods: {
        async loadPrefix() {
            this.loading = true;
            this.error = null;

            try {
                this.prefix = await this.api.get(`/ipam/prefixes/${this.id}/`);
            } catch (err) {
                this.error = err.message || 'Failed to load prefix';
                console.error('Error loading prefix:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.prefix-detail-view {
    padding: 1rem 0;
}
</style>
