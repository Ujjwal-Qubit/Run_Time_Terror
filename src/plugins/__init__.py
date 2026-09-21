"""
Algorithm Evaluation Platform Plugin Management Subsystem
"""

from .exceptions import (
    DuplicatePluginError,
    EntryPointResolutionError,
    InterfaceComplianceError,
    ManifestError,
    ManifestNotFoundError,
    ManifestParseError,
    ManifestValidationError,
    PluginError,
    PluginInstantiationError,
    PluginLoadError,
    UnsupportedApiVersionError,
)
from .loader import PluginLoader
from .models import (
    DiscoveredPlugin,
    DiscoveryResult,
    LoadedPlugin,
    PluginFailure,
    PluginManifest,
)

__all__ = [
    "PluginLoader",
    "PluginManifest",
    "DiscoveredPlugin",
    "LoadedPlugin",
    "DiscoveryResult",
    "PluginFailure",
    "PluginError",
    "PluginLoadError",
    "ManifestError",
    "ManifestNotFoundError",
    "ManifestParseError",
    "ManifestValidationError",
    "UnsupportedApiVersionError",
    "DuplicatePluginError",
    "EntryPointResolutionError",
    "InterfaceComplianceError",
    "PluginInstantiationError",
]
