<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Prefix</h3>
            </div>
            <div class="col-lg-8 col-md-10">
                <div v-if="submitError" class="card border-danger mb-3">
                    <div
                        class="card-header bg-danger-subtle border-danger text-body"
                    >
                        <strong>Errors</strong>
                    </div>
                    <div class="card-body">
                        {{ submitError }}
                    </div>
                </div>

                <div v-if="loading" class="text-center py-5">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>

                <div v-else class="card">
                    <div class="card-header">
                        <strong>Prefix</strong>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="prefix"
                                    v-model="formData.prefix"
                                    label="Prefix"
                                    type="text"
                                    placeholder="192.168.1.0/24"
                                    :required="true"
                                    :error="errors.prefix"
                                    help-text="Enter IP prefix in CIDR notation (e.g., 192.168.1.0/24)"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="status"
                                    v-model="formData.status"
                                    label="Status"
                                    type="select"
                                    :options="statusOptions"
                                    :required="true"
                                    :error="errors.status"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="namespace"
                                    v-model="formData.namespace"
                                    label="Namespace"
                                    type="select"
                                    :options="namespaceOptions"
                                    :error="errors.namespace"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="role"
                                    v-model="formData.role"
                                    label="Role"
                                    type="select"
                                    :options="roleOptions"
                                    :error="errors.role"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="description"
                                    v-model="formData.description"
                                    label="Description"
                                    type="textarea"
                                    placeholder="Prefix description"
                                    :error="errors.description"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="nb-form-sticky-footer">
            <button
                type="submit"
                name="_create"
                class="btn btn-primary"
                :disabled="submitting"
            >
                <span aria-hidden="true" class="mdi mdi-check me-4"></span>
                {{ submitting ? 'Creating...' : 'Create' }}
            </button>
            <button
                type="button"
                class="btn btn-secondary"
                @click="$router.back()"
            >
                <span aria-hidden="true" class="mdi mdi-close me-4"></span>
                Cancel
            </button>
        </div>
    </form>
</template>

<script>
import { inject } from 'vue';
import FormField from '../components/FormField.vue';

export default {
    name: 'PrefixCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                prefix: '',
                status: '',
                namespace: '',
                role: '',
                description: '',
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            statusOptions: [],
            namespaceOptions: [],
            roleOptions: [],
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    async mounted() {
        await this.loadFormData();
    },
    methods: {
        async loadFormData() {
            this.loading = true;
            try {
                // Load statuses for Prefix model
                const statuses = await this.api.get('/extras/statuses/');
                this.statusOptions = (statuses.results || []).map((status) => ({
                    value: status.id,
                    label: status.label || status.name,
                }));

                // Load namespaces (default namespace will be used if not specified)
                const namespaces = await this.api.getList('/ipam/namespaces/');
                this.namespaceOptions = [
                    { value: '', label: '-- Use Default --' },
                    ...(namespaces.results || []).map((ns) => ({
                        value: ns.id,
                        label: ns.display || ns.name,
                    })),
                ];

                // Load roles for Prefix model
                const roles = await this.api.getList('/extras/roles/', {
                    content_types: ['ipam.prefix'],
                });
                this.roleOptions = [
                    { value: '', label: '-- None --' },
                    ...(roles.results || []).map((role) => ({
                        value: role.id,
                        label: role.display || role.name,
                    })),
                ];
            } catch (err) {
                this.submitError = `Failed to load form data: ${err.message}`;
                // eslint-disable-next-line no-console
                console.error('Error loading form data:', err);
            } finally {
                this.loading = false;
            }
        },
        async handleSubmit() {
            this.submitting = true;
            this.submitError = null;
            this.errors = {};

            // Validate required fields
            if (!this.formData.prefix) {
                this.errors.prefix = 'Prefix is required';
            }
            if (!this.formData.status) {
                this.errors.status = 'Status is required';
            }

            if (Object.keys(this.errors).length > 0) {
                this.submitting = false;
                return;
            }

            try {
                const payload = {
                    prefix: this.formData.prefix,
                    status: this.formData.status,
                };

                if (this.formData.namespace) {
                    payload.namespace = this.formData.namespace;
                }
                if (this.formData.role) {
                    payload.role = this.formData.role;
                }
                if (this.formData.description) {
                    payload.description = this.formData.description;
                }

                const prefix = await this.api.post('/ipam/prefixes/', payload);

                // Redirect to detail view
                this.$router.push({
                    name: 'prefix-detail',
                    params: { id: prefix.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create prefix';
                // eslint-disable-next-line no-console
                console.error('Error creating prefix:', err);
            } finally {
                this.submitting = false;
            }
        },
    },
};
</script>

<style scoped>
#nb-create-form {
    display: flex;
    flex-direction: column;
    min-height: 100%;
}

#nb-create-form .row {
    flex: 1;
}
</style>
