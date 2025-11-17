<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new {{ config.singularTitle }}</h3>
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
                        <strong>{{ config.singularTitle }}</strong>
                    </div>
                    <div class="card-body">
                        <div
                            v-for="field in config.createFields"
                            :key="field.id"
                            class="row"
                        >
                            <div :class="field.colClass || 'col-md-12'">
                                <FormField
                                    :id="field.id"
                                    v-model="formData[field.id]"
                                    :label="field.label"
                                    :type="field.type"
                                    :required="field.required"
                                    :placeholder="field.placeholder"
                                    :help-text="field.helpText"
                                    :options="fieldOptions[field.id] || []"
                                    :error="errors[field.id]"
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
import { inject, computed } from 'vue';
import { useRoute } from 'vue-router';
import FormField from '../components/FormField.vue';
import { getViewConfig } from '../config/viewConfig.js';

export default {
    name: 'GenericCreateView',
    components: {
        FormField,
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
            formData: {},
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            fieldOptions: {},
        };
    },
    async mounted() {
        // Initialize form data first to ensure all fields exist
        this.initializeFormData();
        // Then load any dynamic options
        await this.loadFormData();
    },
    watch: {
        '$route.name'() {
            this.initializeFormData();
            this.loadFormData();
        },
    },
    methods: {
        initializeFormData() {
            // Initialize form data with default values from field config
            if (!this.config || !this.config.createFields) {
                return;
            }
            
            const formData = { ...this.formData };
            this.config.createFields.forEach((field) => {
                if (formData[field.id] === undefined) {
                    if (field.type === 'multiselect') {
                        formData[field.id] = [];
                    } else if (field.type === 'color') {
                        formData[field.id] = field.defaultValue || '#9e9e9e';
                    } else if (field.type === 'number') {
                        formData[field.id] = field.defaultValue !== undefined ? field.defaultValue : '';
                    } else if (field.type === 'checkbox') {
                        formData[field.id] = field.defaultValue !== undefined ? field.defaultValue : false;
                    } else {
                        formData[field.id] = field.defaultValue !== undefined ? field.defaultValue : '';
                    }
                }
            });
            this.formData = formData;
        },
        async loadFormData() {
            this.loading = true;
            this.fieldOptions = {};
            
            try {
                // Load options for fields that need them
                for (const field of this.config.createFields) {
                    if (field.optionsEndpoint) {
                        try {
                            const options = await this.api.getList(
                                field.optionsEndpoint,
                                field.optionsParams || {},
                            );
                            this.fieldOptions[field.id] = (options.results || []).map(
                                field.optionsMapper || ((item) => ({
                                    value: item.id,
                                    label: item.display || item.name,
                                })),
                            );
                        } catch (err) {
                            // eslint-disable-next-line no-console
                            console.error(`Error loading options for ${field.id}:`, err);
                        }
                    }
                }
            } catch (err) {
                this.submitError = `Failed to load form data: ${err.message}`;
                // eslint-disable-next-line no-console
                console.error('Error loading form data:', err);
            } finally {
                this.loading = false;
            }
        },
        validateForm() {
            this.errors = {};
            let isValid = true;

            for (const field of this.config.createFields) {
                if (field.required) {
                    const value = this.formData[field.id];
                    if (
                        !value ||
                        (Array.isArray(value) && value.length === 0) ||
                        (typeof value === 'string' && value.trim() === '')
                    ) {
                        this.errors[field.id] = `${field.label} is required`;
                        isValid = false;
                    }
                }
            }

            return isValid;
        },
        async handleSubmit() {
            this.submitting = true;
            this.submitError = null;
            this.errors = {};

            if (!this.validateForm()) {
                this.submitting = false;
                return;
            }

            try {
                const payload = this.config.createPayloadMapper
                    ? this.config.createPayloadMapper(this.formData)
                    : this.formData;

                const item = await this.api.post(
                    this.config.apiEndpoint,
                    payload,
                );

                this.$router.push({
                    name: this.config.detailRoute,
                    params: { id: item.id },
                });
            } catch (err) {
                if (err.response && err.response.data) {
                    const errorData = err.response.data;
                    if (typeof errorData === 'object') {
                        Object.keys(errorData).forEach((field) => {
                            if (Array.isArray(errorData[field])) {
                                this.errors[field] = errorData[field].join(', ');
                            } else if (typeof errorData[field] === 'object') {
                                this.errors[field] = JSON.stringify(errorData[field]);
                            } else {
                                this.errors[field] = errorData[field];
                            }
                        });
                        const errorMessages = Object.values(errorData)
                            .flat()
                            .filter((msg) => typeof msg === 'string');
                        this.submitError =
                            errorMessages.length > 0
                                ? errorMessages.join('; ')
                                : 'Validation failed. Please check the form fields.';
                    } else {
                        this.submitError = errorData || `Failed to create ${this.config.singularTitle.toLowerCase()}`;
                    }
                } else {
                    this.submitError = err.message || `Failed to create ${this.config.singularTitle.toLowerCase()}`;
                }
                // eslint-disable-next-line no-console
                console.error(`Error creating ${this.config.singularTitle.toLowerCase()}:`, err);
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

