# Error Code Overview

The usage of error codes is provided in Nautobot wherever the application raises an error. This does not account for errors sent by other systems, such as Django, DRF, Jinja, or any other dependency. The error code system we employ is based on the ranges:

| Name                | Start | End  |
|---------------------|-------|------|
| Nautobot Core       | 0000  | 0999 |
| Nautobot Nornir     | 1000  | 1199 |
| Device Lifecycle    | 1200  | 1399 |
| Nornir Plugin       | 2000  | 2199 |
| Golden Config       | 3000  | 3199 |
| Custom Application  | 9000  | 9999 |

You are encouraged to use more random starting points in your custom application, to make it less likely to run into overlaps.
