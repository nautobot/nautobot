document.addEventListener('DOMContentLoaded', () => {
    const parseTypeSet = (elementId) => {
        const encodedTypes = document.getElementById(elementId)?.textContent;
        if (!encodedTypes) {
            return new Set();
        }

        return new Set(JSON.parse(encodedTypes));
    };

    const minMaxTypes = parseTypeSet('nb-custom-field-min-max-types');
    const regexTypes = parseTypeSet('nb-custom-field-regex-types');
    const choiceTypes = new Set(['select', 'multi-select']);

    const setSectionVisibility = (element, visible) => {
        if (!element) {
            return;
        }
        element.classList.toggle('d-none', !visible);
    };

    const setFieldVisibility = (containerId, visible) => {
        const container = document.getElementById(containerId);
        if (!container) {
            return;
        }

        setSectionVisibility(container, visible);
        container.querySelectorAll('input, select, textarea').forEach((field) => {
            field.disabled = !visible;
        });
    };

    const setChoicesFieldSubmissionState = (enabled) => {
        const choicesCard = document.getElementById('nb-custom-field-choices-card');
        if (!choicesCard) {
            return;
        }

        const managementFields = [
            choicesCard.querySelector('input[name$="-TOTAL_FORMS"]'),
            choicesCard.querySelector('input[name$="-INITIAL_FORMS"]'),
            choicesCard.querySelector('input[name$="-MIN_NUM_FORMS"]'),
            choicesCard.querySelector('input[name$="-MAX_NUM_FORMS"]'),
        ].filter(Boolean);

        if (!enabled) {
            managementFields.forEach((field) => {
                if (!Object.hasOwn(field.dataset, 'originalValue')) {
                    field.dataset.originalValue = field.value;
                }
            });
            const totalFormsField = choicesCard.querySelector('input[name$="-TOTAL_FORMS"]');
            const initialFormsField = choicesCard.querySelector('input[name$="-INITIAL_FORMS"]');
            if (totalFormsField) {
                totalFormsField.value = '0';
            }
            if (initialFormsField) {
                initialFormsField.value = '0';
            }
        } else {
            managementFields.forEach((field) => {
                if (Object.hasOwn(field.dataset, 'originalValue')) {
                    field.value = field.dataset.originalValue;
                }
            });
        }

        choicesCard.querySelectorAll('input[name], select[name], textarea[name]').forEach((field) => {
            const name = field.getAttribute('name') || '';
            const isManagementFormField = /-(TOTAL_FORMS|INITIAL_FORMS|MIN_NUM_FORMS|MAX_NUM_FORMS)$/.test(name);
            if (!isManagementFormField) {
                field.disabled = !enabled;
            }
        });
    };

    const setFieldHelpText = (containerId, helpText) => {
        const container = document.getElementById(containerId);
        if (!container) {
            return;
        }

        const helpTextElement = container.querySelector('.form-text, .help-block');
        if (!helpTextElement) {
            return;
        }

        helpTextElement.innerHTML = helpText;
    };

    const updateMinMaxHelpText = (selectedType) => {
        if (selectedType === 'integer') {
            setFieldHelpText('nb-validation-minimum-field', 'Minimum numeric value.');
            setFieldHelpText('nb-validation-maximum-field', 'Maximum numeric value.');
            return;
        }

        setFieldHelpText('nb-validation-minimum-field', 'Minimum length of the value.');
        setFieldHelpText('nb-validation-maximum-field', 'Maximum length of the value.');
    };

    const updateCustomFieldTypePanels = () => {
        const typeField = document.getElementById('id_type');
        if (!typeField) {
            return;
        }

        const selectedType = typeField.value;
        updateMinMaxHelpText(selectedType);

        const showMinMax = minMaxTypes.has(selectedType);
        const showRegex = regexTypes.has(selectedType);
        const showValidationCard = showMinMax || showRegex;
        const showChoicesCard = choiceTypes.has(selectedType);

        setSectionVisibility(document.getElementById('nb-validation-rules-card'), showValidationCard);
        setFieldVisibility('nb-validation-minimum-field', showMinMax);
        setFieldVisibility('nb-validation-maximum-field', showMinMax);
        setFieldVisibility('nb-validation-regex-field', showRegex);

        const choicesCard = document.getElementById('nb-custom-field-choices-card');
        setSectionVisibility(choicesCard, showChoicesCard);
        setChoicesFieldSubmissionState(showChoicesCard);
    };

    const typeField = document.getElementById('id_type');
    if (typeField) {
        typeField.addEventListener('change', updateCustomFieldTypePanels);
    }
    updateCustomFieldTypePanels();
});
