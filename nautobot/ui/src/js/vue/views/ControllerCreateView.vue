<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Controller</h3>
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
                        <strong>Controller</strong>
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
                                    placeholder="Controller name"
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
                                    id="location"
                                    v-model="formData.location"
                                    label="Location"
                                    type="select"
                                    :options="locationOptions"
                                    :required="true"
                                    :error="errors.location"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="platform"
                                    v-model="formData.platform"
                                    label="Platform"
                                    type="select"
                                    :options="platformOptions"
                                    :error="errors.platform"
                                />
                            </div>
                        </div>

                        <div class="row">
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
                            <div class="col-md-6">
                                <FormField
                                    id="controller_device"
                                    v-model="formData.controller_device"
                                    label="Controller Device"
                                    type="select"
                                    :options="deviceOptions"
                                    help-text="Cannot assign both a device and a device redundancy group"
                                    :error="errors.controller_device"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="controller_device_redundancy_group"
                                    v-model="
                                        formData.controller_device_redundancy_group
                                    "
                                    label="Device Redundancy Group"
                                    type="select"
                                    :options="deviceRedundancyGroupOptions"
                                    help-text="Cannot assign both a device and a device redundancy group"
                                    :error="
                                        errors.controller_device_redundancy_group
                                    "
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="external_integration"
                                    v-model="formData.external_integration"
                                    label="External Integration"
                                    type="select"
                                    :options="externalIntegrationOptions"
                                    :error="errors.external_integration"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="capabilities"
                                    v-model="formData.capabilities"
                                    label="Capabilities"
                                    type="multiselect"
                                    :options="capabilityOptions"
                                    :error="errors.capabilities"
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
                                    placeholder="Controller description"
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
    name: 'ControllerCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                status: '',
                location: '',
                platform: '',
                role: '',
                tenant: '',
                controller_device: '',
                controller_device_redundancy_group: '',
                external_integration: '',
                capabilities: [],
                description: '',
                tags: [],
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            statusOptions: [],
            locationOptions: [],
            platformOptions: [],
            roleOptions: [],
            tenantOptions: [],
            deviceOptions: [],
            deviceRedundancyGroupOptions: [],
            externalIntegrationOptions: [],
            capabilityOptions: [{ value: 'wireless', label: 'Wireless' }],
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

                const locations = await this.api.getList('/dcim/locations/');
                this.locationOptions = (locations.results || []).map((loc) => ({
                    value: loc.id,
                    label: loc.display || loc.name,
                }));

                const platforms = await this.api.getList('/dcim/platforms/');
                this.platformOptions = [
                    { value: '', label: '-- None --' },
                    ...(platforms.results || []).map((platform) => ({
                        value: platform.id,
                        label: platform.display || platform.name,
                    })),
                ];

                const roles = await this.api.getList('/extras/roles/', {
                    content_types: ['dcim.controller'],
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

                const devices = await this.api.getList('/dcim/devices/');
                this.deviceOptions = [
                    { value: '', label: '-- None --' },
                    ...(devices.results || []).map((device) => ({
                        value: device.id,
                        label: device.display || device.name,
                    })),
                ];

                const deviceRedundancyGroups = await this.api.getList(
                    '/dcim/device-redundancy-groups/',
                );
                this.deviceRedundancyGroupOptions = [
                    { value: '', label: '-- None --' },
                    ...(deviceRedundancyGroups.results || []).map((drg) => ({
                        value: drg.id,
                        label: drg.display || drg.name,
                    })),
                ];

                const externalIntegrations = await this.api.getList(
                    '/extras/external-integrations/',
                );
                this.externalIntegrationOptions = [
                    { value: '', label: '-- None --' },
                    ...(externalIntegrations.results || []).map((ei) => ({
                        value: ei.id,
                        label: ei.display || ei.name,
                    })),
                ];

                const tags = await this.api.getList('/extras/tags/', {
                    content_types: 'dcim.controller',
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
            }
            if (!this.formData.status) {
                this.errors.status = 'Status is required';
            }
            if (!this.formData.location) {
                this.errors.location = 'Location is required';
            }

            if (
                this.formData.controller_device &&
                this.formData.controller_device_redundancy_group
            ) {
                this.submitError =
                    'Cannot assign both a device and a device redundancy group';
                this.submitting = false;
                return;
            }

            if (Object.keys(this.errors).length > 0) {
                this.submitting = false;
                return;
            }

            try {
                const payload = {
                    name: this.formData.name,
                    status: this.formData.status,
                    location: this.formData.location,
                };

                if (this.formData.platform) {
                    payload.platform = this.formData.platform;
                }
                if (this.formData.role) {
                    payload.role = this.formData.role;
                }
                if (this.formData.tenant) {
                    payload.tenant = this.formData.tenant;
                }
                if (this.formData.controller_device) {
                    payload.controller_device = this.formData.controller_device;
                }
                if (this.formData.controller_device_redundancy_group) {
                    payload.controller_device_redundancy_group =
                        this.formData.controller_device_redundancy_group;
                }
                if (this.formData.description) {
                    payload.description = this.formData.description;
                }
                if (this.formData.external_integration) {
                    payload.external_integration =
                        this.formData.external_integration;
                }
                if (
                    this.formData.capabilities &&
                    this.formData.capabilities.length > 0
                ) {
                    payload.capabilities = this.formData.capabilities;
                }
                if (this.formData.tags && this.formData.tags.length > 0) {
                    payload.tags = this.formData.tags;
                }

                const controller = await this.api.post(
                    '/dcim/controllers/',
                    payload,
                );

                this.$router.push({
                    name: 'controller-detail',
                    params: { id: controller.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create controller';
                // eslint-disable-next-line no-console
                console.error('Error creating controller:', err);
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
