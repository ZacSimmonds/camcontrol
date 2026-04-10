class CamcontrolError(Exception):
    """Base exception for camcontrol."""


class DiscoveryError(CamcontrolError):
    """Raised when device discovery fails."""


class ConnectionError(CamcontrolError):
    """Raised when serial connection cannot be established or is lost."""


class ProtocolError(CamcontrolError):
    """Raised for malformed commands/responses."""
