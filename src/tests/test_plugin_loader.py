"""
Tests for PluginLoader Subsystem (Phase 6.2)

Verifies:
1. Deterministic and visible discovery failures.
2. Safe entry-point validation handling all non-class, missing, and abstract edge cases.
3. Isolated test fixtures using pytest `tmp_path`.
4. Backward compatibility and complete isolation from production runtime.
"""

import json
from pathlib import Path
import pytest
import numpy as np

from src.api.v1 import API_VERSION, ITrackingAlgorithm, FramePacket, TrackingResult
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
from src.plugins.loader import PluginLoader
from src.plugins.models import DiscoveryResult, PluginFailure, PluginManifest


def _write_plugin(
    plugin_dir: Path,
    manifest_data: dict,
    code: str,
    file_name: str = "tracker.py"
) -> Path:
    """Helper to write a plugin into an isolated directory."""
    plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = plugin_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    code_path = plugin_dir / file_name
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)

    return plugin_dir


# --- 1. Default Directory & Empty State ---

def test_loader_default_directory():
    """Default directory should point to src/plugins/algorithms and handle empty state cleanly."""
    loader = PluginLoader()
    assert loader.plugins_dir.name == "algorithms"
    assert loader.plugins_dir.parent.name == "plugins"
    result = loader.discover()
    assert isinstance(result, DiscoveryResult)
    assert len(loader.failures) == 0


def test_loader_nonexistent_directory(tmp_path):
    """A non-existent plugins directory should return an empty DiscoveryResult without crashing."""
    non_existent = tmp_path / "does_not_exist"
    loader = PluginLoader(plugins_dir=non_existent)
    result = loader.discover()
    assert len(result) == 0
    assert len(loader.failures) == 0
    assert len(loader.ignored_dirs) == 0


# --- 2. Valid Plugin Discovery & Lifecycle Execution ---

VALID_TRACKER_CODE = """
from src.api.v1 import ITrackingAlgorithm, FramePacket, TrackingResult

class ValidTracker(ITrackingAlgorithm):
    def __init__(self):
        self.initialized = False
        self.frame_count = 0

    def initialize(self, config: dict) -> bool:
        self.initialized = True
        return True

    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        self.frame_count += 1
        return TrackingResult(
            algorithm_is_tracking=True,
            centroid_x=320.0,
            centroid_y=240.0,
            confidence=0.95,
            roi=(310, 230, 20, 20)
        )

    def reset(self) -> None:
        self.frame_count = 0
"""

def test_valid_plugin_discovery_and_lifecycle(tmp_path):
    """Tests discovery, loading, and full lifecycle execution of a valid plugin."""
    plugin_dir = tmp_path / "valid_plugin"
    manifest = {
        "name": "ValidTrackerPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:ValidTracker",
        "description": "A valid test tracker",
        "author": "SIH Evaluator",
        "dependencies": ["numpy"]
    }
    _write_plugin(plugin_dir, manifest, VALID_TRACKER_CODE)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 1
    assert "ValidTrackerPlugin" in result
    assert len(loader.failures) == 0
    assert len(loader.ignored_dirs) == 0

    # Test load_plugin
    loaded = loader.load_plugin("ValidTrackerPlugin")
    assert loaded.manifest.name == "ValidTrackerPlugin"
    assert loaded.algorithm_class.__name__ == "ValidTracker"
    assert isinstance(loaded.instance, ITrackingAlgorithm)

    # Test algorithm lifecycle execution
    init_ok = loaded.instance.initialize({"param": 42})
    assert init_ok is True

    frame = FramePacket(
        image=np.zeros((480, 640), dtype=np.uint8),
        timestamp=0.033,
        frame_number=1,
        resolution=(640, 480),
        fov=(10.0, 7.5)
    )
    tracking_res = loaded.instance.process_frame(frame)
    assert tracking_res.algorithm_is_tracking is True
    assert tracking_res.centroid_x == 320.0
    assert tracking_res.confidence == 0.95

    loaded.instance.reset()
    assert loaded.instance.frame_count == 0


# --- 3. Deterministic Discovery Order ---

