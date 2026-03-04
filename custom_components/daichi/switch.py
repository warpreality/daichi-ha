"""Switch platform for Daichi integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FUNCTION_ID_SOUND_OFF
from .coordinator import DaichiDataUpdateCoordinator
from .entity import DaichiEntity

_LOGGER = logging.getLogger(__name__)


def _device_has_function(device_data: dict[str, Any], function_id: int) -> bool:
    """Check if device supports the given function ID."""
    for section in device_data.get("pult", []):
        for func in section.get("functions", []):
            if func.get("id") == function_id:
                return True
    return False


def _get_function_state(device_data: dict[str, Any], function_id: int) -> bool:
    """Get isOn state for a toggle function from device pult."""
    for section in device_data.get("pult", []):
        for func in section.get("functions", []):
            if func.get("id") == function_id:
                return bool(func.get("state", {}).get("isOn", False))
    return False


class DaichiSoundOffSwitch(DaichiEntity, SwitchEntity):
    """Переключатель функции 365 — звук (тихий режим). Вкл = звук выключен."""

    _attr_translation_key = "sound_off"

    def __init__(
        self,
        coordinator: DaichiDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the sound off switch."""
        super().__init__(coordinator, device_id, device_data)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_sound_off"

    @property
    def is_on(self) -> bool:
        """Return True if sound is off (silent mode)."""
        return _get_function_state(self.device_data, FUNCTION_ID_SOUND_OFF)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn sound off (enable silent mode)."""
        try:
            await self.coordinator.async_control_device_with_retry(
                int(self._device_id), FUNCTION_ID_SOUND_OFF, True
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to turn on sound off for device %s: %s",
                self._device_id,
                err,
            )
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn sound on (disable silent mode)."""
        try:
            await self.coordinator.async_control_device_with_retry(
                int(self._device_id), FUNCTION_ID_SOUND_OFF, False
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to turn off sound off for device %s: %s",
                self._device_id,
                err,
            )
            raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daichi switch entities from a config entry."""
    coordinator: DaichiDataUpdateCoordinator = entry.runtime_data

    if coordinator.data is None:
        await coordinator.async_request_refresh()

    entities: list[SwitchEntity] = []
    for device_id, device_data in (coordinator.data or {}).items():
        if _device_has_function(device_data, FUNCTION_ID_SOUND_OFF):
            entities.append(
                DaichiSoundOffSwitch(coordinator, str(device_id), device_data)
            )

    async_add_entities(entities, update_before_add=True)
