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
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import DaichiDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class DaichiTemperatureSensor(CoordinatorEntity[DaichiDataUpdateCoordinator], SensorEntity):
    """Representation of a Daichi outdoor/indoor temperature sensor."""

    _attr_has_entity_name = True
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
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_data = device_data
        self._sensor_type = sensor_type  # "indoor" or "outdoor"
        
        # Set unique ID
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{sensor_type}_temp"
        
        # Set name based on sensor type
        if sensor_type == "outdoor":
            self._attr_name = "Outdoor Temperature"
            self._attr_translation_key = "outdoor_temperature"
        else:
            self._attr_name = "Indoor Temperature"
            self._attr_translation_key = "indoor_temperature"
        
        # Set device info (link to main device)
        device_name = device_data.get("title") or device_data.get("name") or f"Daichi {device_id}"
        device_info_data = device_data.get("deviceInfo", {})
        model_parts = []
        if device_info_data.get("brand"):
            model_parts.append(device_info_data["brand"])
        if device_info_data.get("model"):
            model_parts.append(device_info_data["model"])
        model = " ".join(model_parts) if model_parts else device_data.get("serial") or "Unknown"
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device_id))},
            name=device_name,
            manufacturer=device_info_data.get("brand") or "Daichi",
            model=model,
        )

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        if not self.coordinator.data:
            return None
            
        device_data = self.coordinator.data.get(self._device_id, {})
        if not device_data:
            return None
        
        if self._sensor_type == "outdoor":
            # Try to get outdoor temperature from various sources
            outdoor_temp = device_data.get("outdoorTemp") or device_data.get("outdoor_temp")
            if outdoor_temp is not None:
                try:
                    return float(outdoor_temp)
                except (ValueError, TypeError):
                    pass
            
            # Try from state info
            state = device_data.get("state", {})
            info = state.get("info", {})
            outdoor_text = info.get("outdoorTemp")
            if outdoor_text:
                try:
                    return float("".join(filter(lambda x: x.isdigit() or x == "-", str(outdoor_text).split("°")[0])))
                except (ValueError, TypeError):
                    pass
        else:
            # Indoor temperature
            cur_temp = device_data.get("curTemp")
            if cur_temp is not None:
                try:
                    return float(cur_temp)
                except (ValueError, TypeError):
                    pass
            
            # Try currentStateDetailed
            current_state_detailed = device_data.get("currentStateDetailed", [])
            if current_state_detailed and len(current_state_detailed) > 0:
                temp_text = current_state_detailed[0].get("text", "")
                if temp_text:
                    try:
                        return float("".join(filter(str.isdigit, temp_text.split("°")[0])))
                    except (ValueError, TypeError):
                        pass
        
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        
        if not self.coordinator.data:
            return False
        
        device_data = self.coordinator.data.get(self._device_id)
        if not device_data:
            return False
        
        # Check if device is connected
        status = device_data.get("status", "").lower()
        if status == "disconnected":
            return False
        
        return True


class DaichiHumiditySensor(CoordinatorEntity[DaichiDataUpdateCoordinator], SensorEntity):
    """Representation of a Daichi humidity sensor."""

    _attr_has_entity_name = True
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
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_data = device_data
        
        # Set unique ID
        self._attr_unique_id = f"{DOMAIN}_{device_id}_humidity"
        
        # Set device info (link to main device)
        device_name = device_data.get("title") or device_data.get("name") or f"Daichi {device_id}"
        device_info_data = device_data.get("deviceInfo", {})
        model_parts = []
        if device_info_data.get("brand"):
            model_parts.append(device_info_data["brand"])
        if device_info_data.get("model"):
            model_parts.append(device_info_data["model"])
        model = " ".join(model_parts) if model_parts else device_data.get("serial") or "Unknown"
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device_id))},
            name=device_name,
            manufacturer=device_info_data.get("brand") or "Daichi",
            model=model,
        )

    @property
    def native_value(self) -> float | None:
        """Return the humidity value."""
        if not self.coordinator.data:
            return None
            
        device_data = self.coordinator.data.get(self._device_id, {})
        if not device_data:
            return None
        
        # Try direct humidity field
        humidity = device_data.get("humidity") or device_data.get("curHumidity")
        if humidity is not None:
            try:
                return float(humidity)
            except (ValueError, TypeError):
                pass
        
        # Try from currentStateDetailed (might have humidity info)
        current_state_detailed = device_data.get("currentStateDetailed", [])
        for item in current_state_detailed:
            text = item.get("text", "")
            if "%" in text and "°" not in text:
                try:
                    return float("".join(filter(str.isdigit, text.replace("%", ""))))
                except (ValueError, TypeError):
                    pass
        
        # Try from state info
        state = device_data.get("state", {})
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
        
        if not self.coordinator.data:
            return False
        
        device_data = self.coordinator.data.get(self._device_id)
        if not device_data:
            return False
        
        # Check if device is connected
        status = device_data.get("status", "").lower()
        if status == "disconnected":
            return False
        
        # Check if humidity data is available
        return self.native_value is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daichi sensor entities from a config entry."""
    coordinator: DaichiDataUpdateCoordinator = entry.runtime_data
    
    # Wait for initial data if not available
    if coordinator.data is None:
        await coordinator.async_request_refresh()
    
    entities = []
    for device_id, device_data in (coordinator.data or {}).items():
        # Always add indoor temperature sensor
        entities.append(
            DaichiTemperatureSensor(coordinator, str(device_id), device_data, "indoor")
        )
        
        # Add outdoor temperature sensor if data is available
        outdoor_temp = device_data.get("outdoorTemp") or device_data.get("outdoor_temp")
        if outdoor_temp is not None:
            entities.append(
                DaichiTemperatureSensor(coordinator, str(device_id), device_data, "outdoor")
            )
        
        # Add humidity sensor if data is available
        humidity = device_data.get("humidity") or device_data.get("curHumidity")
        if humidity is not None:
            entities.append(
                DaichiHumiditySensor(coordinator, str(device_id), device_data)
            )
    
    async_add_entities(entities, update_before_add=True)

