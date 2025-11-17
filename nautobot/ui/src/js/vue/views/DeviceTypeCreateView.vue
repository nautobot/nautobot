<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Device Type</h3>
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
                        <strong>Device Type</strong>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="manufacturer"
                                    v-model="formData.manufacturer"
                                    label="Manufacturer"
                                    type="select"
                                    :options="manufacturerOptions"
                                    :required="true"
                                    :error="errors.manufacturer"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="model"
                                    v-model="formData.model"
                                    label="Model"
                                    type="text"
                                    :required="true"
                                    :error="errors.model"
                                    placeholder="Device model name"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="device_family"
                                    v-model="formData.device_family"
                                    label="Device Family"
                                    type="select"
                                    :options="deviceFamilyOptions"
                                    :error="errors.device_family"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="part_number"
                                    v-model="formData.part_number"
                                    label="Part Number"
                                    type="text"
                                    placeholder="Discrete part number (optional)"
                                    :error="errors.part_number"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-4">
                                <FormField
                                    id="u_height"
                                    v-model="formData.u_height"
                                    label="Height (U)"
                                    type="number"
                                    :error="errors.u_height"
                                    help-text="Height in rack units (default: 1)"
                                />
                            </div>
                            <div class="col-md-4">
                                <FormField
                                    id="is_full_depth"
                                    v-model="formData.is_full_depth"
                                    label="Is Full Depth"
                                    type="select"
                                    :options="booleanOptions"
                                    help-text="Device consumes both front and rear rack faces"
                                    :error="errors.is_full_depth"
                                />
                            </div>
                            <div class="col-md-4">
                                <FormField
                                    id="subdevice_role"
                                    v-model="formData.subdevice_role"
                                    label="Subdevice Role"
                                    type="select"
                                    :options="subdeviceRoleOptions"
                                    help-text="Parent/child status (optional)"
                                    :error="errors.subdevice_role"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="comments"
                                    v-model="formData.comments"
                                    label="Comments"
                                    type="textarea"
                                    placeholder="Additional comments"
                                    :error="errors.comments"
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
    name: 'DeviceTypeCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                manufacturer: '',
                model: '',
                device_family: '',
                part_number: '',
                u_height: 1,
                is_full_depth: true,
                subdevice_role: '',
                comments: '',
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            manufacturerOptions: [],
            deviceFamilyOptions: [],
            booleanOptions: [
                { value: 'true', label: 'Yes' },
                { value: 'false', label: 'No' },
            ],
            subdeviceRoleOptions: [
                { value: '', label: '-- None --' },
                { value: 'parent', label: 'Parent' },
                { value: 'child', label: 'Child' },
            ],
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
                this.manufacturerOptions = (manufacturers.results || []).map(
                    (m) => ({
                        value: m.id,
                        label: m.display || m.name,
                    }),
                );

                const deviceFamilies = await this.api.getList(
                    '/dcim/device-families/',
                );
                this.deviceFamilyOptions = [
                    { value: '', label: '-- None --' },
                    ...(deviceFamilies.results || []).map((df) => ({
                        value: df.id,
                        label: df.display || df.name,
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

            if (!this.formData.manufacturer) {
                this.errors.manufacturer = 'Manufacturer is required';
            }
            if (!this.formData.model) {
                this.errors.model = 'Model is required';
            }

            if (Object.keys(this.errors).length > 0) {
                this.submitting = false;
                return;
            }

            try {
                const payload = {
                    manufacturer: this.formData.manufacturer,
                    model: this.formData.model,
                    u_height: this.formData.u_height || 1,
                    is_full_depth:
                        this.formData.is_full_depth === true ||
                        this.formData.is_full_depth === 'true',
                };

                if (this.formData.device_family) {
                    payload.device_family = this.formData.device_family;
                }
                if (this.formData.part_number) {
                    payload.part_number = this.formData.part_number;
                }
                if (this.formData.subdevice_role) {
                    payload.subdevice_role = this.formData.subdevice_role;
                }
                if (this.formData.comments) {
                    payload.comments = this.formData.comments;
                }

                const deviceType = await this.api.post(
                    '/dcim/device-types/',
                    payload,
                );

                this.$router.push({
                    name: 'device-type-detail',
                    params: { id: deviceType.id },
                });
            } catch (err) {
                this.submitError =
                    err.message || 'Failed to create device type';
                // eslint-disable-next-line no-console
                console.error('Error creating device type:', err);
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