def test_deterministic_discovery_order(tmp_path):
    """Plugins must be discovered in deterministic alphabetical order by directory name."""
    names = ["zeta_tracker", "alpha_tracker", "beta_tracker"]
    for name in names:
        p_dir = tmp_path / name
        manifest = {
            "name": f"Plugin_{name}",
            "version": "1.0.0",
            "api_version": API_VERSION,
            "entry_point": "tracker:ValidTracker"
        }
        _write_plugin(p_dir, manifest, VALID_TRACKER_CODE)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()
    assert len(result) == 3

    # Verification of alphabetical discovery order
    discovered_list = list(result)
    discovered_dir_names = [p.plugin_dir.name for p in discovered_list]
    assert discovered_dir_names == ["alpha_tracker", "beta_tracker", "zeta_tracker"]


# --- 4. Harmless Ignored Directories (Review Correction 1) ---

def test_harmless_directories_ignored_without_failures(tmp_path):
    """Directories without manifest.json must be recorded as ignored, not as failures."""
    # 1. Non-plugin normal directory
    docs_dir = tmp_path / "documentation"
    docs_dir.mkdir()
    (docs_dir / "notes.txt").write_text("just notes", encoding="utf-8")

    # 2. Hidden / cache directory
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()

    # 3. Valid plugin
    plugin_dir = tmp_path / "valid_tracker"
    manifest = {
        "name": "MyValidTracker",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:ValidTracker"
    }
    _write_plugin(plugin_dir, manifest, VALID_TRACKER_CODE)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 1
    assert "MyValidTracker" in result
    assert len(loader.failures) == 0
    assert len(loader.ignored_dirs) == 1
    assert loader.ignored_dirs[0].name == "documentation"


# --- 5. Manifest Parsing & Validation Failures ---

def test_malformed_manifest_json(tmp_path):
    """Malformed JSON in manifest.json must produce a ManifestParseError in failures."""
    bad_dir = tmp_path / "bad_json_plugin"
    bad_dir.mkdir()
    (bad_dir / "manifest.json").write_text("{ unclosed json: true, ", encoding="utf-8")

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == 1
    fail = loader.failures[0]
    assert fail.error_type == "ManifestParseError"
    assert "Failed to parse JSON" in fail.message
    assert fail.plugin_dir == bad_dir


def test_manifest_missing_required_fields(tmp_path):
    """Missing required fields in manifest.json must produce ManifestValidationError."""
    required = ["name", "version", "api_version", "entry_point"]
    for missing_field in required:
        p_dir = tmp_path / f"missing_{missing_field}"
        data = {
            "name": "TestPlugin",
            "version": "1.0.0",
            "api_version": API_VERSION,
            "entry_point": "tracker:ValidTracker"
        }
        del data[missing_field]
        p_dir.mkdir()
        (p_dir / "manifest.json").write_text(json.dumps(data), encoding="utf-8")

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == 4
    for fail in loader.failures:
        assert fail.error_type == "ManifestValidationError"
        assert "missing required field" in fail.message


