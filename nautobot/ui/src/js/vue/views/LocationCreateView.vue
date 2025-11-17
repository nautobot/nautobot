<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Location</h3>
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
                        <strong>Location</strong>
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
                                    id="location_type"
                                    v-model="formData.location_type"
                                    label="Location Type"
                                    type="select"
                                    :options="locationTypeOptions"
                                    :required="true"
                                    :error="errors.location_type"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="parent"
                                    v-model="formData.parent"
                                    label="Parent Location"
                                    type="select"
                                    :options="parentOptions"
                                    :error="errors.parent"
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
                                    placeholder="Location description"
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
    name: 'LocationCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                status: '',
                location_type: '',
                parent: '',
                description: '',
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            statusOptions: [],
            locationTypeOptions: [],
            parentOptions: [],
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
                // Load statuses for Location model
                const statuses = await this.api.getList('/extras/statuses/', {
                    content_types: 'dcim.location',
                });
                this.statusOptions = (statuses.results || []).map((status) => ({
                    value: status.id,
                    label: status.label || status.name,
                }));

                // Load location types
                const locationTypes = await this.api.getList(
                    '/dcim/location-types/',
                );
                this.locationTypeOptions = (locationTypes.results || []).map(
                    (lt) => ({
                        value: lt.id,
                        label: lt.display || lt.name,
                    }),
                );

                // Load parent locations
                const locations = await this.api.getList('/dcim/locations/');
                this.parentOptions = [
                    { value: '', label: '-- None (Top Level) --' },
                    ...(locations.results || []).map((loc) => ({
                        value: loc.id,
                        label: loc.display || loc.name,
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
            if (!this.formData.name) {
                this.errors.name = 'Name is required';
            }
            if (!this.formData.status) {
                this.errors.status = 'Status is required';
            }
            if (!this.formData.location_type) {
                this.errors.location_type = 'Location Type is required';
            }

            if (Object.keys(this.errors).length > 0) {
                this.submitting = false;
                return;
            }

            try {
                const payload = {
                    name: this.formData.name,
                    status: this.formData.status,
                    location_type: this.formData.location_type,
                };

                if (this.formData.parent) {
                    payload.parent = this.formData.parent;
                } else {
                    payload.parent = null;
                }
                if (this.formData.description) {
                    payload.description = this.formData.description;
                }

                const location = await this.api.post(
                    '/dcim/locations/',
                    payload,
                );

                // Redirect to detail view
                this.$router.push({
                    name: 'location-detail',
                    params: { id: location.id },
                });
            } catch (err) {
                if (err.response && err.response.data) {
                    // Handle validation errors from the API
                    const errorData = err.response.data;
                    if (typeof errorData === 'object') {
                        // Set field-specific errors
                        Object.keys(errorData).forEach((field) => {
                            if (Array.isArray(errorData[field])) {
                                this.errors[field] =
                                    errorData[field].join(', ');
                            } else if (typeof errorData[field] === 'object') {
                                // Handle nested objects (like non_field_errors)
                                this.errors[field] = JSON.stringify(
                                    errorData[field],
                                );
                            } else {
                                this.errors[field] = errorData[field];
                            }
                        });
                        // Set general error message
                        const errorMessages = Object.values(errorData)
                            .flat()
                            .filter((msg) => typeof msg === 'string');
                        this.submitError =
                            errorMessages.length > 0
                                ? errorMessages.join('; ')
                                : 'Validation failed. Please check the form fields.';
                    } else {
                        this.submitError =
                            errorData || 'Failed to create location';
                    }
                } else {
                    this.submitError =
                        err.message || 'Failed to create location';
                }
                // eslint-disable-next-line no-console
                console.error('Error creating location:', err);
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
