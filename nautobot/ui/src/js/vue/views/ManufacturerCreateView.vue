<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Manufacturer</h3>
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

                <div class="card">
                    <div class="card-header">
                        <strong>Manufacturer</strong>
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
                                    placeholder="e.g., Cisco, Dell, Juniper"
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
                                    placeholder="Manufacturer description"
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
    name: 'ManufacturerCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                description: '',
            },
            errors: {},
            submitError: null,
            submitting: false,
        };
    },
    setup() {
        const api = inject('api');
        return { api };
    },
    methods: {
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

                const manufacturer = await this.api.post(
                    '/dcim/manufacturers/',
                    payload,
                );

                this.$router.push({
                    name: 'manufacturer-detail',
                    params: { id: manufacturer.id },
                });
            } catch (err) {
                this.submitError =
                    err.message || 'Failed to create manufacturer';
                // eslint-disable-next-line no-console
                console.error('Error creating manufacturer:', err);
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