def test_manifest_empty_or_invalid_field_types(tmp_path):
    """Empty strings or wrong types for manifest fields must be rejected."""
    cases = [
        ("empty_name", {"name": "  ", "version": "1.0.0", "api_version": API_VERSION, "entry_point": "t:T"}),
        ("int_version", {"name": "PluginA", "version": 100, "api_version": API_VERSION, "entry_point": "t:T"}),
        ("list_entry_point", {"name": "PluginB", "version": "1.0", "api_version": API_VERSION, "entry_point": ["t", "T"]}),
        ("bad_deps", {"name": "PluginC", "version": "1.0", "api_version": API_VERSION, "entry_point": "t:T", "dependencies": "not-a-list"}),
    ]

    for dir_name, manifest in cases:
        p_dir = tmp_path / dir_name
        p_dir.mkdir()
        (p_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == len(cases)
    for fail in loader.failures:
        assert fail.error_type == "ManifestValidationError"


# --- 6. API Version Enforcement ---

def test_unsupported_api_version(tmp_path):
    """Unsupported API version must produce UnsupportedApiVersionError in failures."""
    p_dir = tmp_path / "v2_plugin"
    manifest = {
        "name": "FutureTracker",
        "version": "1.0.0",
        "api_version": "v2",
        "entry_point": "tracker:ValidTracker"
    }
    _write_plugin(p_dir, manifest, VALID_TRACKER_CODE)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == 1
    fail = loader.failures[0]
    assert fail.error_type == "UnsupportedApiVersionError"
    assert "requires API version 'v2'" in fail.message
    assert "supports 'v1'" in fail.message


# --- 7. Duplicate Plugin Names ---

def test_duplicate_plugin_name_rejected(tmp_path):
    """Two plugins declaring the identical name must trigger DuplicatePluginError."""
    dir1 = tmp_path / "dir_one"
    manifest = {
        "name": "IdenticalName",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:ValidTracker"
    }
    _write_plugin(dir1, manifest, VALID_TRACKER_CODE)

    dir2 = tmp_path / "dir_two"
    _write_plugin(dir2, manifest, VALID_TRACKER_CODE)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    # One registered, the second duplicate flagged as failure
    assert len(result) == 1
    assert len(loader.failures) == 1
    fail = loader.failures[0]
    assert fail.error_type == "DuplicatePluginError"
    assert "Duplicate plugin name 'IdenticalName'" in fail.message


# --- 8. Entry Point Syntax Validation ---

def test_invalid_entry_point_syntax(tmp_path):
    """Malformed entry point syntax must raise ManifestValidationError."""
    bad_syntax = ["tracker", "tracker:ValidTracker:Extra", ":ValidTracker", "tracker:", "123bad:ValidTracker"]
    for i, entry in enumerate(bad_syntax):
        p_dir = tmp_path / f"syntax_{i}"
        manifest = {
            "name": f"SyntaxPlugin_{i}",
            "version": "1.0.0",
            "api_version": API_VERSION,
            "entry_point": entry
        }
        _write_plugin(p_dir, manifest, VALID_TRACKER_CODE)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == len(bad_syntax)
    for fail in loader.failures:
        assert fail.error_type == "ManifestValidationError"


# --- 9. Entry-Point Resolution & Safety (Review Correction 2) ---

def test_missing_module_file(tmp_path):
    """Entry point pointing to non-existent module file produces EntryPointResolutionError."""
    p_dir = tmp_path / "missing_module"
    manifest = {
        "name": "MissingModulePlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "nonexistent_file:ValidTracker"
    }
    p_dir.mkdir()
    (p_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == 1
    assert loader.failures[0].error_type == "EntryPointResolutionError"
    assert "not found in plugin directory" in loader.failures[0].message


def test_missing_attribute_in_module(tmp_path):
    """Entry point specifying a class name not in the module produces EntryPointResolutionError."""
    p_dir = tmp_path / "missing_attr"
    manifest = {
        "name": "MissingAttrPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:NonExistentClass"
    }
    _write_plugin(p_dir, manifest, VALID_TRACKER_CODE)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == 1
    fail = loader.failures[0]
    assert fail.error_type == "EntryPointResolutionError"
    assert "does not define attribute 'NonExistentClass'" in fail.message


def test_resolved_target_is_not_a_class(tmp_path):
    """Entry point resolving to a function, string, or non-class object must be caught cleanly."""
    code = """
from src.api.v1 import ITrackingAlgorithm

# Function instead of a class
def NotAClassTracker():
    return None

# String instead of a class
StringTarget = "just a string"
"""
    # Test function target
    p_dir1 = tmp_path / "func_target"
    manifest1 = {
        "name": "FuncTargetPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:NotAClassTracker"
    }
    _write_plugin(p_dir1, manifest1, code)

    # Test string target
    p_dir2 = tmp_path / "str_target"
    manifest2 = {
        "name": "StrTargetPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:StringTarget"
    }
    _write_plugin(p_dir2, manifest2, code)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == 2
    for fail in loader.failures:
        assert fail.error_type == "EntryPointResolutionError"
        assert "is not a class" in fail.message


def test_class_does_not_implement_itrackingalgorithm(tmp_path):
    """Class that does not inherit from ITrackingAlgorithm must raise InterfaceComplianceError."""
    code = """
class UnrelatedClass:
    def __init__(self):
        pass
"""
    p_dir = tmp_path / "unrelated_class"
    manifest = {
        "name": "UnrelatedClassPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:UnrelatedClass"
    }
    _write_plugin(p_dir, manifest, code)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == 1
    fail = loader.failures[0]
    assert fail.error_type == "InterfaceComplianceError"
    assert "does not implement ITrackingAlgorithm" in fail.message


def test_abstract_class_unimplemented_methods(tmp_path):
    """Class inheriting from ITrackingAlgorithm but missing abstract methods must be caught cleanly."""
    code = """
from src.api.v1 import ITrackingAlgorithm

class IncompleteTracker(ITrackingAlgorithm):
    # Only implements initialize, misses process_frame and reset
    def initialize(self, config: dict) -> bool:
        return True
"""
    p_dir = tmp_path / "abstract_class"
    manifest = {
        "name": "IncompletePlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:IncompleteTracker"
    }
    _write_plugin(p_dir, manifest, code)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 0
    assert len(loader.failures) == 1
    fail = loader.failures[0]
    assert fail.error_type == "InterfaceComplianceError"
    assert "is abstract and cannot be instantiated" in fail.message
    assert "process_frame" in fail.message
    assert "reset" in fail.message


def test_constructor_failure_handled(tmp_path):
    """Constructor requiring arguments or raising exceptions must raise PluginInstantiationError."""
    # Case 1: Constructor requiring argument
    code_req_arg = """
from src.api.v1 import ITrackingAlgorithm, FramePacket, TrackingResult

class ArgRequiringTracker(ITrackingAlgorithm):
    def __init__(self, required_arg):
        self.arg = required_arg

    def initialize(self, config: dict) -> bool:
        return True

    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        return TrackingResult(algorithm_is_tracking=False)

    def reset(self) -> None:
        pass
"""
    p_dir1 = tmp_path / "req_arg"
    manifest1 = {
        "name": "ReqArgPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:ArgRequiringTracker"
    }
    _write_plugin(p_dir1, manifest1, code_req_arg)

    # Case 2: Constructor throwing exception
    code_exploding = """
from src.api.v1 import ITrackingAlgorithm, FramePacket, TrackingResult

class ExplodingTracker(ITrackingAlgorithm):
    def __init__(self):
        raise RuntimeError("Fatal initialization hardware fault")

    def initialize(self, config: dict) -> bool:
        return True

    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        return TrackingResult(algorithm_is_tracking=False)

    def reset(self) -> None:
        pass
"""
    p_dir2 = tmp_path / "exploding"
    manifest2 = {
        "name": "ExplodingPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:ExplodingTracker"
    }
    _write_plugin(p_dir2, manifest2, code_exploding)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    # Both classes are valid subclasses of ITrackingAlgorithm (not abstract), so discovery succeeds
    assert len(result) == 2
    assert len(loader.failures) == 0

    # Instantiation must raise PluginInstantiationError
    with pytest.raises(PluginInstantiationError) as exc1:
        loader.load_plugin("ReqArgPlugin")
    assert "Constructor signature error" in str(exc1.value)

    with pytest.raises(PluginInstantiationError) as exc2:
        loader.load_plugin("ExplodingPlugin")
    assert "Fatal initialization hardware fault" in str(exc2.value)


# --- 10. Fault Isolation: Multiple Plugins with Mixed Health ---

def test_fault_isolation_multiple_mixed_plugins(tmp_path):
    """
    Verifies that one or more bad plugins do NOT crash discovery of valid plugins.
    Ensures visible diagnostics for all failures and clean tracking of ignored dirs.
    """
    # 1. Valid Plugin A
    _write_plugin(
        tmp_path / "valid_a",
        {"name": "ValidA", "version": "1.0", "api_version": API_VERSION, "entry_point": "tracker:ValidTracker"},
        VALID_TRACKER_CODE
    )

    # 2. Corrupt JSON manifest
    bad_json_dir = tmp_path / "broken_json"
    bad_json_dir.mkdir()
    (bad_json_dir / "manifest.json").write_text("{ unclosed", encoding="utf-8")

    # 3. Valid Plugin B
    _write_plugin(
        tmp_path / "valid_b",
        {"name": "ValidB", "version": "2.0", "api_version": API_VERSION, "entry_point": "tracker:ValidTracker"},
        VALID_TRACKER_CODE
    )

    # 4. Incompatible API version
    _write_plugin(
        tmp_path / "bad_api",
        {"name": "BadApi", "version": "1.0", "api_version": "v999", "entry_point": "tracker:ValidTracker"},
        VALID_TRACKER_CODE
    )

    # 5. Harmless directory without manifest
    harmless_dir = tmp_path / "shared_assets"
    harmless_dir.mkdir()
    (harmless_dir / "logo.png").write_bytes(b"\x89PNG")

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    # Exactly the 2 valid plugins discovered
    assert len(result) == 2
    assert "ValidA" in result
    assert "ValidB" in result

    # Exactly 2 failures recorded with explicit diagnostics
    assert len(result.failures) == 2
    error_types = {f.error_type for f in result.failures}
    assert "ManifestParseError" in error_types
    assert "UnsupportedApiVersionError" in error_types

    # Harmless directory recorded in ignored
    assert len(result.ignored) == 1
    assert result.ignored[0].name == "shared_assets"

    # Both valid plugins can be loaded and executed
    loaded_a = loader.load_plugin("ValidA")
    loaded_b = loader.load_plugin("ValidB")
    assert loaded_a.instance.initialize({}) is True
    assert loaded_b.instance.initialize({}) is True


# --- 11. Relative Imports and Plugin Local Dependencies ---

def test_plugin_local_imports(tmp_path):
    """Plugin must be able to import local helper modules within its directory."""
    plugin_dir = tmp_path / "plugin_with_helper"
    plugin_dir.mkdir()

    # Write local helper module
    helper_code = """
def get_roi():
    return (100, 100, 30, 30)
"""
    (plugin_dir / "helper.py").write_text(helper_code, encoding="utf-8")

    # Write main tracker importing helper
    tracker_code = """
import helper
from src.api.v1 import ITrackingAlgorithm, FramePacket, TrackingResult

class HelperTracker(ITrackingAlgorithm):
    def initialize(self, config: dict) -> bool:
        return True

    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        return TrackingResult(
            algorithm_is_tracking=True,
            centroid_x=115.0,
            centroid_y=115.0,
            confidence=0.88,
            roi=helper.get_roi()
        )

    def reset(self) -> None:
        pass
"""
    manifest = {
        "name": "HelperTrackerPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:HelperTracker"
    }
    _write_plugin(plugin_dir, manifest, tracker_code)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 1
    loaded = loader.load_plugin("HelperTrackerPlugin")
    assert loaded is not None

    frame = FramePacket(
        image=np.zeros((200, 200), dtype=np.uint8),
        timestamp=0.01,
        frame_number=1,
        resolution=(200, 200),
        fov=(5.0, 5.0)
    )
    res = loaded.instance.process_frame(frame)
    assert res.roi == (100, 100, 30, 30)


# --- 12. DiscoveryResult and Loader Helper Methods ---

def test_discovery_result_and_loader_helpers(tmp_path):
    """Verifies helper methods: len, in, get, load_all, is_plugin_available."""
    plugin_dir = tmp_path / "helper_test_plugin"
    manifest = {
        "name": "HelperTestPlugin",
        "version": "1.0.0",
        "api_version": API_VERSION,
        "entry_point": "tracker:ValidTracker"
    }
    _write_plugin(plugin_dir, manifest, VALID_TRACKER_CODE)

    loader = PluginLoader(plugins_dir=tmp_path)
    result = loader.discover()

    assert len(result) == 1
    assert "HelperTestPlugin" in result
    assert "NonExistent" not in result
    assert result.get("HelperTestPlugin") is not None
    assert result.get("NonExistent") is None
    assert result.has_failures is False

    assert loader.is_plugin_available("HelperTestPlugin") is True
    assert loader.is_plugin_available("NonExistent") is False

    loaded_dict, failures = loader.load_all()
    assert "HelperTestPlugin" in loaded_dict
    assert len(failures) == 0
    assert loader.get_plugin("HelperTestPlugin") is not None
    assert loader.get_discovered("HelperTestPlugin") is not None
