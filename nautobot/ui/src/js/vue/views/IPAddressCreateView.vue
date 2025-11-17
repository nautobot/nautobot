<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new IP Address</h3>
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
                        <strong>IP Address</strong>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="address"
                                    v-model="formData.address"
                                    label="IP Address"
                                    type="text"
                                    :required="true"
                                    :error="errors.address"
                                    placeholder="192.168.1.1/24 or 2001:db8::1/64"
                                    help-text="Enter IP address with CIDR notation (e.g., 192.168.1.1/24)"
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
                            <div class="col-md-6">
                                <FormField
                                    id="dns_name"
                                    v-model="formData.dns_name"
                                    label="DNS Name"
                                    type="text"
                                    placeholder="hostname.example.com"
                                    :error="errors.dns_name"
                                />
                            </div>
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
                                    placeholder="IP address description"
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
    name: 'IPAddressCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                address: '',
                status: '',
                namespace: '',
                role: '',
                tenant: '',
                dns_name: '',
                description: '',
                tags: [],
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            statusOptions: [],
            namespaceOptions: [],
            roleOptions: [],
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
                const statuses = await this.api.get('/extras/statuses/');
                this.statusOptions = (statuses.results || []).map((status) => ({
                    value: status.id,
                    label: status.label || status.name,
                }));

                const namespaces = await this.api.getList('/ipam/namespaces/');
                this.namespaceOptions = [
                    { value: '', label: '-- Use Default --' },
                    ...(namespaces.results || []).map((ns) => ({
                        value: ns.id,
                        label: ns.display || ns.name,
                    })),
                ];

                const roles = await this.api.getList('/extras/roles/', {
                    content_types: ['ipam.ipaddress'],
                });
                this.roleOptions = [
                    { value: '', label: '-- None --' },
                    ...(roles.results || []).map((role) => ({
                        value: role.id,
                        label: role.display || role.name,
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
                    content_types: 'ipam.ipaddress',
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

            if (!this.formData.address) {
                this.errors.address = 'IP Address is required';
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
                    address: this.formData.address,
                    status: this.formData.status,
                };

                if (this.formData.namespace) {
                    payload.namespace = this.formData.namespace;
                }
                if (this.formData.role) {
                    payload.role = this.formData.role;
                }
                if (this.formData.dns_name) {
                    payload.dns_name = this.formData.dns_name;
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

                const ipAddress = await this.api.post(
                    '/ipam/ip-addresses/',
                    payload,
                );

                this.$router.push({
                    name: 'ip-address-detail',
                    params: { id: ipAddress.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create IP address';
                // eslint-disable-next-line no-console
                console.error('Error creating IP address:', err);
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
