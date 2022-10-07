# Devices and Cabling

{%
    include-markdown "../models/dcim/device.md"
    heading-offset=1
%}
{%
    include-markdown "../models/dcim/devicerole.md"
    heading-offset=1
%}
{%
    include-markdown "../models/dcim/platform.md"
    heading-offset=1
%}

---

## Device Components

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).

{%
    include-markdown "../models/dcim/consoleport.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/consoleserverport.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/powerport.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/poweroutlet.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/interface.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/frontport.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/rearport.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/devicebay.md"
    heading-offset=2
%}
{%
    include-markdown "../models/dcim/inventoryitem.md"
    heading-offset=2
%}

---

{%
    include-markdown "../models/dcim/virtualchassis.md"
    heading-offset=1
%}

---

{%
    include-markdown "../models/dcim/cable.md"
    heading-offset=1
%}
