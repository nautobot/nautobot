"""Custom choices for the nautobot_vpn_models app."""

from nautobot.apps.choices import ChoiceSet
        
        
        
        
        
        
        
        
        
        
        
        
        
        
class IkeVersionChoices(ChoiceSet):
    """Choices for the ike_version field on the VPNPhase1Policy model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
        
class EncryptionAlgorithmChoices(ChoiceSet):
    """Choices for the encryption_algorithm field on the VPNPhase1Policy model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
class IntegrityAlgorithmChoices(ChoiceSet):
    """Choices for the integrity_algorithm field on the VPNPhase1Policy model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
class DhGroupChoices(ChoiceSet):
    """Choices for the dh_group field on the VPNPhase1Policy model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
        
        
class AuthenticationMethodChoices(ChoiceSet):
    """Choices for the authentication_method field on the VPNPhase1Policy model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
        
        
class EncryptionAlgorithmChoices(ChoiceSet):
    """Choices for the encryption_algorithm field on the VPNPhase2Policy model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
class IntegrityAlgorithmChoices(ChoiceSet):
    """Choices for the integrity_algorithm field on the VPNPhase2Policy model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
class PfsGroupChoices(ChoiceSet):
    """Choices for the pfs_group field on the VPNPhase2Policy model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
        
        
        
        
        
        
        
        
        
        
        
        
        
class EncapsulationChoices(ChoiceSet):
    """Choices for the encapsulation field on the VPNTunnel model."""

    # TODO INIT Add choices here
    NYC = "New York City"

    CHOICES = (
        (NYC, "New York City"),
    )
        
        
        
class VPNTunnelStatusChoices(ChoiceSet):
    """Choices for the status field on the VPNTunnel model."""

    # TODO INIT Add Status choices here
    STATUS_ACTIVE = "active"

    CHOICES = (
        (STATUS_ACTIVE, "Active"),
    )
        
        
        
        
        
        
        
        
        
        
        