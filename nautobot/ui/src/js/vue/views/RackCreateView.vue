<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Rack</h3>
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
                        <strong>Rack</strong>
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
                                    id="rack_group"
                                    v-model="formData.rack_group"
                                    label="Rack Group"
                                    type="select"
                                    :options="rackGroupOptions"
                                    :error="errors.rack_group"
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
                                    :required="true"
                                    :error="errors.u_height"
                                    help-text="Height in rack units (default: 42)"
                                />
                            </div>
                            <div class="col-md-4">
                                <FormField
                                    id="width"
                                    v-model="formData.width"
                                    label="Width"
                                    type="select"
                                    :options="widthOptions"
                                    :error="errors.width"
                                />
                            </div>
                            <div class="col-md-4">
                                <FormField
                                    id="type"
                                    v-model="formData.type"
                                    label="Type"
                                    type="select"
                                    :options="typeOptions"
                                    :error="errors.type"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="facility_id"
                                    v-model="formData.facility_id"
                                    label="Facility ID"
                                    type="text"
                                    placeholder="Locally-assigned identifier"
                                    :error="errors.facility_id"
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
    name: 'RackCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                status: '',
                location: '',
                rack_group: '',
                u_height: 42,
                width: '19',
                type: '',
                facility_id: '',
                role: '',
                comments: '',
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            statusOptions: [],
            locationOptions: [],
            rackGroupOptions: [],
            roleOptions: [],
            widthOptions: [
                { value: '19', label: '19 inches' },
                { value: '23', label: '23 inches' },
            ],
            typeOptions: [
                { value: '', label: '-- None --' },
                { value: '2-post-frame', label: '2-Post Frame' },
                { value: '4-post-frame', label: '4-Post Frame' },
                { value: '4-post-cabinet', label: '4-Post Cabinet' },
                { value: 'wall-frame', label: 'Wall Frame' },
                { value: 'wall-cabinet', label: 'Wall Cabinet' },
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

                const rackGroups = await this.api.getList('/dcim/rack-groups/');
                this.rackGroupOptions = [
                    { value: '', label: '-- None --' },
                    ...(rackGroups.results || []).map((rg) => ({
                        value: rg.id,
                        label: rg.display || rg.name,
                    })),
                ];

                const roles = await this.api.getList('/extras/roles/', {
                    content_types: ['dcim.rack'],
                });
                this.roleOptions = [
                    { value: '', label: '-- None --' },
                    ...(roles.results || []).map((role) => ({
                        value: role.id,
                        label: role.display || role.name,
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
            }
            if (!this.formData.status) {
                this.errors.status = 'Status is required';
            }
            if (!this.formData.location) {
                this.errors.location = 'Location is required';
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
                    u_height: this.formData.u_height || 42,
                };

                if (this.formData.rack_group) {
                    payload.rack_group = this.formData.rack_group;
                }
                if (this.formData.width) {
                    payload.width = this.formData.width;
                }
                if (this.formData.type) {
                    payload.type = this.formData.type;
                }
                if (this.formData.facility_id) {
                    payload.facility_id = this.formData.facility_id;
                }
                if (this.formData.role) {
                    payload.role = this.formData.role;
                }
                if (this.formData.comments) {
                    payload.comments = this.formData.comments;
                }

                const rack = await this.api.post('/dcim/racks/', payload);

                this.$router.push({
                    name: 'rack-detail',
                    params: { id: rack.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create rack';
                // eslint-disable-next-line no-console
                console.error('Error creating rack:', err);
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
