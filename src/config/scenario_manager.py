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
        self._scenario_dir = scenario_dir
        os.makedirs(self._scenario_dir, exist_ok=True)

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
        path = os.path.join(self._scenario_dir, f"{name}.json")
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
