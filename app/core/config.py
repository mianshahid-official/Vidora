"""
Global Configuration Management with reactivity.
"""

from typing import Callable, List
from app.database.repositories import SettingsRepository
from app.models.settings_model import AppSettings
from app.core.logger import logger


class ConfigManager:
    """Manages application-wide settings and change listeners."""

    def __init__(self):
        self._settings = SettingsRepository.load_settings()
        self._listeners: List[Callable[[AppSettings], None]] = []

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def update_settings(self, new_settings: AppSettings):
        self._settings = new_settings
        SettingsRepository.save_settings(new_settings)
        logger.log_app("Application settings updated and persisted.")
        self._notify()

    def add_listener(self, listener: Callable[[AppSettings], None]):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[AppSettings], None]):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify(self):
        for listener in self._listeners:
            try:
                listener(self._settings)
            except Exception as e:
                logger.log_error(f"Error in config listener: {e}")


# Global config instance
config_manager = ConfigManager()
