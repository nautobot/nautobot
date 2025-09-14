# VPN

VPNs can be used to group multiple VPN Tunnels that share similar characteristics (e.g. connections to AWS) or belong to the same organizational unit such as a WAN (e.g. DM-VPN). When creating a VPN, users can specify a VPN Profile that defines common settings and policies for all associated tunnels. This profile can include parameters such as encryption methods, authentication protocols, and other relevant configurations.

!!! note
    At present, the main use case for VPNs is to group multiple VPN Tunnels that share similar traits. However, we plan to introduce additional functionalities for VPNs in future versions such as modeling overlay networks (MPLS, VXLAN, etc.) and possibly implementing advanced routing policies.
