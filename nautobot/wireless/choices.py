from nautobot.core.choices import ChoiceSet


class RadioFrequencyChoices(ChoiceSet):
    FREQUENCY_24G = "2.4 GHz"
    FREQUENCY_5G = "5GHz"
    FREQUENCY_6G = "6GHz"

    CHOICES = (
        (FREQUENCY_24G, "2.4 GHz"),
        (FREQUENCY_5G, "5 GHz"),
        (FREQUENCY_6G, "6 GHz"),
    )


class RadioStandardChoices(ChoiceSet):
    A = "802.11a"
    B = "802.11b"
    G = "802.11g"
    N = "802.11n"
    AC = "802.11ac"
    AX = "802.11ax"
    BE = "802.11be"

    CHOICES = (
        (A, "802.11a"),
        (B, "802.11b"),
        (G, "802.11g"),
        (N, "802.11n"),
        (AC, "802.11ac"),
        (AX, "802.11ax"),
        (BE, "802.11be"),
    )


class WirelessDeploymentModeChoices(ChoiceSet):
    CENTRAL = "Central (tunnelMode(controller managed))"
    FABRIC = "Fabric"
    STANDALONE = "Standalone (Autonomous)"
    LOCAL = "Local (Flex)"
    MESH = "Mesh"
    BRIDGE = "Bridge"

    CHOICES = (
        (CENTRAL, "Central (tunnelMode(controller managed))"),
        (FABRIC, "Fabric"),
        (STANDALONE, "Standalone (Autonomous)"),
        (LOCAL, "Local (Flex)"),
        (MESH, "Mesh"),
        (BRIDGE, "Bridge"),
    )


class WirelessAuthTypeChoices(ChoiceSet):
    OPEN = "Open"
    WPA2_PERSONAL = "WPA2 Personal"
    WPA2_ENTERPRISE = "WPA2 Enterprise"
    ENHANCED_OPEN = "Enhanced Open"
    WPA3_PERSONAL = "WPA3 Personal"
    WPA3_SAE = "WPA3 SAE"
    WPA3_ENTERPRISE = "WPA3 Enterprise"
    WPA3_ENTERPRISE_192_BIT = "WPA3 Enterprise 192Bit"

    CHOICES = (
        (OPEN, "Open"),
        (WPA2_PERSONAL, "WPA2 Personal"),
        (WPA2_ENTERPRISE, "WPA2 Enterprise"),
        (ENHANCED_OPEN, "Enhanced Open"),
        (WPA3_PERSONAL, "WPA3 Personal"),
        (WPA3_SAE, "WPA3 SAE"),
        (WPA3_ENTERPRISE, "WPA3 Enterprise"),
        (WPA3_ENTERPRISE_192_BIT, "WPA3 Enterprise 192Bit"),
    )
