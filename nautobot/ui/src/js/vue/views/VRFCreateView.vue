<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new VRF</h3>
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
                        <strong>VRF</strong>
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
                                    placeholder="VRF name"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="rd"
                                    v-model="formData.rd"
                                    label="Route Distinguisher"
                                    type="text"
                                    placeholder="e.g., 65000:100"
                                    help-text="Unique route distinguisher (as defined in RFC 4364)"
                                    :error="errors.rd"
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
                                    id="status"
                                    v-model="formData.status"
                                    label="Status"
                                    type="select"
                                    :options="statusOptions"
                                    :error="errors.status"
                                />
                            </div>
                        </div>

                        <div class="row">
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
                                    placeholder="VRF description"
                                    :error="errors.description"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="import_targets"
                                    v-model="formData.import_targets"
                                    label="Import Targets"
                                    type="multiselect"
                                    :options="routeTargetOptions"
                                    :error="errors.import_targets"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="export_targets"
                                    v-model="formData.export_targets"
                                    label="Export Targets"
                                    type="multiselect"
                                    :options="routeTargetOptions"
                                    :error="errors.export_targets"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="devices"
                                    v-model="formData.devices"
                                    label="Devices"
                                    type="multiselect"
                                    :options="deviceOptions"
                                    :error="errors.devices"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="virtual_machines"
                                    v-model="formData.virtual_machines"
                                    label="Virtual Machines"
                                    type="multiselect"
                                    :options="virtualMachineOptions"
                                    :error="errors.virtual_machines"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="virtual_device_contexts"
                                    v-model="formData.virtual_device_contexts"
                                    label="Virtual Device Contexts"
                                    type="multiselect"
                                    :options="virtualDeviceContextOptions"
                                    :error="errors.virtual_device_contexts"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-12">
                                <FormField
                                    id="prefixes"
                                    v-model="formData.prefixes"
                                    label="Prefixes"
                                    type="multiselect"
                                    :options="prefixOptions"
                                    :error="errors.prefixes"
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
    name: 'VRFCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                name: '',
                rd: '',
                namespace: '',
                status: '',
                tenant: '',
                description: '',
                import_targets: [],
                export_targets: [],
                devices: [],
                virtual_machines: [],
                virtual_device_contexts: [],
                prefixes: [],
                tags: [],
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            namespaceOptions: [],
            statusOptions: [],
            tenantOptions: [],
            routeTargetOptions: [],
            deviceOptions: [],
            virtualMachineOptions: [],
            virtualDeviceContextOptions: [],
            prefixOptions: [],
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
                const namespaces = await this.api.getList('/ipam/namespaces/');
                this.namespaceOptions = [
                    { value: '', label: '-- Use Default --' },
                    ...(namespaces.results || []).map((ns) => ({
                        value: ns.id,
                        label: ns.display || ns.name,
                    })),
                ];

                const statuses = await this.api.get('/extras/statuses/');
                this.statusOptions = [
                    { value: '', label: '-- None --' },
                    ...(statuses.results || []).map((status) => ({
                        value: status.id,
                        label: status.label || status.name,
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

                const routeTargets = await this.api.getList(
                    '/ipam/route-targets/',
                );
                this.routeTargetOptions = (routeTargets.results || []).map(
                    (rt) => ({
                        value: rt.id,
                        label: rt.display || rt.name,
                    }),
                );

                const devices = await this.api.getList('/dcim/devices/');
                this.deviceOptions = (devices.results || []).map((device) => ({
                    value: device.id,
                    label: device.display || device.name,
                }));

                const virtualMachines = await this.api.getList(
                    '/virtualization/virtual-machines/',
                );
                this.virtualMachineOptions = (
                    virtualMachines.results || []
                ).map((vm) => ({
                    value: vm.id,
                    label: vm.display || vm.name,
                }));

                const virtualDeviceContexts = await this.api.getList(
                    '/dcim/virtual-device-contexts/',
                );
                this.virtualDeviceContextOptions = (
                    virtualDeviceContexts.results || []
                ).map((vdc) => ({
                    value: vdc.id,
                    label: vdc.display || vdc.name,
                }));

                const prefixes = await this.api.getList('/ipam/prefixes/');
                this.prefixOptions = (prefixes.results || []).map((prefix) => ({
                    value: prefix.id,
                    label: prefix.display || prefix.prefix,
                }));

                const tags = await this.api.getList('/extras/tags/', {
                    content_types: 'ipam.vrf',
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
                this.submitting = false;
                return;
            }

            try {
                const payload = {
                    name: this.formData.name,
                };

                if (this.formData.rd) {
                    payload.rd = this.formData.rd;
                }
                if (this.formData.namespace) {
                    payload.namespace = this.formData.namespace;
                }
                if (this.formData.status) {
                    payload.status = this.formData.status;
                }
                if (this.formData.tenant) {
                    payload.tenant = this.formData.tenant;
                }
                if (this.formData.description) {
                    payload.description = this.formData.description;
                }
                if (
                    this.formData.import_targets &&
                    this.formData.import_targets.length > 0
                ) {
                    payload.import_targets = this.formData.import_targets;
                }
                if (
                    this.formData.export_targets &&
                    this.formData.export_targets.length > 0
                ) {
                    payload.export_targets = this.formData.export_targets;
                }
                if (this.formData.devices && this.formData.devices.length > 0) {
                    payload.devices = this.formData.devices;
                }
                if (
                    this.formData.virtual_machines &&
                    this.formData.virtual_machines.length > 0
                ) {
                    payload.virtual_machines = this.formData.virtual_machines;
                }
                if (
                    this.formData.virtual_device_contexts &&
                    this.formData.virtual_device_contexts.length > 0
                ) {
                    payload.virtual_device_contexts =
                        this.formData.virtual_device_contexts;
                }
                if (
                    this.formData.prefixes &&
                    this.formData.prefixes.length > 0
                ) {
                    payload.prefixes = this.formData.prefixes;
                }
                if (this.formData.tags && this.formData.tags.length > 0) {
                    payload.tags = this.formData.tags;
                }

                const vrf = await this.api.post('/ipam/vrfs/', payload);

                this.$router.push({
                    name: 'vrf-detail',
                    params: { id: vrf.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create VRF';
                // eslint-disable-next-line no-console
                console.error('Error creating VRF:', err);
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
