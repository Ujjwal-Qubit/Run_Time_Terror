"""
Scenario Manager — Module 3 per Architecture v1.2.

Manages loading, saving, and selecting simulation scenarios.
A scenario is a complete SystemConfig snapshot that can be
replayed for reproducible experiments.

Phase 5.1 provides the interface and file-based load/save.
Full scenario library is built incrementally during later phases.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from src.config.config_manager import ConfigManager, SystemConfig


class ScenarioManager:
    """
    Scenario Manager — Module 3.

    Responsibilities:
      - Load scenario from JSON file
      - Save current config as a scenario
      - List available scenarios in a directory
      - Provide scenario metadata (name, description)
    """

    def __init__(self, scenario_dir: str = "scenarios") -> None:
        self._scenario_dir = self._resolve_scenario_dir(scenario_dir)
        os.makedirs(self._scenario_dir, exist_ok=True)

    @staticmethod
    def _resolve_scenario_dir(scenario_dir: str) -> str:
        candidates = [
            scenario_dir,
        ]
        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(getattr(sys, "_MEIPASS"), scenario_dir))
        if hasattr(sys, "executable"):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            candidates.append(os.path.join(exe_dir, scenario_dir))
            candidates.append(os.path.join(exe_dir, "_internal", scenario_dir))
        module_root = Path(__file__).resolve().parents[2]
        candidates.append(str(module_root / scenario_dir))

        for cand in candidates:
            if os.path.isdir(cand) and any(f.endswith(".json") for f in os.listdir(cand)):
                return cand
        return scenario_dir

    def list_scenarios(self) -> List[str]:
        """List available scenario files."""
        if not os.path.isdir(self._scenario_dir):
            return []
        return [
            f[:-5]  # strip .json
            for f in os.listdir(self._scenario_dir)
            if f.endswith(".json")
        ]

    def load_scenario(
        self, name: str, config_manager: ConfigManager
    ) -> None:
        """Load a named scenario into the ConfigManager."""
        if os.path.isfile(name):
            path = name
        elif name.endswith(".json"):
            path = os.path.join(self._scenario_dir, name)
        else:
            path = os.path.join(self._scenario_dir, f"{name}.json")
            if not os.path.isfile(path) and os.path.isdir(self._scenario_dir):
                for f in os.listdir(self._scenario_dir):
                    if f.endswith(".json") and name.lower() in f.lower():
                        path = os.path.join(self._scenario_dir, f)
                        break
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Scenario not found: {path}")
        config_manager.load_from_file(path)

    def save_scenario(
        self, name: str, config_manager: ConfigManager
    ) -> None:
        """Save the current configuration as a named scenario."""
        path = os.path.join(self._scenario_dir, f"{name}.json")
        config_manager.save_to_file(path)

    def get_scenario_dir(self) -> str:
        return self._scenario_dir
