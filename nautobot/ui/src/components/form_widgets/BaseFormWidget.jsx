import { FormControl, FormLabel, shouldForwardProp } from '@chakra-ui/react';
import { labelValue } from '@rjsf/utils';


// This is a copy paste code from https://github.com/rjsf-team/react-jsonschema-form/blob/main/packages/chakra-ui/src/utils.ts
// as @chakra-ui/react do not provide access to this function
export function getChakra({ uiSchema = {} }) {
    const chakraProps = (uiSchema['ui:options'] && uiSchema['ui:options'].chakra) || {};
    Object.keys(chakraProps).forEach((key) => {
        if (shouldForwardProp(key)) {
            delete (chakraProps)[key];
        }
    });

    return chakraProps;
}

/*
  All Form widget should use this component as its parent component e.g
  <BaseFormWidget>
    <input />
  </BaseFormWidget>

*/
export default function BaseFormWidget({
    children,
    id,
    label,
    hideLabel,
    disabled,
    readonly,
    uiSchema,
    required,
    rawErrors,
}) {
  const chakraProps = getChakra({ uiSchema });

  return (
    <FormControl
      mb={1}
      {...chakraProps}
      isDisabled={disabled || readonly}
      isRequired={required}
      isReadOnly={readonly}
      isInvalid={rawErrors && rawErrors.length > 0}
    >
      {labelValue(<FormLabel htmlFor={id}>{label}</FormLabel>, hideLabel || !label)}
      {children}
    </FormControl>
  );
}