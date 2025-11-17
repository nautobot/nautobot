<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Platform</h3>
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
                        <strong>Platform</strong>
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
                                    placeholder="e.g., Cisco IOS-XR, Juniper Junos"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="manufacturer"
                                    v-model="formData.manufacturer"
                                    label="Manufacturer"
                                    type="select"
                                    :options="manufacturerOptions"
                                    :error="errors.manufacturer"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="network_driver"
                                    v-model="formData.network_driver"
                                    label="Network Driver"
                                    type="text"
                                    placeholder="e.g., cisco_ios, arista_eos"
                                    help-text="Normalized network driver name"
                                    :error="errors.network_driver"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="napalm_driver"
                                    v-model="formData.napalm_driver"
                                    label="NAPALM Driver"
                                    type="text"
                                    placeholder="e.g., ios, eos, junos"
                                    :error="errors.napalm_driver"
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
                                    placeholder="Platform description"
                                    :error="errors.description"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="napalm_args"
                                    v-model="formData.napalm_args"
                                    label="NAPALM Arguments"
                                    type="textarea"
                                    placeholder='{"optional_args": {"port": 22}}'
                                    help-text="Enter NAPALM arguments in JSON format"
                                    :error="errors.napalm_args"
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
    name: 'PlatformCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                manufacturer: '',
                network_driver: '',
                napalm_driver: '',
                description: '',
                napalm_args: '',
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            manufacturerOptions: [],
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
                const manufacturers = await this.api.getList(
                    '/dcim/manufacturers/',
                );
                this.manufacturerOptions = [
                    { value: '', label: '-- None --' },
                    ...(manufacturers.results || []).map((m) => ({
                        value: m.id,
                        label: m.display || m.name,
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

            if (!this.formData.name) {
                this.errors.name = 'Name is required';
                this.submitting = false;
                return;
            }

            try {
                const payload = {
                    name: this.formData.name,
                };

                if (this.formData.manufacturer) {
                    payload.manufacturer = this.formData.manufacturer;
                }
                if (this.formData.network_driver) {
                    payload.network_driver = this.formData.network_driver;
                }
                if (this.formData.napalm_driver) {
                    payload.napalm_driver = this.formData.napalm_driver;
                }
                if (this.formData.description) {
                    payload.description = this.formData.description;
                }
                if (this.formData.napalm_args) {
                    try {
                        payload.napalm_args = JSON.parse(
                            this.formData.napalm_args,
                        );
                    } catch (e) {
                        this.errors.napalm_args = 'Invalid JSON format';
                        this.submitting = false;
                        return;
                    }
                }

                const platform = await this.api.post(
                    '/dcim/platforms/',
                    payload,
                );

                this.$router.push({
                    name: 'platform-detail',
                    params: { id: platform.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create platform';
                // eslint-disable-next-line no-console
                console.error('Error creating platform:', err);
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
