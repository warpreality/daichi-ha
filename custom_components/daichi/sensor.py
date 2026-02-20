"""Sensor platform for Daichi integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DaichiDataUpdateCoordinator
from .entity import DaichiEntity, parse_temperature

_LOGGER = logging.getLogger(__name__)


class DaichiTemperatureSensor(DaichiEntity, SensorEntity):
    """Representation of a Daichi outdoor/indoor temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: DaichiDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
        sensor_type: str,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator, device_id, device_data)
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{sensor_type}_temp"

        if sensor_type == "outdoor":
            self._attr_name = "Outdoor Temperature"
            self._attr_translation_key = "outdoor_temperature"
        else:
            self._attr_name = "Indoor Temperature"
            self._attr_translation_key = "indoor_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        dd = self.device_data
        if not dd:
            return None

        if self._sensor_type == "outdoor":
            outdoor_temp = dd.get("outdoorTemp") or dd.get("outdoor_temp")
            if outdoor_temp is not None:
                try:
                    return float(outdoor_temp)
                except (ValueError, TypeError):
                    pass

            state = dd.get("state", {})
            info = state.get("info", {})
            temp = parse_temperature(str(info.get("outdoorTemp", "")))
            if temp is not None:
                return temp
        else:
            cur_temp = dd.get("curTemp")
            if cur_temp is not None:
                try:
                    return float(cur_temp)
                except (ValueError, TypeError):
                    pass

            current_state_detailed = dd.get("currentStateDetailed", [])
            if current_state_detailed:
                temp = parse_temperature(current_state_detailed[0].get("text", ""))
                if temp is not None:
                    return temp

        return None


class DaichiHumiditySensor(DaichiEntity, SensorEntity):
    """Representation of a Daichi humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Humidity"
    _attr_translation_key = "humidity"

    def __init__(
        self,
        coordinator: DaichiDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the humidity sensor entity."""
        super().__init__(coordinator, device_id, device_data)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_humidity"

    @property
    def native_value(self) -> float | None:
        """Return the humidity value."""
        dd = self.device_data
        if not dd:
            return None

        humidity = dd.get("humidity") or dd.get("curHumidity")
        if humidity is not None:
            try:
                return float(humidity)
            except (ValueError, TypeError):
                pass

        current_state_detailed = dd.get("currentStateDetailed", [])
        for item in current_state_detailed:
            text = item.get("text", "")
            if "%" in text and "\u00b0" not in text:
                try:
                    return float("".join(filter(str.isdigit, text.replace("%", ""))))
                except (ValueError, TypeError):
                    pass

        state = dd.get("state", {})
        info = state.get("info", {})
        humidity_text = info.get("humidity")
        if humidity_text:
            try:
                return float("".join(filter(str.isdigit, str(humidity_text).replace("%", ""))))
            except (ValueError, TypeError):
                pass

        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        return self.native_value is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daichi sensor entities from a config entry."""
    coordinator: DaichiDataUpdateCoordinator = entry.runtime_data

    if coordinator.data is None:
        await coordinator.async_request_refresh()

    entities: list[SensorEntity] = []
    for device_id, device_data in (coordinator.data or {}).items():
        entities.append(
            DaichiTemperatureSensor(coordinator, str(device_id), device_data, "indoor")
        )

        outdoor_temp = device_data.get("outdoorTemp") or device_data.get("outdoor_temp")
        if outdoor_temp is not None:
            entities.append(
                DaichiTemperatureSensor(coordinator, str(device_id), device_data, "outdoor")
            )

        humidity = device_data.get("humidity") or device_data.get("curHumidity")
        if humidity is not None:
            entities.append(
                DaichiHumiditySensor(coordinator, str(device_id), device_data)
            )

    async_add_entities(entities, update_before_add=True)
