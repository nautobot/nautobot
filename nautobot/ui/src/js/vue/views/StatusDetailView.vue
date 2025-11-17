<template>
    <div class="status-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="status">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ status.display || status.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'status-list' }"
                                    >Statuses</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ status.display || status.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'status-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Status Information">
                        <KeyValueTable :data="statusInfo" />
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
    name: 'StatusDetailView',
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
            status: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        statusInfo() {
            if (!this.status) return {};
            return {
                Name: this.status.name || 'N/A',
                'Content Types':
                    this.status.content_types &&
                    this.status.content_types.length > 0
                        ? (Array.isArray(this.status.content_types)
                              ? this.status.content_types
                              : [this.status.content_types])
                              .filter((ct) => ct != null)
                              .map((ct) => {
                                  // ContentTypeField returns strings like "app_label.model"
                                  if (typeof ct === 'string') {
                                      return ct;
                                  }
                                  // Fallback for nested objects (if API changes in future)
                                  return ct.display || ct.model || String(ct);
                              })
                              .join(', ') || 'N/A'
                        : 'N/A',
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadStatus();
    },
    methods: {
        async loadStatus() {
            this.loading = true;
            this.error = null;

            try {
                this.status = await this.api.get(
                    `/extras/statuses/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load status';
                // eslint-disable-next-line no-console
                console.error('Error loading status:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.status-detail-view {
    padding: 1rem 0;
}
</style>
