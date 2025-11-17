<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Role</h3>
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
                        <strong>Role</strong>
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
                                    placeholder="Role name"
                                />
                            </div>
                            <div class="col-md-3">
                                <FormField
                                    id="weight"
                                    v-model="formData.weight"
                                    label="Weight"
                                    type="number"
                                    placeholder="100"
                                    help-text="Higher weights appear first in lists"
                                    :error="errors.weight"
                                />
                            </div>
                            <div class="col-md-3">
                                <FormField
                                    id="color"
                                    v-model="formData.color"
                                    label="Color"
                                    type="color"
                                    :error="errors.color"
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
                                    placeholder="Role description"
                                    :error="errors.description"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="content_types"
                                    v-model="formData.content_types"
                                    label="Content Type(s)"
                                    type="multiselect"
                                    :options="contentTypeOptions"
                                    :error="errors.content_types"
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
    name: 'RoleCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                description: '',
                weight: '',
                color: '#9e9e9e',
                content_types: [],
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            contentTypeOptions: [],
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
                const contentTypes = await this.api.getList(
                    '/extras/content-types/',
                );
                this.contentTypeOptions = (contentTypes.results || []).map(
                    (ct) => ({
                        value: `${ct.app_label}.${ct.model}`,
                        label: ct.display || ct.app_labeled_name,
                    }),
                );
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

                if (this.formData.description) {
                    payload.description = this.formData.description;
                }
                if (this.formData.weight) {
                    payload.weight = parseInt(this.formData.weight, 10);
                }
                if (this.formData.color) {
                    // Strip # prefix if present - API expects 6-character hex without #
                    payload.color = this.formData.color.replace(/^#/, '');
                }
                if (
                    this.formData.content_types &&
                    this.formData.content_types.length > 0
                ) {
                    payload.content_types = this.formData.content_types;
                }

                const role = await this.api.post('/extras/roles/', payload);

                this.$router.push({
                    name: 'role-detail',
                    params: { id: role.id },
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
                        this.submitError = errorData || 'Failed to create role';
                    }
                } else {
                    this.submitError = err.message || 'Failed to create role';
                }
                // eslint-disable-next-line no-console
                console.error('Error creating role:', err);
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
