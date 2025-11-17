<template>
    <div class="generic-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="item">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ item.display || item.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: config.listRoute }">
                                    {{ config.title }}
                                </router-link>
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ item.display || item.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: config.listRoute }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard :title="`${config.singularTitle} Information`">
                        <KeyValueTable :data="itemInfo" />
                    </DetailCard>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { inject, computed } from 'vue';
import { useRoute } from 'vue-router';
import DetailCard from '../components/DetailCard.vue';
import KeyValueTable from '../components/KeyValueTable.vue';
import { getViewConfig } from '../config/viewConfig.js';

export default {
    name: 'GenericDetailView',
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
    setup() {
        const api = inject('api');
        const route = useRoute();
        // Get config from route name
        const config = computed(() => getViewConfig(route.name || ''));
        
        return { api, config };
    },
    data() {
        return {
            item: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        itemInfo() {
            if (!this.item) return {};
            return this.config.detailFields(this.item);
        },
    },
    mounted() {
        this.loadItem();
    },
    watch: {
        // Reload when route changes
        '$route.params.id'() {
            this.loadItem();
        },
        '$route.name'() {
            this.loadItem();
        },
    },
    methods: {
        async loadItem() {
            this.loading = true;
            this.error = null;

            try {
                this.item = await this.api.get(
                    `${this.config.apiEndpoint}${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || `Failed to load ${this.config.singularTitle.toLowerCase()}`;
                // eslint-disable-next-line no-console
                console.error(`Error loading ${this.config.singularTitle.toLowerCase()}:`, err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.generic-detail-view {
    padding: 1rem 0;
}
</style>

