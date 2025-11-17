<template>
    <div class="controller-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="controller">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ controller.display || controller.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'controller-list' }"
                                    >Controllers</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ controller.display || controller.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'controller-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="Controller Information">
                        <KeyValueTable :data="controllerInfo" />
                    </DetailCard>
                </div>
                <div class="col-md-6">
                    <DetailCard title="Assignment Information">
                        <KeyValueTable :data="assignmentInfo" />
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
    name: 'ControllerDetailView',
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
            controller: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        controllerInfo() {
            if (!this.controller) return {};
            return {
                Name: this.controller.name || 'N/A',
                Status: this.controller.status?.value || 'N/A',
                Location: this.controller.location?.display || 'N/A',
                Platform: this.controller.platform?.display || 'N/A',
                Role: this.controller.role?.display || 'N/A',
                Tenant: this.controller.tenant?.display || 'N/A',
            };
        },
        assignmentInfo() {
            if (!this.controller) return {};
            return {
                Description: this.controller.description || 'N/A',
                'Controller Device':
                    this.controller.controller_device?.display || 'N/A',
                'Device Redundancy Group':
                    this.controller.controller_device_redundancy_group
                        ?.display || 'N/A',
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadController();
    },
    methods: {
        async loadController() {
            this.loading = true;
            this.error = null;

            try {
                this.controller = await this.api.get(
                    `/dcim/controllers/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load controller';
                // eslint-disable-next-line no-console
                console.error('Error loading controller:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.controller-detail-view {
    padding: 1rem 0;
}
</style>
