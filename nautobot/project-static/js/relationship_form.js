document.addEventListener('DOMContentLoaded', () => {
    const SYMMETRIC_RELATIONSHIP_TYPES = new Set(['symmetric-one-to-one', 'symmetric-many-to-many']);
    const SYMMETRIC_TYPE_HELP_TEXT_ID = 'relationship-symmetric-type-help';
    const SYMMETRIC_TYPE_HELP_TEXT = 'Symmetric type: Destination fields mirror source values automatically.';

    const form = document.querySelector('#nb-create-form');
    if (!form) {
        return;
    }

    const typeField = document.querySelector('#id_type');
    const sourceTypeField = document.querySelector('#id_source_type');
    const sourceLabelField = document.querySelector('#id_source_label');
    const sourceHiddenField = document.querySelector('#id_source_hidden');
    const sourceFilterField = document.querySelector('#id_source_filter');

    const destinationTypeField = document.querySelector('#id_destination_type');
    const destinationLabelField = document.querySelector('#id_destination_label');
    const destinationHiddenField = document.querySelector('#id_destination_hidden');
    const destinationFilterField = document.querySelector('#id_destination_filter');

    const mirroredFieldPairs = [
        [sourceTypeField, destinationTypeField],
        [sourceLabelField, destinationLabelField],
        [sourceHiddenField, destinationHiddenField],
        [sourceFilterField, destinationFilterField],
    ].filter(([sourceField, destinationField]) => sourceField && destinationField);

    const managedDestinationFields = mirroredFieldPairs.map(([, destinationField]) => destinationField);

    const isSymmetricTypeSelected = () => typeField && SYMMETRIC_RELATIONSHIP_TYPES.has(typeField.value);

    const updateTypeFieldSymmetricHelpText = (isSymmetric) => {
        if (!typeField) {
            return;
        }

        const typeFieldContainer = typeField.closest('.col-md-9');
        if (!typeFieldContainer) {
            return;
        }

        const existingText = typeFieldContainer.querySelector(`#${SYMMETRIC_TYPE_HELP_TEXT_ID}`);
        if (isSymmetric) {
            if (existingText) {
                return;
            }

            const helpText = document.createElement('span');
            helpText.classList.add('form-text', 'w-100');
            helpText.id = SYMMETRIC_TYPE_HELP_TEXT_ID;
            helpText.textContent = SYMMETRIC_TYPE_HELP_TEXT;
            typeFieldContainer.appendChild(helpText);
            return;
        }

        existingText?.remove();
    };

    const setSelectValue = (field, value) => {
        if (!field) {
            return;
        }
        field.value = value;
        field.dispatchEvent(new Event('change', { bubbles: true }));
    };

    const copyFieldValue = (sourceField, destinationField) => {
        if (!sourceField || !destinationField) {
            return;
        }

        if (sourceField.tagName === 'SELECT') {
            setSelectValue(destinationField, sourceField.value);
            return;
        }

        if (sourceField.type === 'checkbox') {
            destinationField.checked = sourceField.checked;
            destinationField.dispatchEvent(new Event('change', { bubbles: true }));
            return;
        }

        destinationField.value = sourceField.value;
    };

    const mirrorSourceToDestination = () => {
        mirroredFieldPairs.forEach(([sourceField, destinationField]) => copyFieldValue(sourceField, destinationField));
    };

    const updateDestinationFieldDisabledState = (isDisabled) => {
        managedDestinationFields.forEach((field) => {
            field.disabled = isDisabled;
            if (field.tagName === 'SELECT') {
                field.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    };

    const handleSymmetricStateChange = () => {
        const isSymmetric = isSymmetricTypeSelected();
        if (isSymmetric) {
            mirrorSourceToDestination();
        }
        updateDestinationFieldDisabledState(isSymmetric);
        updateTypeFieldSymmetricHelpText(isSymmetric);
    };

    if (typeField) {
        typeField.addEventListener('change', handleSymmetricStateChange);
    }

    mirroredFieldPairs.forEach(([sourceField]) => {
        sourceField.addEventListener('change', () => {
            if (isSymmetricTypeSelected()) {
                mirrorSourceToDestination();
            }
        });
        if (sourceField.tagName !== 'SELECT' && sourceField.type !== 'checkbox') {
            sourceField.addEventListener('input', () => {
                if (isSymmetricTypeSelected()) {
                    mirrorSourceToDestination();
                }
            });
        }
    });

    form.addEventListener('submit', () => {
        if (isSymmetricTypeSelected()) {
            mirrorSourceToDestination();
        }
        updateDestinationFieldDisabledState(false);
    });

    handleSymmetricStateChange();
});
