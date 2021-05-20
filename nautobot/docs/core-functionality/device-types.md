# Device Types

{%
    include-markdown "../models/dcim/devicetype.md"
    heading-offset=1
%}
{%
    include-markdown "../models/dcim/manufacturer.md"
    heading-offset=1
%}

---

## Device Component Templates

Each device type is assigned a number of component templates which define the physical components within a device. These are:

* Console ports
* Console server ports
* Power ports
* Power outlets
* Network interfaces
* Front ports
* Rear ports
* Device bays (which house child devices)

Whenever a new device is created, its components are automatically created per the templates assigned to its device type. For example, a Juniper EX4300-48T device type might have the following component templates defined:

* One template for a console port ("Console")
* Two templates for power ports ("PSU0" and "PSU1")
* 48 templates for 1GE interfaces ("ge-0/0/0" through "ge-0/0/47")
* Four templates for 10GE interfaces ("xe-0/2/0" through "xe-0/2/3")

Once component templates have been created, every new device that you create as an instance of this type will automatically be assigned each of the components listed above.

!!! note
    Assignment of components from templates occurs only at the time of device creation. If you modify the templates of a device type, it will not affect devices which have already been created. However, you always have the option of adding, modifying, or deleting components on existing devices.

{%
    include-markdown "../models/dcim/consoleporttemplate.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/consoleserverporttemplate.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/powerporttemplate.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/poweroutlettemplate.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/interfacetemplate.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/frontporttemplate.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/rearporttemplate.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/devicebaytemplate.md"
    heading-offset=2
%}
