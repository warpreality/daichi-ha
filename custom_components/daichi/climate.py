"""Climate platform for Daichi integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    FUNCTION_ID_POWER,
    FUNCTION_ID_TEMPERATURE,
    FUNCTION_ID_COOL,
    FUNCTION_ID_HEAT,
    FUNCTION_ID_AUTO,
    FUNCTION_ID_DRY,
    FUNCTION_ID_FAN,
    FUNCTION_ID_FAN_SPEED_AUTO,
    FUNCTION_ID_FAN_SPEED,
    FUNCTION_ID_VERTICAL_SWING,
    FUNCTION_ID_HORIZONTAL_SWING,
    FUNCTION_ID_3D_SWING,
    FUNCTION_ID_ECO,
    FUNCTION_ID_TURBO,
    FUNCTION_ID_SLEEP,
    HVAC_MODE_TO_FUNCTION_ID,
    FAN_MODE_TO_FUNCTION_ID,
    PRESET_NONE,
    PRESET_ECO,
    PRESET_TURBO,
    PRESET_SLEEP,
    PRESET_MODE_TO_FUNCTION_ID,
    SWING_OFF,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
    SWING_BOTH,
    SWING_MODE_TO_FUNCTION_ID,
)
from .coordinator import DaichiDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Map Daichi modes to Home Assistant HVAC modes
DAICHI_TO_HA_MODE = {
    "cool": HVACMode.COOL,
    "heat": HVACMode.HEAT,
    "fan_only": HVACMode.FAN_ONLY,
    "dry": HVACMode.DRY,
    "auto": HVACMode.AUTO,
    "off": HVACMode.OFF,
}

HA_TO_DAICHI_MODE = {v: k for k, v in DAICHI_TO_HA_MODE.items()}


class DaichiClimateEntity(CoordinatorEntity[DaichiDataUpdateCoordinator], ClimateEntity):
    """Representation of a Daichi climate entity."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_min_temp = 16.0
    _attr_max_temp = 30.0
    _attr_target_temperature_step = 1.0

    def __init__(
        self,
        coordinator: DaichiDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_data = device_data
        
        # Set unique ID
        self._attr_unique_id = f"{DOMAIN}_{device_id}"
        
        # Set device info
        device_name = device_data.get("title") or device_data.get("name") or f"Daichi {device_id}"
        
        # Get model info from deviceInfo if available
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
            serial_number=device_data.get("serial"),
        )
        
        # Initialize state attributes
        self._attr_current_temperature: float | None = None
        self._attr_target_temperature: float | None = None
        self._attr_hvac_mode: HVACMode = HVACMode.OFF
        self._attr_hvac_modes: list[HVACMode] = [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.FAN_ONLY,
            HVACMode.DRY,
            HVACMode.AUTO,
        ]
        self._attr_fan_modes: list[str] = ["auto", "1", "2", "3", "4", "5"]
        self._attr_preset_modes: list[str] = [
            PRESET_NONE,
            PRESET_ECO,
            PRESET_TURBO,
            PRESET_SLEEP,
        ]
        self._attr_swing_modes: list[str] = [
            SWING_OFF,
            SWING_VERTICAL,
            SWING_HORIZONTAL,
            SWING_BOTH,
        ]
        
        # Function IDs are now in const.py, no need to extract from device data
        # But we can still store them if needed for debugging
        self._function_ids: dict[str, int] = {}

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if not self.coordinator.data:
            return None
            
        device_data = self.coordinator.data.get(self._device_id, {})
        if not device_data:
            return None
        
        # Try curTemp field first (from API structure)
        cur_temp = device_data.get("curTemp")
        if cur_temp is not None:
            try:
                return float(cur_temp)
            except (ValueError, TypeError):
                pass
        
        # Try currentStateDetailed (array with text like "21°")
        current_state_detailed = device_data.get("currentStateDetailed", [])
        if current_state_detailed and len(current_state_detailed) > 0:
            temp_text = current_state_detailed[0].get("text", "")
            if temp_text:
                # Parse "21°" or "21°C" format
                try:
                    temp_value = float("".join(filter(str.isdigit, temp_text.split("°")[0])))
                    return temp_value
                except (ValueError, TypeError):
                    pass
        
        # Try currentState (array with text like "22°")
        current_state = device_data.get("currentState", [])
        if current_state and len(current_state) > 0:
            temp_text = current_state[0].get("text", "")
            if temp_text:
                try:
                    temp_value = float("".join(filter(str.isdigit, temp_text.split("°")[0])))
                    return temp_value
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if not self.coordinator.data:
            return None
            
        device_data = self.coordinator.data.get(self._device_id, {})
        if not device_data:
            return None
            
        state = device_data.get("state", {})
        if not state:
            return None
        
        # Target temperature is in state.info.text (format: "26°C")
        info = state.get("info", {})
        temp_text = info.get("text", "")
        
        if temp_text:
            # Parse "26°C" format
            try:
                # Extract number before °C
                temp_value = float("".join(filter(str.isdigit, temp_text.split("°")[0])))
                return temp_value
            except (ValueError, TypeError):
                pass
        
        # Try to get from pult functions (if available in device data)
        pult = device_data.get("pult", [])
        for section in pult:
            if section.get("title") == "Temperature":
                functions = section.get("functions", [])
                for func in functions:
                    if func.get("id") == FUNCTION_ID_TEMPERATURE:
                        func_state = func.get("state", {})
                        temp_value = func_state.get("value")
                        if temp_value is not None:
                            try:
                                return float(temp_value)
                            except (ValueError, TypeError):
                                pass
        
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if not self.coordinator.data:
            _LOGGER.debug("hvac_mode: no coordinator data")
            return HVACMode.OFF
            
        device_data = self.coordinator.data.get(self._device_id, {})
        if not device_data:
            _LOGGER.debug("hvac_mode: no device_data for %s", self._device_id)
            return HVACMode.OFF
            
        state = device_data.get("state", {})
        if not state:
            _LOGGER.debug("hvac_mode: no state in device_data for %s", self._device_id)
            return HVACMode.OFF
        
        # Check if device is on
        is_on = state.get("isOn", False)
        
        if not is_on:
            _LOGGER.debug("hvac_mode: device %s is off", self._device_id)
            return HVACMode.OFF
        
        # Determine mode from iconNames in state.info
        info = state.get("info", {})
        icon_names = info.get("iconNames", [])
        
        _LOGGER.debug("hvac_mode: device %s iconNames: %s", self._device_id, icon_names)
        
        # Map iconNames to HVAC modes
        if "modeCool_active" in icon_names:
            return HVACMode.COOL
        elif "modeHeat_active" in icon_names:
            return HVACMode.HEAT
        elif "modeDry_active" in icon_names:
            return HVACMode.DRY
        elif "modeFan_active" in icon_names:
            return HVACMode.FAN_ONLY
        elif "modeAuto_active" in icon_names:
            return HVACMode.AUTO
        else:
            # Default to auto if device is on but mode is unclear
            _LOGGER.debug("hvac_mode: device %s mode unclear, defaulting to AUTO", self._device_id)
            return HVACMode.AUTO

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode."""
        if not self.coordinator.data:
            return "auto"
            
        device_data = self.coordinator.data.get(self._device_id, {})
        if not device_data:
            return "auto"
        
        # Try to get from pult functions first (most reliable)
        pult = device_data.get("pult", [])
        for section in pult:
            if section.get("title") == "Fan speed":
                functions = section.get("functions", [])
                for func in functions:
                    func_id = func.get("id")
                    func_state = func.get("state", {})
                    
                    # Check if Auto is active
                    if func_id == FUNCTION_ID_FAN_SPEED_AUTO:
                        if func_state.get("isOn", False):
                            return "auto"
                    
                    # Get fan speed value (1-5)
                    if func_id == FUNCTION_ID_FAN_SPEED:
                        speed_value = func_state.get("value")
                        if speed_value is not None:
                            return str(speed_value)
        
        # Fallback: determine from iconNames
        state = device_data.get("state", {})
        info = state.get("info", {})
        icon_names = info.get("iconNames", [])
        
        if "fanSpeedAuto_active" in icon_names:
            return "auto"
        
        # Try to find fan speed in iconNames (fanSpeed1_active, fanSpeed2_active, etc.)
        for icon_name in icon_names:
            if icon_name.startswith("fanSpeed") and icon_name.endswith("_active"):
                # Extract number from "fanSpeed3_active"
                speed_str = icon_name.replace("fanSpeed", "").replace("_active", "")
                if speed_str.isdigit():
                    return speed_str
        
        return "auto"

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if not self.coordinator.data:
            return PRESET_NONE
            
        device_data = self.coordinator.data.get(self._device_id, {})
        if not device_data:
            return PRESET_NONE
        
        # Check pult functions for active preset modes
        pult = device_data.get("pult", [])
        for section in pult:
            section_title = section.get("title", "").lower()
            if "additional" in section_title or "режим" in section_title.lower():
                functions = section.get("functions", [])
                for func in functions:
                    func_id = func.get("id")
                    func_state = func.get("state", {})
                    is_on = func_state.get("isOn", False)
                    
                    if is_on:
                        if func_id == FUNCTION_ID_ECO:
                            return PRESET_ECO
                        elif func_id == FUNCTION_ID_TURBO:
                            return PRESET_TURBO
                        elif func_id == FUNCTION_ID_SLEEP:
                            return PRESET_SLEEP
        
        # Check iconNames for preset modes
        state = device_data.get("state", {})
        info = state.get("info", {})
        icon_names = info.get("iconNames", [])
        
        if "eco_active" in icon_names:
            return PRESET_ECO
        elif "turbo_active" in icon_names:
            return PRESET_TURBO
        elif "sleep_active" in icon_names:
            return PRESET_SLEEP
        # Note: Comfortable Sleep is shown in UI but not settable via preset
        # as it requires additional parameters (temp, sleepTime)
        
        return PRESET_NONE

    @property
    def swing_mode(self) -> str | None:
        """Return the current swing mode."""
        if not self.coordinator.data:
            return SWING_OFF
            
        device_data = self.coordinator.data.get(self._device_id, {})
        if not device_data:
            return SWING_OFF
        
        # Check pult functions for swing modes
        pult = device_data.get("pult", [])
        vertical_on = False
        horizontal_on = False
        swing_3d_on = False
        
        for section in pult:
            section_title = section.get("title", "").lower()
            if "swing" in section_title or "качание" in section_title.lower():
                functions = section.get("functions", [])
                for func in functions:
                    func_id = func.get("id")
                    func_state = func.get("state", {})
                    is_on = func_state.get("isOn", False)
                    
                    if func_id == FUNCTION_ID_VERTICAL_SWING and is_on:
                        vertical_on = True
                    elif func_id == FUNCTION_ID_HORIZONTAL_SWING and is_on:
                        horizontal_on = True
                    elif func_id == FUNCTION_ID_3D_SWING and is_on:
                        swing_3d_on = True
        
        # Determine swing mode based on active functions
        if swing_3d_on or (vertical_on and horizontal_on):
            return SWING_BOTH
        elif vertical_on:
            return SWING_VERTICAL
        elif horizontal_on:
            return SWING_HORIZONTAL
        
        # Fallback: check iconNames
        state = device_data.get("state", {})
        info = state.get("info", {})
        icon_names = info.get("iconNames", [])
        
        if "swing3D_active" in icon_names:
            return SWING_BOTH
        elif "swingVertical_active" in icon_names:
            return SWING_VERTICAL
        elif "swingHorizontal_active" in icon_names:
            return SWING_HORIZONTAL
        
        return SWING_OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        # Validate temperature range
        if temperature < self._attr_min_temp or temperature > self._attr_max_temp:
            _LOGGER.warning(
                "Temperature %s is out of range [%s, %s]",
                temperature,
                self._attr_min_temp,
                self._attr_max_temp,
            )
            return
        
        try:
            await self.coordinator.api.async_control_device(
                int(self._device_id),
                FUNCTION_ID_TEMPERATURE,
                int(temperature),
            )
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set temperature for device %s: %s", self._device_id, err)
            raise

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            # Turn off the device
            try:
                await self.coordinator.api.async_control_device(
                    int(self._device_id),
                    FUNCTION_ID_POWER,
                    False,
                )
            except Exception as err:
                _LOGGER.error("Failed to turn off device %s: %s", self._device_id, err)
                raise
        else:
            # First, ensure device is on
            try:
                await self.coordinator.api.async_control_device(
                    int(self._device_id),
                    FUNCTION_ID_POWER,
                    True,
                )
            except Exception as err:
                _LOGGER.warning("Failed to turn on device %s: %s", self._device_id, err)
            
            # Set the mode using Function ID from mapping
            function_id = HVAC_MODE_TO_FUNCTION_ID.get(hvac_mode.value)
            if function_id:
                try:
                    # For modes with applyable: true (Cool, Heat, Auto, Dry, Fan),
                    # the API expects to activate the function.
                    # Based on intercepted requests, value can be None or True.
                    # We'll try None first (as seen in intercepted requests),
                    # but this may need adjustment based on actual API behavior.
                    await self.coordinator.api.async_control_device(
                        int(self._device_id),
                        function_id,
                        None,  # For applyable functions, value is usually None
                    )
                    _LOGGER.debug(
                        "Set HVAC mode %s (function_id=%s) for device %s",
                        hvac_mode.value,
                        function_id,
                        self._device_id,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to set HVAC mode %s for device %s: %s",
                        hvac_mode.value,
                        self._device_id,
                        err,
                    )
                    raise
            else:
                _LOGGER.warning("Unknown HVAC mode: %s", hvac_mode)
        
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode not in self._attr_fan_modes:
            _LOGGER.warning("Invalid fan mode: %s", fan_mode)
            return
        
        try:
            if fan_mode == "auto":
                # Set auto fan speed
                await self.coordinator.api.async_control_device(
                    int(self._device_id),
                    FUNCTION_ID_FAN_SPEED_AUTO,
                    True,  # Activate auto mode
                )
            else:
                # Set specific fan speed (1-5)
                try:
                    speed_value = int(fan_mode)
                    if 1 <= speed_value <= 5:
                        await self.coordinator.api.async_control_device(
                            int(self._device_id),
                            FUNCTION_ID_FAN_SPEED,
                            speed_value,
                        )
                    else:
                        _LOGGER.warning("Fan speed out of range: %s", speed_value)
                        return
                except ValueError:
                    _LOGGER.warning("Invalid fan mode value: %s", fan_mode)
                    return
            
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set fan mode for device %s: %s", self._device_id, err)
            raise

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in self._attr_preset_modes:
            _LOGGER.warning("Invalid preset mode: %s", preset_mode)
            return
        
        try:
            # First, turn off all preset modes
            for preset, func_id in PRESET_MODE_TO_FUNCTION_ID.items():
                if preset != preset_mode:
                    try:
                        await self.coordinator.api.async_control_device(
                            int(self._device_id),
                            func_id,
                            False,
                        )
                    except Exception:
                        pass  # Ignore errors when turning off other presets
            
            # Set the new preset mode (if not "none")
            if preset_mode != PRESET_NONE:
                function_id = PRESET_MODE_TO_FUNCTION_ID.get(preset_mode)
                if function_id:
                    await self.coordinator.api.async_control_device(
                        int(self._device_id),
                        function_id,
                        True,
                    )
                    _LOGGER.debug(
                        "Set preset mode %s (function_id=%s) for device %s",
                        preset_mode,
                        function_id,
                        self._device_id,
                    )
            
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set preset mode for device %s: %s", self._device_id, err)
            raise

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new swing mode."""
        if swing_mode not in self._attr_swing_modes:
            _LOGGER.warning("Invalid swing mode: %s", swing_mode)
            return
        
        try:
            if swing_mode == SWING_OFF:
                # Turn off all swing modes
                for func_id in SWING_MODE_TO_FUNCTION_ID.values():
                    try:
                        await self.coordinator.api.async_control_device(
                            int(self._device_id),
                            func_id,
                            False,
                        )
                    except Exception:
                        pass  # Ignore errors when turning off swing
            elif swing_mode == SWING_BOTH:
                # Use 3D swing if available
                await self.coordinator.api.async_control_device(
                    int(self._device_id),
                    FUNCTION_ID_3D_SWING,
                    True,
                )
            else:
                # First turn off other swing modes
                for mode, func_id in SWING_MODE_TO_FUNCTION_ID.items():
                    if mode != swing_mode:
                        try:
                            await self.coordinator.api.async_control_device(
                                int(self._device_id),
                                func_id,
                                False,
                            )
                        except Exception:
                            pass
                
                # Set the requested swing mode
                function_id = SWING_MODE_TO_FUNCTION_ID.get(swing_mode)
                if function_id:
                    await self.coordinator.api.async_control_device(
                        int(self._device_id),
                        function_id,
                        True,
                    )
                    _LOGGER.debug(
                        "Set swing mode %s (function_id=%s) for device %s",
                        swing_mode,
                        function_id,
                        self._device_id,
                    )
            
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set swing mode for device %s: %s", self._device_id, err)
            raise

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

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
        
        # Device is available if it has state or basic info
        # Check status to see if device is connected
        status = device_data.get("status", "").lower()
        if status == "disconnected":
            return False
        
        return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daichi climate entities from a config entry."""
    coordinator: DaichiDataUpdateCoordinator = entry.runtime_data
    
    # Wait for initial data if not available
    if coordinator.data is None:
        await coordinator.async_request_refresh()
    
    entities = []
    for device_id, device_data in (coordinator.data or {}).items():
        entities.append(
            DaichiClimateEntity(coordinator, str(device_id), device_data)
        )
    
    async_add_entities(entities, update_before_add=True)

