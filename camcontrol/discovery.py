from __future__ import annotations

import sys
from typing import List, Optional

from .device import DeviceInfo
from .exceptions import DiscoveryError


def find_devices() -> List[DeviceInfo]:
    """
    Windows-only in Phase 1.

    Kept as a thin dispatcher so Linux/macOS backends can be added later without
    leaking platform-specific logic into the rest of the package.
    """
    if sys.platform != "win32":
        raise DiscoveryError("Device discovery is currently supported on Windows only.")
    from .discovery_windows import find_devices as impl

    return impl()


def pick_default_device(devices: List[DeviceInfo]) -> Optional[DeviceInfo]:
    if sys.platform != "win32":
        return None
    from .discovery_windows import pick_default_device as impl

    return impl(devices)
