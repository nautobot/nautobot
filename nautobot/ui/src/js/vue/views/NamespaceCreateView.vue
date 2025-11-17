<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Namespace</h3>
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
                        <strong>Namespace</strong>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="name"
                                    v-model="formData.name"
                                    label="Name"
                                    type="text"
                                    :required="true"
                                    :error="errors.name"
                                    placeholder="Namespace name"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="location"
                                    v-model="formData.location"
                                    label="Location"
                                    type="select"
                                    :options="locationOptions"
                                    :error="errors.location"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="tenant"
                                    v-model="formData.tenant"
                                    label="Tenant"
                                    type="select"
                                    :options="tenantOptions"
                                    :error="errors.tenant"
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
                                    placeholder="Namespace description"
                                    :error="errors.description"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="tags"
                                    v-model="formData.tags"
                                    label="Tags"
                                    type="multiselect"
                                    :options="tagOptions"
                                    :error="errors.tags"
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
    name: 'NamespaceCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                location: '',
                tenant: '',
                description: '',
                tags: [],
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            locationOptions: [],
            tenantOptions: [],
            tagOptions: [],
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
                const locations = await this.api.getList('/dcim/locations/');
                this.locationOptions = [
                    { value: '', label: '-- None --' },
                    ...(locations.results || []).map((loc) => ({
                        value: loc.id,
                        label: loc.display || loc.name,
                    })),
                ];

                const tenants = await this.api.getList('/tenancy/tenants/');
                this.tenantOptions = [
                    { value: '', label: '-- None --' },
                    ...(tenants.results || []).map((tenant) => ({
                        value: tenant.id,
                        label: tenant.display || tenant.name,
                    })),
                ];

                const tags = await this.api.getList('/extras/tags/', {
                    content_types: 'ipam.namespace',
                });
                this.tagOptions = (tags.results || []).map((tag) => ({
                    value: tag.id,
                    label: tag.display || tag.name,
                }));
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

            if (!this.formData.name) {
                this.errors.name = 'Name is required';
                this.submitting = false;
                return;
            }

            try {
                const payload = {
                    name: this.formData.name,
                };

                if (this.formData.location) {
                    payload.location = this.formData.location;
                }
                if (this.formData.description) {
                    payload.description = this.formData.description;
                }
                if (this.formData.tenant) {
                    payload.tenant = this.formData.tenant;
                }
                if (this.formData.tags && this.formData.tags.length > 0) {
                    payload.tags = this.formData.tags;
                }

                const namespace = await this.api.post(
                    '/ipam/namespaces/',
                    payload,
                );

                this.$router.push({
                    name: 'namespace-detail',
                    params: { id: namespace.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create namespace';
                // eslint-disable-next-line no-console
                console.error('Error creating namespace:', err);
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
