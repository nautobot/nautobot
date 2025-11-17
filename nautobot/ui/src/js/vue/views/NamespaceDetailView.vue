<template>
    <div class="namespace-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="namespace">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ namespace.display || namespace.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'namespace-list' }"
                                    >Namespaces</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ namespace.display || namespace.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'namespace-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Namespace Information">
                        <KeyValueTable :data="namespaceInfo" />
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
    name: 'NamespaceDetailView',
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
            namespace: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        namespaceInfo() {
            if (!this.namespace) return {};
            return {
                Name: this.namespace.name || 'N/A',
                Location: this.namespace.location?.display || 'N/A',
                Description: this.namespace.description || 'N/A',
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadNamespace();
    },
    methods: {
        async loadNamespace() {
            this.loading = true;
            this.error = null;

            try {
                this.namespace = await this.api.get(
                    `/ipam/namespaces/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load namespace';
                // eslint-disable-next-line no-console
                console.error('Error loading namespace:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.namespace-detail-view {
    padding: 1rem 0;
}
</style>
