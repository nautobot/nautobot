from django.core.exceptions import ValidationError


class KubernetesJobManifestError(ValidationError):
    """Raised when we are unable to retrieve a kubernetes job manifest."""
