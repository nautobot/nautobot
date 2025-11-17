<template>
    <div class="vlan-group-detail-view">
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div v-else-if="error" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ error }}
        </div>

        <div v-else-if="vlanGroup">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1>{{ vlanGroup.display || vlanGroup.name }}</h1>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item">
                                <router-link :to="{ name: 'vlan-group-list' }"
                                    >VLAN Groups</router-link
                                >
                            </li>
                            <li
                                class="breadcrumb-item active"
                                aria-current="page"
                            >
                                {{ vlanGroup.display || vlanGroup.name }}
                            </li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <router-link
                        :to="{ name: 'vlan-group-list' }"
                        class="btn btn-secondary"
                    >
                        <i class="mdi mdi-arrow-left"></i> Back to List
                    </router-link>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <DetailCard title="VLAN Group Information">
                        <KeyValueTable :data="vlanGroupInfo" />
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
    name: 'VLANGroupDetailView',
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
            vlanGroup: null,
            loading: false,
            error: null,
        };
    },
    computed: {
        vlanGroupInfo() {
            if (!this.vlanGroup) return {};
            return {
                Name: this.vlanGroup.name || 'N/A',
                Location: this.vlanGroup.location?.display || 'N/A',
                'VLAN Range': this.vlanGroup.range || 'N/A',
                Description: this.vlanGroup.description || 'N/A',
                'VLAN Count': this.vlanGroup.vlan_count || 0,
            };
        },
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    mounted() {
        this.loadVLANGroup();
    },
    methods: {
        async loadVLANGroup() {
            this.loading = true;
            this.error = null;

            try {
                this.vlanGroup = await this.api.get(
                    `/ipam/vlan-groups/${this.id}/`,
                );
            } catch (err) {
                this.error = err.message || 'Failed to load VLAN group';
                // eslint-disable-next-line no-console
                console.error('Error loading VLAN group:', err);
            } finally {
                this.loading = false;
            }
        },
    },
};
</script>

<style scoped>
.vlan-group-detail-view {
    padding: 1rem 0;
}
</style>
