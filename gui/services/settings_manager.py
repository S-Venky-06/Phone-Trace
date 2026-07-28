"""
PhoneTrace -- Settings Manager
================================

Persists user preferences to a JSON file.
Provides defaults for all configurable options.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("gui.settings")

_DEFAULTS: Dict[str, Any] = {
    "timezone": "Asia/Kolkata",
    "theme": "dark",
    "export_folder": "",
    "logging_level": "INFO",
    "session_gap_minutes": 15,
    "correlation_time_window": 15,
    "gps_movement_threshold_km": 0.5,
    "location_proximity_m": 200.0,
    "communication_cluster_minutes": 10,
    "window_width": 1400,
    "window_height": 850,
    "ai_provider": "rule_based",
    "ai_api_key": "",
    "ai_ollama_url": "http://localhost:11434",
    "ai_model": "",
}

_SETTINGS_FILE = "settings.json"


class SettingsManager:
    """Read / write application settings from a JSON file.

    Args:
        project_root: Root directory of the project (settings file lives here).
    """

    def __init__(self, project_root: str | Path | None = None) -> None:
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent.parent
        self._path = Path(project_root) / _SETTINGS_FILE
        self._data: Dict[str, Any] = dict(_DEFAULTS)
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value (does NOT auto-save)."""
        self._data[key] = value

    def save(self) -> None:
        """Persist current settings to disk."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.info("Settings saved to %s", self._path)
        except OSError as exc:
            logger.error("Failed to save settings: %s", exc)

    def reset(self) -> None:
        """Reset all settings to defaults."""
        self._data = dict(_DEFAULTS)
        self.save()

    @property
    def all_settings(self) -> Dict[str, Any]:
        """Return a copy of all current settings."""
        return dict(self._data)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load settings from disk, falling back to defaults."""
        if self._path.is_file():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                # Merge with defaults (so new keys get defaults)
                for key, default_val in _DEFAULTS.items():
                    self._data[key] = stored.get(key, default_val)
                logger.info("Settings loaded from %s", self._path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not load settings: %s", exc)
                self._data = dict(_DEFAULTS)
        else:
            self._data = dict(_DEFAULTS)
