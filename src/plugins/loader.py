"""
PluginLoader Subsystem

Discovers, parses, validates, and instantiates external tracking algorithm plugins
implementing the Phase 6.1 ITrackingAlgorithm public API.
"""

import importlib
import importlib.util
import inspect
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from src.api.v1 import API_VERSION, ITrackingAlgorithm
from src.plugins.exceptions import (
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
from src.plugins.models import (
    DiscoveredPlugin,
    DiscoveryResult,
    LoadedPlugin,
    PluginFailure,
    PluginManifest,
)

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Core manager responsible for discovering, validating, and loading algorithm plugins.
    
    Operates in isolated directories, supports deterministic alphabetical discovery,
    and isolates failures so invalid plugins do not crash discovery of valid ones.
    """

    def __init__(self, plugins_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize the PluginLoader.
        
        Args:
            plugins_dir: Root directory containing algorithm plugin subdirectories.
                         If None, defaults to `src/plugins/algorithms`.
        """
        if plugins_dir is None:
            self.plugins_dir = (Path(__file__).parent / "algorithms").resolve()
        else:
            self.plugins_dir = Path(plugins_dir).resolve()

        self.discovered_plugins: Dict[str, DiscoveredPlugin] = {}
        self.failures: List[PluginFailure] = []
        self.ignored_dirs: List[Path] = []
        self.loaded_plugins: Dict[str, LoadedPlugin] = {}

    def discover(self, validate_entry_points: bool = True) -> DiscoveryResult:
        """
        Discover and validate all algorithm plugins in the plugins directory.
        
        Distinguishes harmless non-plugin directories (e.g. lacking manifest.json)
        from actual plugin failures (e.g. malformed manifest, unsupported API version,
        missing or invalid entry points).
        
        Discovery order is deterministic (sorted alphabetically by directory name).
        Individual plugin errors are recorded in `failures` without halting discovery.
        
        Args:
            validate_entry_points: If True, entry point modules, classes, and interface
                                   compliance are resolved and validated during discovery.
                                   
        Returns:
            DiscoveryResult containing discovered plugins, failure records, and ignored directories.
        """
        self.discovered_plugins.clear()
        self.failures.clear()
        self.ignored_dirs.clear()

        if not self.plugins_dir.exists() or not self.plugins_dir.is_dir():
            logger.warning(f"Plugin directory does not exist or is not a directory: {self.plugins_dir}")
            return DiscoveryResult(
                discovered=self.discovered_plugins,
                failures=self.failures,
                ignored=self.ignored_dirs
            )

        # Deterministic alphabetical ordering
        subdirs = sorted(
            [d for d in self.plugins_dir.iterdir() if d.is_dir()],
            key=lambda p: p.name.lower()
        )

        for subdir in subdirs:
            # Skip hidden or private directories like __pycache__ or .pytest_cache
            if subdir.name.startswith((".", "__")):
                continue

            manifest_path = subdir / "manifest.json"

            # Case 1: Harmless directory without manifest.json
            if not manifest_path.is_file():
                self.ignored_dirs.append(subdir)
                continue

            # Case 2: Plugin candidate with manifest.json -> validate deterministically
            try:
                manifest = self.parse_manifest(manifest_path, plugin_dir=subdir)

                # Check duplicate plugin names across different directories
                if manifest.name in self.discovered_plugins:
                    existing = self.discovered_plugins[manifest.name]
                    raise DuplicatePluginError(
                        f"Duplicate plugin name '{manifest.name}' declared in '{subdir.name}'. "
                        f"Already registered from '{existing.plugin_dir.name}'.",
                        plugin_name=manifest.name,
                        existing_dir=existing.plugin_dir,
                        conflicting_dir=subdir
                    )

                algorithm_class: Optional[Type[ITrackingAlgorithm]] = None
                if validate_entry_points:
                    algorithm_class = self.resolve_entry_point(manifest, subdir)

                discovered = DiscoveredPlugin(
                    name=manifest.name,
                    plugin_dir=subdir,
                    manifest_path=manifest_path,
                    manifest=manifest,
                    algorithm_class=algorithm_class
                )
                self.discovered_plugins[manifest.name] = discovered

            except PluginLoadError as e:
                failure = PluginFailure(
                    plugin_name=getattr(e, "plugin_name", None),
                    plugin_dir=subdir,
                    error_type=type(e).__name__,
                    message=str(e),
                    exception=e
                )
                self.failures.append(failure)
                logger.error(f"Plugin discovery failed for '{subdir.name}': {e}")
            except Exception as e:
                failure = PluginFailure(
                    plugin_name=None,
                    plugin_dir=subdir,
                    error_type="UnexpectedError",
                    message=f"Unexpected error loading plugin from '{subdir.name}': {e}",
                    exception=e
                )
                self.failures.append(failure)
                logger.exception(f"Unexpected error loading plugin from '{subdir.name}': {e}")

        return DiscoveryResult(
            discovered=dict(self.discovered_plugins),
            failures=list(self.failures),
            ignored=list(self.ignored_dirs)
        )

    def parse_manifest(self, manifest_path: Path, plugin_dir: Optional[Path] = None) -> PluginManifest:
        """
        Parses and validates a plugin manifest.json file against the schema.
        
        Args:
            manifest_path: Path to the manifest.json file.
            plugin_dir: Optional plugin directory for error context.
            
        Returns:
            Validated PluginManifest instance.
            
        Raises:
            ManifestNotFoundError: If manifest file does not exist.
            ManifestParseError: If file is not valid JSON.
            ManifestValidationError: If required fields are missing or schema is violated.
            UnsupportedApiVersionError: If api_version is unsupported.
        """
        if not manifest_path.is_file():
            raise ManifestNotFoundError(
                f"Manifest file not found: {manifest_path}",
                plugin_dir=plugin_dir
            )

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ManifestParseError(
                f"Failed to parse JSON in manifest '{manifest_path.name}': {e.msg} (line {e.lineno}, col {e.colno})",
                plugin_dir=plugin_dir,
                cause=e
            ) from e
        except Exception as e:
            raise ManifestParseError(
                f"Failed to read manifest '{manifest_path}': {e}",
                plugin_dir=plugin_dir,
                cause=e
            ) from e

        if not isinstance(data, dict):
            raise ManifestValidationError(
                f"Manifest root must be a JSON object, got {type(data).__name__}",
                plugin_dir=plugin_dir
            )

        # Validate required string fields
        required_fields = ["name", "version", "api_version", "entry_point"]
        for req_field in required_fields:
            if req_field not in data:
                raise ManifestValidationError(
                    f"Manifest is missing required field '{req_field}'",
                    plugin_name=data.get("name") if isinstance(data.get("name"), str) else None,
                    plugin_dir=plugin_dir
                )
            val = data[req_field]
            if not isinstance(val, str) or not val.strip():
                raise ManifestValidationError(
                    f"Field '{req_field}' must be a non-empty string, got {val!r}",
                    plugin_name=data.get("name") if isinstance(data.get("name"), str) else None,
                    plugin_dir=plugin_dir
                )

        plugin_name = data["name"].strip()

        # Validate API version compatibility
        requested_api = data["api_version"].strip()
        if requested_api != API_VERSION:
            raise UnsupportedApiVersionError(
                f"Plugin '{plugin_name}' requires API version '{requested_api}', but platform supports '{API_VERSION}'",
                requested_version=requested_api,
                supported_version=API_VERSION,
                plugin_name=plugin_name,
                plugin_dir=plugin_dir
            )

        # Validate entry_point format syntax: 'module_name:ClassName'
        entry_point = data["entry_point"].strip()
        parts = entry_point.split(":")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise ManifestValidationError(
                f"Invalid entry_point syntax '{entry_point}' in plugin '{plugin_name}'. Expected 'module:ClassName'.",
                plugin_name=plugin_name,
                plugin_dir=plugin_dir
            )

        mod_name, cls_name = parts[0].strip(), parts[1].strip()
        if not all(p.isidentifier() for p in mod_name.split(".")):
            raise ManifestValidationError(
                f"Invalid module identifier '{mod_name}' in entry_point for plugin '{plugin_name}'",
                plugin_name=plugin_name,
                plugin_dir=plugin_dir
            )
        if not cls_name.isidentifier():
            raise ManifestValidationError(
                f"Invalid class identifier '{cls_name}' in entry_point for plugin '{plugin_name}'",
                plugin_name=plugin_name,
                plugin_dir=plugin_dir
            )

        # Validate optional fields
        dependencies = data.get("dependencies", [])
        if not isinstance(dependencies, list) or not all(isinstance(d, str) for d in dependencies):
            raise ManifestValidationError(
                f"Field 'dependencies' must be a list of strings, got {dependencies!r}",
                plugin_name=plugin_name,
                plugin_dir=plugin_dir
            )

        description = data.get("description", "")
        if not isinstance(description, str):
            raise ManifestValidationError(
                f"Field 'description' must be a string, got {type(description).__name__}",
                plugin_name=plugin_name,
                plugin_dir=plugin_dir
            )

        author = data.get("author", "")
        if not isinstance(author, str):
            raise ManifestValidationError(
                f"Field 'author' must be a string, got {type(author).__name__}",
                plugin_name=plugin_name,
                plugin_dir=plugin_dir
            )

        metadata = {
            k: v for k, v in data.items()
            if k not in {"name", "version", "api_version", "entry_point", "dependencies", "description", "author"}
        }

        return PluginManifest(
            name=plugin_name,
            version=data["version"].strip(),
            api_version=requested_api,
            entry_point=entry_point,
            description=description.strip(),
            author=author.strip(),
            dependencies=[d.strip() for d in dependencies],
            metadata=metadata
        )

    def resolve_entry_point(self, manifest: PluginManifest, plugin_dir: Path) -> Type[ITrackingAlgorithm]:
        """
        Resolves, imports, and validates the algorithm entry point class.
        
        Safely validates:
        1. Module exists and imports without error.
        2. Attribute exists on module.
        3. Attribute is a class (isinstance(cls, type)).
        4. Class inherits from ITrackingAlgorithm (issubclass).
        5. Class is not abstract (no unimplemented abstract methods).
        
        Args:
            manifest: The parsed plugin manifest.
            plugin_dir: Directory where the plugin is located.
            
        Returns:
            Resolved and validated class object.
            
        Raises:
            EntryPointResolutionError: Module or class resolution failed, or object is not a class.
            InterfaceComplianceError: Class does not implement ITrackingAlgorithm or is abstract.
        """
        mod_name, cls_name = manifest.parse_entry_point()

        # Locate the module file within plugin_dir
        parts = mod_name.split(".")
        candidate_file = plugin_dir.joinpath(*parts).with_suffix(".py")
        candidate_pkg = plugin_dir.joinpath(*parts, "__init__.py")

        file_path: Optional[Path] = None
        if candidate_file.is_file():
            file_path = candidate_file
        elif candidate_pkg.is_file():
            file_path = candidate_pkg

        if file_path is None:
            raise EntryPointResolutionError(
                f"Module '{mod_name}' not found in plugin directory '{plugin_dir.name}'. "
                f"Looked for '{candidate_file.name}' or package '__init__.py'.",
                plugin_name=manifest.name,
                plugin_dir=plugin_dir
            )

        # Ensure plugin directory is in sys.path so local imports within the plugin resolve
        dir_str = str(plugin_dir.resolve())
        path_inserted = False
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)
            path_inserted = True

        # Use a unique module name to avoid collision across plugins with identical file names
        sanitized_name = "".join(c if c.isalnum() or c == "_" else "_" for c in manifest.name)
        sanitized_mod = mod_name.replace(".", "_")
        unique_mod_name = f"_lumitrack_plugin_{sanitized_name}_{sanitized_mod}"

        try:
            spec = importlib.util.spec_from_file_location(unique_mod_name, file_path)
            if spec is None or spec.loader is None:
                raise EntryPointResolutionError(
                    f"Failed to create module spec for '{mod_name}' from '{file_path.name}'",
                    plugin_name=manifest.name,
                    plugin_dir=plugin_dir
                )

            module = importlib.util.module_from_spec(spec)
            sys.modules[unique_mod_name] = module
            spec.loader.exec_module(module)

        except EntryPointResolutionError:
            raise
        except Exception as e:
            sys.modules.pop(unique_mod_name, None)
            raise EntryPointResolutionError(
                f"Failed to import/execute module '{mod_name}' for plugin '{manifest.name}': {e}",
                plugin_name=manifest.name,
                plugin_dir=plugin_dir,
                cause=e
            ) from e
        finally:
            if path_inserted and dir_str in sys.path:
                try:
                    sys.path.remove(dir_str)
                except ValueError:
                    pass

        # Case: Missing class/attribute in module
        if not hasattr(module, cls_name):
            raise EntryPointResolutionError(
                f"Module '{mod_name}' does not define attribute '{cls_name}' for plugin '{manifest.name}'",
                plugin_name=manifest.name,
                plugin_dir=plugin_dir
            )

        obj = getattr(module, cls_name)

        # Case: Resolved object is not a class (function, instance, variable, etc.)
        if not isinstance(obj, type):
            raise EntryPointResolutionError(
                f"Entry point target '{cls_name}' in module '{mod_name}' is not a class (got {type(obj).__name__})",
                plugin_name=manifest.name,
                plugin_dir=plugin_dir
            )

        # Case: Class does not implement ITrackingAlgorithm
        if not issubclass(obj, ITrackingAlgorithm):
            raise InterfaceComplianceError(
                f"Class '{cls_name}' in plugin '{manifest.name}' does not implement ITrackingAlgorithm",
                plugin_name=manifest.name,
                plugin_dir=plugin_dir
            )

        # Case: Abstract class with unimplemented abstract methods
        if inspect.isabstract(obj):
            unimplemented = sorted(list(getattr(obj, "__abstractmethods__", set())))
            raise InterfaceComplianceError(
                f"Class '{cls_name}' in plugin '{manifest.name}' is abstract and cannot be instantiated. "
                f"Unimplemented abstract methods: {unimplemented}",
                plugin_name=manifest.name,
                plugin_dir=plugin_dir
            )

        return obj

    def instantiate_algorithm(
        self,
        algorithm_class: Type[ITrackingAlgorithm],
        plugin_name: Optional[str] = None,
        plugin_dir: Optional[Path] = None
    ) -> ITrackingAlgorithm:
        """
        Instantiates an algorithm class using its parameterless constructor.
        
        Args:
            algorithm_class: Validated class implementing ITrackingAlgorithm.
            plugin_name: Optional plugin name for error reporting.
            plugin_dir: Optional plugin directory for error reporting.
            
        Returns:
            Instantiated ITrackingAlgorithm object.
            
        Raises:
            PluginInstantiationError: If the constructor requires arguments or raises an exception.
        """
        try:
            instance = algorithm_class()
            return instance
        except TypeError as e:
            raise PluginInstantiationError(
                f"Failed to instantiate algorithm '{algorithm_class.__name__}' for plugin '{plugin_name}': "
                f"Constructor signature error (algorithms must support parameterless instantiation): {e}",
                plugin_name=plugin_name,
                plugin_dir=plugin_dir,
                cause=e
            ) from e
        except Exception as e:
            raise PluginInstantiationError(
                f"Failed to instantiate algorithm '{algorithm_class.__name__}' for plugin '{plugin_name}': "
                f"Constructor raised an unexpected exception: {e}",
                plugin_name=plugin_name,
                plugin_dir=plugin_dir,
                cause=e
            ) from e

    def load_plugin(self, plugin_name: str) -> LoadedPlugin:
        """
        Loads and instantiates a specific discovered plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load.
            
        Returns:
            LoadedPlugin containing manifest, directory, class, and initialized instance.
            
        Raises:
            PluginLoadError: If plugin was not discovered, has unresolved errors, or failed instantiation.
        """
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]

        if plugin_name not in self.discovered_plugins:
            # Check if it was recorded as a failure
            matching_failures = [f for f in self.failures if f.plugin_name == plugin_name]
            if matching_failures:
                fail = matching_failures[0]
                if fail.exception and isinstance(fail.exception, PluginLoadError):
                    raise fail.exception
                raise PluginLoadError(
                    f"Plugin '{plugin_name}' failed during discovery: {fail.message}",
                    plugin_name=plugin_name,
                    plugin_dir=fail.plugin_dir
                )
            raise PluginLoadError(
                f"Plugin '{plugin_name}' was not discovered in '{self.plugins_dir}'.",
                plugin_name=plugin_name
            )

        discovered = self.discovered_plugins[plugin_name]

        # Resolve algorithm class if not already resolved
        algorithm_class = discovered.algorithm_class
        if algorithm_class is None:
            algorithm_class = self.resolve_entry_point(discovered.manifest, discovered.plugin_dir)
            discovered.algorithm_class = algorithm_class

        # Instantiate algorithm instance
        instance = self.instantiate_algorithm(
            algorithm_class,
            plugin_name=discovered.name,
            plugin_dir=discovered.plugin_dir
        )

        loaded = LoadedPlugin(
            manifest=discovered.manifest,
            plugin_dir=discovered.plugin_dir,
            algorithm_class=algorithm_class,
            instance=instance
        )
        self.loaded_plugins[plugin_name] = loaded
        return loaded

    def load_all(self) -> Tuple[Dict[str, LoadedPlugin], List[PluginFailure]]:
        """
        Loads and instantiates all discovered valid plugins.
        
        Returns:
            Tuple of (dict of loaded plugins, list of all failures encountered).
        """
        if not self.discovered_plugins and not self.failures:
            self.discover()

        for name in list(self.discovered_plugins.keys()):
            if name not in self.loaded_plugins:
                try:
                    self.load_plugin(name)
                except PluginLoadError as e:
                    failure = PluginFailure(
                        plugin_name=name,
                        plugin_dir=self.discovered_plugins[name].plugin_dir,
                        error_type=type(e).__name__,
                        message=str(e),
                        exception=e
                    )
                    self.failures.append(failure)

        return dict(self.loaded_plugins), list(self.failures)

    def get_plugin(self, name: str) -> Optional[LoadedPlugin]:
        """Returns loaded plugin by name if loaded, else None."""
        return self.loaded_plugins.get(name)

    def get_discovered(self, name: str) -> Optional[DiscoveredPlugin]:
        """Returns discovered plugin by name if discovered, else None."""
        return self.discovered_plugins.get(name)

    def get_failures(self) -> List[PluginFailure]:
        """Returns list of all discovery and loading failures."""
        return list(self.failures)

    def get_ignored(self) -> List[Path]:
        """Returns list of harmless non-plugin directories encountered."""
        return list(self.ignored_dirs)

    def is_plugin_available(self, name: str) -> bool:
        """Returns True if the plugin was successfully discovered and validated."""
        return name in self.discovered_plugins
