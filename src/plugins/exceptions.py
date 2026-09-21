"""
Plugin System Exceptions

Defines the exception hierarchy for plugin discovery, manifest parsing,
entry point resolution, interface compliance verification, and instantiation.
"""

from pathlib import Path
from typing import Optional


class PluginError(Exception):
    """Base exception for all plugin system errors."""
    pass


class PluginLoadError(PluginError):
    """Base exception for errors encountered when loading a plugin."""

    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        plugin_dir: Optional[Path] = None,
        cause: Optional[Exception] = None
    ) -> None:
        super().__init__(message)
        self.plugin_name = plugin_name
        self.plugin_dir = plugin_dir
        self.cause = cause


class ManifestError(PluginLoadError):
    """Base exception for manifest-related errors."""
    pass


class ManifestNotFoundError(ManifestError):
    """Raised when manifest.json is expected but not found."""
    pass


class ManifestParseError(ManifestError):
    """Raised when manifest.json cannot be parsed as valid JSON."""
    pass


class ManifestValidationError(ManifestError):
    """Raised when manifest.json violates schema requirements."""
    pass


class UnsupportedApiVersionError(PluginLoadError):
    """Raised when a plugin requires an unsupported platform API version."""

    def __init__(
        self,
        message: str,
        requested_version: Optional[str] = None,
        supported_version: Optional[str] = None,
        plugin_name: Optional[str] = None,
        plugin_dir: Optional[Path] = None
    ) -> None:
        super().__init__(message, plugin_name=plugin_name, plugin_dir=plugin_dir)
        self.requested_version = requested_version
        self.supported_version = supported_version


class DuplicatePluginError(PluginLoadError):
    """Raised when multiple plugins declare the same unique name."""

    def __init__(
        self,
        message: str,
        plugin_name: str,
        existing_dir: Optional[Path] = None,
        conflicting_dir: Optional[Path] = None
    ) -> None:
        super().__init__(message, plugin_name=plugin_name, plugin_dir=conflicting_dir)
        self.existing_dir = existing_dir
        self.conflicting_dir = conflicting_dir


class EntryPointResolutionError(PluginLoadError):
    """
    Raised when an entry point cannot be resolved:
    - Invalid syntax (missing ':')
    - Missing module or import failure
    - Missing attribute/class in module
    - Resolved object is not a class
    """
    pass


class InterfaceComplianceError(PluginLoadError):
    """
    Raised when a resolved class does not properly implement ITrackingAlgorithm:
    - Does not inherit from ITrackingAlgorithm
    - Is an abstract class with unimplemented abstract methods
    """
    pass


class PluginInstantiationError(PluginLoadError):
    """Raised when an algorithm class raises an exception during instantiation."""
    pass
