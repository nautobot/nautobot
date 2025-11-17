<template>
    <form
        id="nb-create-form"
        class="h-100 vstack"
        @submit.prevent="handleSubmit"
    >
        <div class="row justify-content-center align-content-start flex-fill">
            <div class="col-lg-8 col-md-10 mb-10">
                <h3>Add a new Interface</h3>
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
                        <strong>Interface</strong>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="device"
                                    v-model="formData.device"
                                    label="Device"
                                    type="select"
                                    :options="deviceOptions"
                                    :required="true"
                                    :error="errors.device"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="name"
                                    v-model="formData.name"
                                    label="Name"
                                    type="text"
                                    :required="true"
                                    :error="errors.name"
                                    placeholder="e.g., GigabitEthernet0/1"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="type"
                                    v-model="formData.type"
                                    label="Type"
                                    type="select"
                                    :options="typeOptions"
                                    :required="true"
                                    :error="errors.type"
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
                                    id="enabled"
                                    v-model="formData.enabled"
                                    label="Enabled"
                                    type="select"
                                    :options="booleanOptions"
                                    :error="errors.enabled"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="mgmt_only"
                                    v-model="formData.mgmt_only"
                                    label="Management Only"
                                    type="select"
                                    :options="booleanOptions"
                                    help-text="This interface is used only for out-of-band management"
                                    :error="errors.mgmt_only"
                                />
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <FormField
                                    id="mac_address"
                                    v-model="formData.mac_address"
                                    label="MAC Address"
                                    type="text"
                                    placeholder="00:00:00:00:00:00"
                                    :error="errors.mac_address"
                                />
                            </div>
                            <div class="col-md-6">
                                <FormField
                                    id="mtu"
                                    v-model="formData.mtu"
                                    label="MTU"
                                    type="number"
                                    placeholder="1500"
                                    :error="errors.mtu"
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
                                    placeholder="Interface description"
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
    name: 'InterfaceCreateView',
    components: {
        FormField,
    },
    data() {
        return {
            formData: {
                device: '',
                name: '',
                type: '',
                status: '',
                enabled: true,
                mgmt_only: false,
                mac_address: '',
                mtu: '',
                description: '',
            },
            errors: {},
            submitError: null,
            submitting: false,
            loading: true,
            deviceOptions: [],
            statusOptions: [],
            typeOptions: [
                // Virtual
                { value: 'virtual', label: 'Virtual' },
                { value: 'bridge', label: 'Bridge' },
                { value: 'lag', label: 'Link Aggregation Group (LAG)' },
                { value: 'tunnel', label: 'Tunnel' },
                // Common Ethernet
                { value: '100base-tx', label: '100BASE-TX (10/100ME)' },
                { value: '1000base-t', label: '1000BASE-T (1GE)' },
                { value: '1000base-x-sfp', label: '1000BASE-X (SFP)' },
                { value: '2.5gbase-t', label: '2.5GBASE-T (2.5GE)' },
                { value: '5gbase-t', label: '5GBASE-T (5GE)' },
                { value: '10gbase-t', label: '10GBASE-T (10GE)' },
                { value: '10gbase-x-sfpp', label: '10GBASE-X (SFP+)' },
                { value: '25gbase-x-sfp28', label: '25GBASE-X (SFP28)' },
                { value: '40gbase-x-qsfpp', label: '40GBASE-X (QSFP+)' },
                { value: '100gbase-x-qsfp28', label: '100GBASE-X (QSFP28)' },
                { value: '100gbase-x-qsfpdd', label: '100GBASE-X (QSFP-DD)' },
                { value: '400gbase-x-qsfpdd', label: '400GBASE-X (QSFP-DD)' },
                // Wireless
                { value: 'ieee802.11a', label: 'IEEE 802.11a' },
                { value: 'ieee802.11g', label: 'IEEE 802.11g' },
                { value: 'ieee802.11n', label: 'IEEE 802.11n' },
                { value: 'ieee802.11ac', label: 'IEEE 802.11ac' },
                { value: 'ieee802.11ax', label: 'IEEE 802.11ax' },
                // Other
                { value: 'other', label: 'Other' },
            ],
            booleanOptions: [
                { value: 'true', label: 'Yes' },
                { value: 'false', label: 'No' },
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
                const devices = await this.api.getList('/dcim/devices/');
                this.deviceOptions = (devices.results || []).map((d) => ({
                    value: d.id,
                    label: d.display || d.name || d.id,
                }));

                const statuses = await this.api.get('/extras/statuses/');
                this.statusOptions = (statuses.results || []).map((status) => ({
                    value: status.id,
                    label: status.label || status.name,
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

            if (!this.formData.device) {
                this.errors.device = 'Device is required';
            }
            if (!this.formData.name) {
                this.errors.name = 'Name is required';
            }
            if (!this.formData.type) {
                this.errors.type = 'Type is required';
            }
            if (!this.formData.status) {
                this.errors.status = 'Status is required';
            }

            if (Object.keys(this.errors).length > 0) {
                this.submitting = false;
                return;
            }

            try {
                const payload = {
                    device: this.formData.device,
                    name: this.formData.name,
                    type: this.formData.type,
                    status: this.formData.status,
                    enabled:
                        this.formData.enabled === true ||
                        this.formData.enabled === 'true',
                    mgmt_only:
                        this.formData.mgmt_only === true ||
                        this.formData.mgmt_only === 'true',
                };

                if (this.formData.mac_address) {
                    payload.mac_address = this.formData.mac_address;
                }
                if (this.formData.mtu) {
                    payload.mtu = parseInt(this.formData.mtu, 10);
                }
                if (this.formData.description) {
                    payload.description = this.formData.description;
                }

                const interfaceItem = await this.api.post(
                    '/dcim/interfaces/',
                    payload,
                );

                this.$router.push({
                    name: 'interface-detail',
                    params: { id: interfaceItem.id },
                });
            } catch (err) {
                this.submitError = err.message || 'Failed to create interface';
                // eslint-disable-next-line no-console
                console.error('Error creating interface:', err);
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
