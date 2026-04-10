class CamlockError(Exception):
    """Base exception for camlock."""


class DiscoveryError(CamlockError):
    """Raised when device discovery fails."""


class ConnectionError(CamlockError):
    """Raised when serial connection cannot be established or is lost."""


class ProtocolError(CamlockError):
    """Raised for malformed commands/responses."""

