"""
Plugin Data Models

Defines the core data structures for plugin manifests, discovered plugins,
load failure diagnostics, and loaded plugin instances.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type

from src.api.v1.algorithm import ITrackingAlgorithm


@dataclass(frozen=True)
class PluginManifest:
    """Represents a validated algorithm plugin manifest."""
    name: str
    version: str
    api_version: str
    entry_point: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def parse_entry_point(self) -> Tuple[str, str]:
        """Splits the entry_point into (module_name, class_name)."""
        parts = self.entry_point.split(":")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise ValueError(f"Invalid entry_point syntax: '{self.entry_point}'. Expected 'module:ClassName'.")
        return parts[0].strip(), parts[1].strip()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes manifest to a dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "api_version": self.api_version,
            "entry_point": self.entry_point,
            "description": self.description,
            "author": self.author,
            "dependencies": list(self.dependencies),
            "metadata": dict(self.metadata)
        }


@dataclass
class PluginFailure:
    """Represents a diagnostic record of a failed plugin during discovery or loading."""
    plugin_name: Optional[str]
    plugin_dir: Path
    error_type: str
    message: str
    exception: Optional[Exception] = None

    def __str__(self) -> str:
        name_str = f"'{self.plugin_name}' in " if self.plugin_name else ""
        return f"[{self.error_type}] Plugin {name_str}{self.plugin_dir.name}: {self.message}"


@dataclass
class DiscoveredPlugin:
    """Represents a discovered and validated plugin candidate."""
    name: str
    plugin_dir: Path
    manifest_path: Path
    manifest: PluginManifest
    algorithm_class: Optional[Type[ITrackingAlgorithm]] = None


@dataclass
class LoadedPlugin:
    """Represents an active, validated, and instantiated tracking algorithm plugin."""
    manifest: PluginManifest
    plugin_dir: Path
    algorithm_class: Type[ITrackingAlgorithm]
    instance: ITrackingAlgorithm


@dataclass
class DiscoveryResult:
    """
    Result container returned by PluginLoader.discover().
    
    Provides structured access to:
    - discovered: Mapping of plugin name -> DiscoveredPlugin
    - failures: List of PluginFailure records for broken/invalid plugins
    - ignored: List of harmless directories without manifest.json
    """
    discovered: Dict[str, DiscoveredPlugin] = field(default_factory=dict)
    failures: List[PluginFailure] = field(default_factory=list)
    ignored: List[Path] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.discovered)

    def __iter__(self) -> Iterator[DiscoveredPlugin]:
        return iter(self.discovered.values())

    def __getitem__(self, name: str) -> DiscoveredPlugin:
        return self.discovered[name]

    def __contains__(self, name: str) -> bool:
        return name in self.discovered

    def get(self, name: str, default: Optional[DiscoveredPlugin] = None) -> Optional[DiscoveredPlugin]:
        return self.discovered.get(name, default)

    @property
    def has_failures(self) -> bool:
        return len(self.failures) > 0
