"""
Regression tests for F-SEC-02: Scenario Endpoint Path Traversal Hardening.

Verifies:
  1. Parent traversal attempts (../, ../../) are rejected with HTTP 400 across load, save, and delete.
  2. Nested directory separators (/ and \\) are rejected with HTTP 400.
  3. Absolute paths (drive letters, root slashes) are rejected with HTTP 400.
  4. Invalid characters (null bytes, colons, dotfiles) are rejected with HTTP 400.
  5. Valid scenario operations (load, save, delete, list) work correctly within an isolated sandbox.
  6. No filesystem operations escape the configured scenarios directory.
  7. Symlink containment checks prevent directory breakout even if symlinks exist.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi import HTTPException

from src.api.server import (
    load_scenario,
    save_scenario,
    delete_scenario,
    get_scenarios,
    ScenarioSaveRequest,
    _resolve_safe_scenario_path,
)


@pytest.fixture
def scenario_sandbox():
    """Provides an isolated temporary directory configured as the scenarios directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        resolved_tmp = Path(tmp_dir).resolve()
        with patch.dict(os.environ, {"LUMITRACK_SCENARIOS_DIR": str(resolved_tmp)}):
            yield resolved_tmp


def test_path_traversal_parent_directory_rejected(scenario_sandbox):
    """Verify ../ traversal strings are rejected across all scenario endpoints."""
    traversal_payloads = [
        "../../package.json",
        "../test.json",
        "..\\..\\package.json",
        "..\\test.json",
        "scenarios/../../secret.json",
        "foo/../bar.json",
    ]

    for payload in traversal_payloads:
        # Load
        with pytest.raises(HTTPException) as exc_load:
            load_scenario(payload)
        assert exc_load.value.status_code == 400
        assert exc_load.value.detail == "Invalid scenario name."

        # Save
        with pytest.raises(HTTPException) as exc_save:
            save_scenario(ScenarioSaveRequest(name=payload))
        assert exc_save.value.status_code == 400
        assert exc_save.value.detail == "Invalid scenario name."

        # Delete
        with pytest.raises(HTTPException) as exc_del:
            delete_scenario(payload)
        assert exc_del.value.status_code == 400
        assert exc_del.value.detail == "Invalid scenario name."


def test_absolute_paths_rejected(scenario_sandbox):
    """Verify absolute paths (POSIX and Windows) are rejected with HTTP 400."""
    abs_payloads = [
        "/etc/passwd",
        "/var/log/syslog",
        "C:\\Windows\\win.ini",
        "C:/Windows/win.ini",
        "D:\\data\\scenario.json",
        "\\system32\\drivers",
    ]

    for payload in abs_payloads:
        with pytest.raises(HTTPException) as exc_info:
            load_scenario(payload)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid scenario name."


def test_invalid_characters_and_dotfiles_rejected(scenario_sandbox):
    """Verify null bytes, colons, dotfiles, and empty names are rejected."""
    invalid_names = [
        "",
        "   ",
        ".",
        "..",
        ".hidden_scenario",
        "scenario\0null",
        "data:stream",
        "scenario name with spaces",
        "scenario;inject",
        "scenario|pipe",
        "scenario*wildcard",
    ]

    for name in invalid_names:
        with pytest.raises(HTTPException) as exc_info:
            load_scenario(name)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid scenario name."


def test_sandboxed_crud_lifecycle(scenario_sandbox):
    """Verify full CRUD lifecycle inside the isolated sandbox."""
    scenario_name = "test_matrix_valid_01"

    # 1. Initially empty
    scenarios_initial = get_scenarios()
    assert scenario_name not in scenarios_initial["scenarios"]
    assert f"{scenario_name}.json" not in scenarios_initial["scenarios"]

    # 2. Save scenario
    save_res = save_scenario(ScenarioSaveRequest(name=scenario_name))
    assert save_res["success"] is True
    assert save_res["scenario"] == f"{scenario_name}.json"

    # Verify physical containment: file exists only in sandbox
    expected_file = scenario_sandbox / f"{scenario_name}.json"
    assert expected_file.is_file(), f"File {expected_file} was not created in sandbox"

    # 3. List scenarios
    scenarios_list = get_scenarios()
    assert f"{scenario_name}.json" in scenarios_list["scenarios"]

    # 4. Load scenario
    load_res = load_scenario(scenario_name)
    assert load_res["success"] is True
    assert load_res["scenario"] == f"{scenario_name}.json"
    assert "config" in load_res

    # 5. Delete scenario
    del_res = delete_scenario(scenario_name)
    assert del_res["success"] is True
    assert not expected_file.exists(), "File should be unlinked after deletion"

    # 6. Load after delete raises 404
    with pytest.raises(HTTPException) as exc_404:
        load_scenario(scenario_name)
    assert exc_404.value.status_code == 404
    assert "not found" in exc_404.value.detail.lower()

    # 7. Delete non-existent raises 404
    with pytest.raises(HTTPException) as exc_del_404:
        delete_scenario(scenario_name)
    assert exc_del_404.value.status_code == 404


def test_symlink_breakout_prevented(scenario_sandbox):
    """Verify that symlinks resolving outside the sandbox are strictly blocked."""
    outside_dir = scenario_sandbox.parent / "canary_outside"
    outside_dir.mkdir(parents=True, exist_ok=True)
    canary_file = outside_dir / "target_secret.json"
    canary_file.write_text(json.dumps({"secret": "do_not_delete"}), encoding="utf-8")

    symlink_path = scenario_sandbox / "symlink_escape.json"
    can_symlink = False
    try:
        os.symlink(str(canary_file), str(symlink_path))
        can_symlink = True
    except (OSError, NotImplementedError):
        # On Windows without developer mode/admin rights, symlink creation is restricted
        pass

    if can_symlink:
        try:
            # Attempt load via symlink
            with pytest.raises(HTTPException) as exc_load:
                load_scenario("symlink_escape.json")
            assert exc_load.value.status_code == 400
            assert exc_load.value.detail == "Invalid scenario name."

            # Attempt delete via symlink
            with pytest.raises(HTTPException) as exc_del:
                delete_scenario("symlink_escape.json")
            assert exc_del.value.status_code == 400

            # Canary file outside must remain untouched
            assert canary_file.exists(), "Canary file outside sandbox was deleted!"
            assert "secret" in canary_file.read_text(encoding="utf-8")
        finally:
            if symlink_path.is_symlink() or symlink_path.exists():
                symlink_path.unlink()
            if canary_file.exists():
                canary_file.unlink()
            if outside_dir.exists():
                outside_dir.rmdir()
    else:
        # If OS prevents symlink creation (e.g. Windows without SeCreateSymbolicLinkPrivilege),
        # verify containment rejection when resolving an escaped symlink path
        escaped_path = canary_file.resolve()
        with patch("src.api.server.get_scenarios_dir", return_value=scenario_sandbox):
            with patch.object(Path, "resolve", return_value=escaped_path):
                with pytest.raises(HTTPException) as exc:
                    _resolve_safe_scenario_path("symlink_mock.json")
                assert exc.value.status_code == 400
                assert exc.value.detail == "Invalid scenario name."

        if canary_file.exists():
            canary_file.unlink()
        if outside_dir.exists():
            outside_dir.rmdir()
