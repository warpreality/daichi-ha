"""Base entity for Daichi integration."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DaichiDataUpdateCoordinator


def parse_temperature(text: str) -> float | None:
    """Parse temperature from text like '21°', '-5°C', '26°C'."""
    if not text:
        return None
    try:
        raw = text.split("°")[0].strip()
        return float(raw)
    except (ValueError, TypeError, IndexError):
        return None


def build_device_info(device_id: str, device_data: dict[str, Any]) -> DeviceInfo:
    """Build DeviceInfo from device data."""
    device_name = (
        device_data.get("title")
        or device_data.get("name")
        or f"Daichi {device_id}"
    )
    device_info_data = device_data.get("deviceInfo", {})
    model_parts = []
    if device_info_data.get("brand"):
        model_parts.append(device_info_data["brand"])
    if device_info_data.get("model"):
        model_parts.append(device_info_data["model"])
    model = (
        " ".join(model_parts)
        if model_parts
        else device_data.get("serial") or "Unknown"
    )
    return DeviceInfo(
        identifiers={(DOMAIN, str(device_id))},
        name=device_name,
        manufacturer=device_info_data.get("brand") or "Daichi",
        model=model,
        serial_number=device_data.get("serial"),
    )


class DaichiEntity(CoordinatorEntity[DaichiDataUpdateCoordinator]):
    """Base class for all Daichi entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DaichiDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_info = build_device_info(device_id, device_data)

    @property
    def device_data(self) -> dict[str, Any]:
        """Return current device data from coordinator."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get(self._device_id, {})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available or not self.coordinator.data:
            return False
        device_data = self.coordinator.data.get(self._device_id)
        if not device_data:
            return False
        if device_data.get("status", "").lower() == "disconnected":
            return False
        return True
