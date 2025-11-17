<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Device</h3>
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
                        <strong>Device</strong>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="name"
                                    v-model="formData.name"
                                    label="Name"
                                    type="text"
                                    placeholder="Device name (optional)"
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
                                    id="device_type"
                                    v-model="formData.device_type"
                                    label="Device Type"
                                    type="select"
                                    :options="deviceTypeOptions"
                                    :required="true"
                                    :error="errors.device_type"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="role"
                                    v-model="formData.role"
                                    label="Role"
                                    type="select"
                                    :options="roleOptions"
                                    :required="true"
                                    :error="errors.role"
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
                            <div class="col-md-12">
                                <FormField
                                    id="description"
                                    v-model="formData.description"
                                    label="Description"
                                    type="textarea"
                                    placeholder="Device description"
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
    name: 'DeviceCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                status: '',
                device_type: '',
                role: '',
                location: '',
                platform: '',
                description: '',
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            statusOptions: [],
            deviceTypeOptions: [],
            roleOptions: [],
            locationOptions: [],
            platformOptions: [],
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
                // Load statuses for Device model
                const statuses = await this.api.get('/extras/statuses/', {
                    headers: { Accept: 'application/json' },
                });
                this.statusOptions = (statuses.results || []).map((status) => ({
                    value: status.id,
                    label: status.label || status.name,
                }));

                // Load device types
                const deviceTypes = await this.api.getList(
                    '/dcim/device-types/',
                );
                this.deviceTypeOptions = (deviceTypes.results || []).map(
                    (dt) => ({
                        value: dt.id,
                        label: dt.display || dt.model,
                    }),
                );

                // Load roles for Device model
                const roles = await this.api.getList('/extras/roles/', {
                    content_types: ['dcim.device'],
                });
                this.roleOptions = (roles.results || []).map((role) => ({
                    value: role.id,
                    label: role.display || role.name,
                }));

                // Load locations that support devices
                const locations = await this.api.getList('/dcim/locations/');
                this.locationOptions = (locations.results || []).map((loc) => ({
                    value: loc.id,
                    label: loc.display || loc.name,
                }));

                // Load platforms
                const platforms = await this.api.getList('/dcim/platforms/');
                this.platformOptions = [
                    { value: '', label: '-- None --' },
                    ...(platforms.results || []).map((platform) => ({
                        value: platform.id,
                        label: platform.display || platform.name,
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
            if (!this.formData.status) {
                this.errors.status = 'Status is required';
            }
            if (!this.formData.device_type) {
                this.errors.device_type = 'Device Type is required';
            }
            if (!this.formData.role) {
                this.errors.role = 'Role is required';
            }
            if (!this.formData.location) {
                this.errors.location = 'Location is required';
            }

            if (Object.keys(this.errors).length > 0) {
                this.submitting = false;
                return;
            }

            try {
                // Prepare data for API
                const payload = {
                    name: this.formData.name || null,
                    status: this.formData.status,
                    device_type: this.formData.device_type,
                    role: this.formData.role,
                    location: this.formData.location,
                };

                if (this.formData.platform) {
                    payload.platform = this.formData.platform;
                }
                if (this.formData.description) {
                    payload.description = this.formData.description;
                }

                const device = await this.api.post('/dcim/devices/', payload);

                // Redirect to detail view
                this.$router.push({
                    name: 'device-detail',
                    params: { id: device.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create device';
                // eslint-disable-next-line no-console
                console.error('Error creating device:', err);
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
