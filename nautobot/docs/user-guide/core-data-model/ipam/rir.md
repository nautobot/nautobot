# Regional Internet Registries (RIRs)

[Regional Internet registries](https://en.wikipedia.org/wiki/Regional_Internet_registry) are responsible for the allocation of globally-routable address space. The five RIRs are ARIN, RIPE, APNIC, LACNIC, and AFRINIC. However, some address space has been set aside for internal use, such as defined in RFCs 1918 and 6598. Nautobot considers these RFCs as a sort of RIR as well; that is, an authority which "owns" certain address space. There also exist lower-tier registries which serve particular geographic areas.

Users can create whatever RIRs they like and optionally assign prefixes to an RIR. The RIR model includes a boolean flag which indicates whether the RIR allocates only private IP space.

For example, suppose your organization has been allocated 104.131.0.0/16 by ARIN. It also makes use of RFC 1918 addressing internally. You would first create RIRs named "ARIN" and "RFC 1918," then create a prefix for each of these top-level networks, assigning it to its respective RIR.

+/- 2.0.0
    The `Aggregate` model and its relationships to `RIR` were migrated to the `Prefix` model.
