# Cisco Stackwise

Cisco StackWise allows up to 8–9 physical switches to behave as a single logical unit, offering unified management (one IP), high-speed backplane stacking (up to 1Tbps), and increased port density with redundancy. Key features include hot-swappable switches, a master/subordinate architecture for shared control planes, and reduced operational complexity. 

Whitepaper
https://www.cisco.com/c/en/us/products/collateral/switches/catalyst-9300-series-switches/white-paper-c11-741468.html


1. Use the Nautobot Virtual Chassis feature to represent the stackwise stacks  {{ stackwise_stackname }}
2. The hostname of the stackwise stack should be the hostname of the master switch
3. The master switch should be the first switch in the stack and the master
  - Named  {{ stackwise_stackname }}
  - Device type shouldn't have templated interface components.
  - All device components should be defined on the master switch.
    - Interfaces
    - IP addresses
    - Protocols (e.g. bgp)
    - Redundancy Groups
4. The remaining switches in the stack should be {{ stackwise_stackname }}:{{ switch_number }}.
  - Only required fields should be defined (+ Serial Number)
  - No device components should be defined (interfaces, ip addresses, etc)j
  - Place individual devices on racks
5. (Optional) Business requirements considerations
  - One device role for all stackwise switches vs a device role for the master and a device role for the members, such as "switch" and "switch-child", to make filtering easier
  - One status for master and one status for child, such as "active" and "active-child", to make filtering easier


## Questions for Data model

Q. Can you port channel across multiple devices?
Q. Can you see all interfaces on the Primary? 
Q. Can you see all interfaces on the Backup? 
Q. On Primary, can you tell which interfaces are assigned to which device? 
Q. When do you see all the interfaces on the master device?
Q. Can you connect interfaces from master to non-master? 
Q. Any configurations don't map back to model? 
Q. How are interfaces named?
Q. What should the naming standard be for the chassis device?
Q. Should I use interface named templates?


