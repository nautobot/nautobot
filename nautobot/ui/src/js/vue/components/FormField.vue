<template>
    <div class="mb-3">
        <label v-if="type !== 'checkbox'" :for="id" class="form-label">
            {{ label }}
            <span v-if="required" class="text-danger">*</span>
        </label>
        <input
            v-if="type === 'text' || type === 'number'"
            :id="id"
            :type="type"
            :class="['form-control', { 'is-invalid': error }]"
            :value="modelValue"
            :required="required"
            :placeholder="placeholder"
            @input="$emit('update:modelValue', $event.target.value)"
        />
        <select
            v-else-if="type === 'select'"
            :id="id"
            :class="['form-select', { 'is-invalid': error }]"
            :value="modelValue"
            :required="required"
            @change="handleSelectChange"
        >
            <option v-if="!required" value="">-- Select --</option>
            <option
                v-for="option in options"
                :key="option.value"
                :value="option.value"
            >
                {{ option.label }}
            </option>
        </select>
        <textarea
            v-else-if="type === 'textarea'"
            :id="id"
            :class="['form-control', { 'is-invalid': error }]"
            :value="modelValue"
            :required="required"
            :placeholder="placeholder"
            rows="3"
            @input="$emit('update:modelValue', $event.target.value)"
        ></textarea>
        <select
            v-else-if="type === 'multiselect'"
            :id="id"
            :class="['form-select', { 'is-invalid': error }]"
            :required="required"
            multiple
            @change="handleMultiSelectChange"
        >
            <option
                v-for="option in options"
                :key="option.value"
                :value="option.value"
                :selected="
                    Array.isArray(modelValue) &&
                    modelValue.includes(option.value)
                "
            >
                {{ option.label }}
            </option>
        </select>
        <div v-else-if="type === 'checkbox'" class="form-check">
            <input
                :id="id"
                type="checkbox"
                :class="['form-check-input', { 'is-invalid': error }]"
                :checked="modelValue"
                @change="$emit('update:modelValue', $event.target.checked)"
            />
            <label :for="id" class="form-check-label">
                {{ label }}
            </label>
        </div>
        <input
            v-else-if="type === 'color'"
            :id="id"
            type="color"
            :class="[
                'form-control form-control-color',
                { 'is-invalid': error },
            ]"
            :value="modelValue || '#000000'"
            :required="required"
            @input="$emit('update:modelValue', $event.target.value)"
        />
        <div v-if="error && type !== 'checkbox'" class="invalid-feedback">
            {{ error }}
        </div>
        <div v-if="error && type === 'checkbox'" class="text-danger small">
            {{ error }}
        </div>
        <small
            v-if="helpText && type !== 'checkbox'"
            class="form-text text-muted"
            >{{ helpText }}</small
        >
    </div>
</template>

<script>
export default {
    name: 'FormField',
    props: {
        id: {
            type: String,
            required: true,
        },
        label: {
            type: String,
            required: true,
        },
        type: {
            type: String,
            default: 'text',
            validator: (value) =>
                [
                    'text',
                    'number',
                    'select',
                    'textarea',
                    'multiselect',
                    'checkbox',
                    'color',
                ].includes(value),
        },
        modelValue: {
            type: [String, Number, Boolean, Array],
            default: '',
        },
        required: {
            type: Boolean,
            default: false,
        },
        placeholder: {
            type: String,
            default: '',
        },
        helpText: {
            type: String,
            default: '',
        },
        error: {
            type: String,
            default: '',
        },
        options: {
            type: Array,
            default: () => [],
        },
    },
    emits: ['update:modelValue'],
    methods: {
        handleSelectChange(event) {
            const value = event.target.value;
            // Handle boolean values from select
            if (value === 'true') {
                this.$emit('update:modelValue', true);
            } else if (value === 'false') {
                this.$emit('update:modelValue', false);
            } else {
                this.$emit('update:modelValue', value);
            }
        },
        handleMultiSelectChange(event) {
            const selectedOptions = Array.from(event.target.selectedOptions);
            const values = selectedOptions.map((option) => option.value);
            this.$emit('update:modelValue', values);
        },
    },
};
</script>
