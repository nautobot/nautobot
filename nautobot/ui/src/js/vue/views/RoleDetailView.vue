<template>
    <div class="role-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="role">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ role.display || role.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'role-list' }"
                                    >Roles</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ role.display || role.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'role-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Role Information">
                        <KeyValueTable :data="roleInfo" />
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
    name: 'RoleDetailView',
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
            role: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        roleInfo() {
            if (!this.role) return {};
            return {
                Name: this.role.name || 'N/A',
                Description: this.role.description || 'N/A',
                'Content Types':
                    this.role.content_types &&
                    this.role.content_types.length > 0
                        ? (Array.isArray(this.role.content_types)
                              ? this.role.content_types
                              : [this.role.content_types])
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
        this.loadRole();
    },
    methods: {
        async loadRole() {
            this.loading = true;
            this.error = null;

            try {
                this.role = await this.api.get(`/extras/roles/${this.id}/`);
            } catch (err) {
                this.error = err.message || 'Failed to load role';
                // eslint-disable-next-line no-console
                console.error('Error loading role:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.role-detail-view {
    padding: 1rem 0;
}
</style>
