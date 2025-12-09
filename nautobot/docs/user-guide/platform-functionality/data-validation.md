# Data Validation Engine

+++ 3.0.0

The data validation engine offers a set of user definable rules which are used to enforce business constraints on the data in Nautobot. These rules are tied to particular models and each rule is meant to enforce one aspect of a business use case.

Supported rule types include:

- Regular expression
- Min/max value
- Required fields
- Unique values

![Dropdown](../../media/data-validation-engine/ss_dropdown_light.png#only-light){ .on-glb }
![Dropdown](../../media/data-validation-engine/ss_dropdown_dark.png#only-dark){ .on-glb }

## Use-cases and common workflows

### Min/Max Rules

![Min/Max Rules List](../../media/data-validation-engine/ss_min-max-rules-list_light.png#only-light){ .on-glb }
![Min/Max Rules List](../../media/data-validation-engine/ss_min-max-rules-list_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/min-max-rules/`"

Each rule is defined with these fields:

- name - A unique name for the rule.
- enabled - A boolean to toggle enforcement of the rule on and off.
- content type - The Nautobot model to which the rule should apply (e.g. device, location, etc.).
- field - The name of the numeric based field on the model to which the min/max value is validated.
- min - The min value to validate value against (greater than or equal).
- max - The max value to validate value against (less than or equal).
- error message - An optional error message to display to the user when validation fails. By default, a message indicating validation against the defined min/max value has failed is shown.

![Min/Max Rules Edit](../../media/data-validation-engine/ss_min-max-rules-edit_light.png#only-light){ .on-glb }
![Min/Max Rules Edit](../../media/data-validation-engine/ss_min-max-rules-edit_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/min-max-rules/57f06495-503e-5202-8ce3-ccba5acc8ecc/edit/`"

In this example, a max value for VLAN IDs has been configured, preventing VLANs greater than 3999 from being created.

![Min/Max Rules Enforcement](../../media/data-validation-engine/ss_min-max-rules-enforcement_light.png#only-light){ .on-glb }
![Min/Max Rules Enforcement](../../media/data-validation-engine/ss_min-max-rules-enforcement_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/ipam/vlans/add/`"

### Regular Expression Rules

![Regex Rules List](../../media/data-validation-engine/ss_regex-rules-list_light.png#only-light){ .on-glb }
![Regex Rules List](../../media/data-validation-engine/ss_regex-rules-list_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/regex-rules/`"

Each rule is defined with these fields:

- name - A unique name for the rule.
- enabled - A boolean to toggle enforcement of the rule on and off.
- content type - The Nautobot model to which the rule should apply (e.g. device, location, etc.).
- field - The name of the character based field on the model to which the regular expression is validated.
- regular expression - The body of the regular expression used for validation.
- context processing - A boolean to toggle Jinja2 context processing of the regular expression prior to evaluation
- error message - An optional error message to display to the use when validation fails. By default, a message indicating validation against the defined regular expression has failed is shown.

![Regex Rules Edit](../../media/data-validation-engine/ss_regex-rules-edit_light.png#only-light){ .on-glb }
![Regex Rules Edit](../../media/data-validation-engine/ss_regex-rules-edit_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/regex-rules/a5fbe536-92c1-4ea2-9634-0fb08f081532/edit/`"

In this example, a device hostname validation rule has been created and prevents device records from being created or updated that do not conform to the naming standard.

![Regex Rules Enforcement](../../media/data-validation-engine/ss_regex-rules-enforcement_light.png#only-light){ .on-glb }
![Regex Rules Enforcement](../../media/data-validation-engine/ss_regex-rules-enforcement_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/dcim/devices/add/`"

Regex rules may also support complex Jinja2 rendering called context processing which allows for the regular expression itself to by dynamically generated based on the context of the data it is validating.

In this example the name of a device must start with the first three characters of the name of the location to which the device belongs. The dynamic nature of the Jinja2 rendering means that the location name can be anything, the enforcement action is simply that the given device name matches its assigned location.

![Regex Rules Jinja2 Context Processing](../../media/data-validation-engine/ss_regex-rules-jinja2-context-processing_light.png#only-light){ .on-glb }
![Regex Rules Jinja2 Context Processing](../../media/data-validation-engine/ss_regex-rules-jinja2-context-processing_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/regex-rules/a5fbe536-92c1-4ea2-9634-0fb08f081532/`"

!!! warning
    If there is an exception while rendering the Jinja2 template or the resulting regular expression string is invalid, data validation against the rule will fail and users will be instructed to either fix the rule or disable it before the data may be saved.

### Required Rules

![Required List](../../media/data-validation-engine/ss_required-rules-list_light.png#only-light){ .on-glb }
![Required List](../../media/data-validation-engine/ss_required-rules-list_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/regex-rules/`"

Each rule is defined with these fields:

- name - A unique name for the rule.
- enabled - A boolean to toggle enforcement of the rule on and off.
- content type - The Nautobot model to which the rule should apply (e.g. device, location, etc.).
- field - The name of the field on the Nautobot model which should always be required.
- error message - An optional error message to display to the user when validation fails. By default, a message indicating the field may not be left blank is shown.

![Required Rules Edit](../../media/data-validation-engine/ss_required-rules-edit_light.png#only-light){ .on-glb }
![Required Rules Edit](../../media/data-validation-engine/ss_required-rules-edit_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/regex-rules/783fbab7-8b2d-40be-8649-621c025d2e42/edit/`"

In this example, a rule is enforcing that location objects must always have a description populated.

![Required Rules Enforcement](../../media/data-validation-engine/ss_required-rules-enforcement_light.png#only-light){ .on-glb }
![Required Rules Enforcement](../../media/data-validation-engine/ss_required-rules-enforcement_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/dcim/locations/add/`"

### Unique Rules

![Unique List](../../media/data-validation-engine/ss_unique-rules-list_light.png#only-light){ .on-glb }
![Unique List](../../media/data-validation-engine/ss_unique-rules-list_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/unique-rules/`"

Each rule is defined with these fields:

- name - A unique name for the rule.
- enabled - A boolean to toggle enforcement of the rule on and off.
- content type - The Nautobot model to which the rule should apply (e.g. device, location, etc.).
- field - The name of the field on the Nautobot model which should always be required.
- max instances - The total number of records that may have the same unique value for the given field. Default of 1.
- error message - An optional error message to display to the user when validation fails. By default, a message indicating the value already exists on another record or set of records, as determined by max instances.

![Unique Rules Edit](../../media/data-validation-engine/ss_unique-rules-edit_light.png#only-light){ .on-glb }
![Unique Rules Edit](../../media/data-validation-engine/ss_unique-rules-edit_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/data-validation/unique-rules/add/`"

In this example, the rule enforces that the assigned ASN for a location is unique across all other locations.

![Unique Rules Enforcement](../../media/data-validation-engine/ss_unique-rules-enforcement_light.png#only-light){ .on-glb }
![Unique Rules Enforcement](../../media/data-validation-engine/ss_unique-rules-enforcement_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/dcim/locations/add/`"
