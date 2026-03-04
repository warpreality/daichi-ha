"""Climate platform for Daichi integration."""
from __future__ import annotations

import logging
import re
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

from .const import (
    DOMAIN,
    FUNCTION_ID_POWER,
    FUNCTION_ID_TEMPERATURE,
    FUNCTION_ID_FAN_SPEED_AUTO,
    FUNCTION_ID_FAN_SPEED,
    FUNCTION_ID_VERTICAL_SWING,
    FUNCTION_ID_HORIZONTAL_SWING,
    FUNCTION_ID_3D_SWING,
    FUNCTION_ID_ECO,
    FUNCTION_ID_TURBO,
    FUNCTION_ID_SLEEP,
    FUNCTION_ID_TO_HVAC_MODE,
    FUNCTION_ID_TO_PRESET,
    FUNCTION_ID_TO_SWING,
    HVAC_MODE_TO_FUNCTION_ID,
    PRESET_NONE,
    PRESET_MODE_TO_FUNCTION_ID,
    SWING_OFF,
    SWING_BOTH,
    SWING_MODE_TO_FUNCTION_ID,
)
from .coordinator import DaichiDataUpdateCoordinator
from .entity import DaichiEntity, parse_temperature

_LOGGER = logging.getLogger(__name__)


def _collect_function_ids(device_data: dict[str, Any]) -> set[int]:
    """Collect all function IDs available in device pult."""
    ids: set[int] = set()
    for section in device_data.get("pult", []):
        for func in section.get("functions", []):
            fid = func.get("id")
            if fid is not None:
                ids.add(fid)
    return ids


def _detect_fan_speed_range(device_data: dict[str, Any]) -> int:
    """Detect max fan speed from pult function config."""
    for section in device_data.get("pult", []):
        for func in section.get("functions", []):
            if func.get("id") == FUNCTION_ID_FAN_SPEED:
                max_val = func.get("maxValue") or func.get("max")
                if max_val is not None:
                    try:
                        return int(max_val)
                    except (ValueError, TypeError):
                        pass
    return 5


def _detect_temp_range(device_data: dict[str, Any]) -> tuple[float, float]:
    """Detect min/max temperature from pult function config."""
    for section in device_data.get("pult", []):
        for func in section.get("functions", []):
            if func.get("id") == FUNCTION_ID_TEMPERATURE:
                min_val = func.get("minValue") or func.get("min")
                max_val = func.get("maxValue") or func.get("max")
                try:
                    lo = float(min_val) if min_val is not None else 16.0
                    hi = float(max_val) if max_val is not None else 30.0
                    return (lo, hi)
                except (ValueError, TypeError):
                    pass
    return (16.0, 30.0)


class DaichiClimateEntity(DaichiEntity, ClimateEntity):
    """Representation of a Daichi climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0

    def __init__(
        self,
        coordinator: DaichiDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, device_id, device_data)
        self._attr_unique_id = f"{DOMAIN}_{device_id}"

        func_ids = _collect_function_ids(device_data)

        self._attr_hvac_modes = [HVACMode.OFF]
        for fid, mode_str in FUNCTION_ID_TO_HVAC_MODE.items():
            if fid in func_ids:
                self._attr_hvac_modes.append(HVACMode(mode_str))
        if len(self._attr_hvac_modes) == 1:
            self._attr_hvac_modes = [
                HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT,
                HVACMode.FAN_ONLY, HVACMode.DRY, HVACMode.AUTO,
            ]

        has_fan = FUNCTION_ID_FAN_SPEED in func_ids or FUNCTION_ID_FAN_SPEED_AUTO in func_ids
        if has_fan:
            max_speed = _detect_fan_speed_range(device_data)
            self._attr_fan_modes = ["auto"] + [str(i) for i in range(1, max_speed + 1)]
        else:
            self._attr_fan_modes = []

        preset_list: list[str] = []
        for fid, preset_name in FUNCTION_ID_TO_PRESET.items():
            if fid in func_ids:
                preset_list.append(preset_name)
        if preset_list:
            self._attr_preset_modes = [PRESET_NONE] + preset_list
        else:
            self._attr_preset_modes = []

        swing_list: list[str] = []
        for fid, swing_name in FUNCTION_ID_TO_SWING.items():
            if fid in func_ids:
                swing_list.append(swing_name)
        if swing_list:
            self._attr_swing_modes = [SWING_OFF] + swing_list
        else:
            self._attr_swing_modes = []

        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if FUNCTION_ID_TEMPERATURE in func_ids:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if has_fan:
            features |= ClimateEntityFeature.FAN_MODE
        if preset_list:
            features |= ClimateEntityFeature.PRESET_MODE
        if swing_list:
            features |= ClimateEntityFeature.SWING_MODE
        self._attr_supported_features = features

        min_t, max_t = _detect_temp_range(device_data)
        self._attr_min_temp = min_t
        self._attr_max_temp = max_t

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        dd = self.device_data
        if not dd:
            return None

        cur_temp = dd.get("curTemp")
        if cur_temp is not None:
            try:
                return float(cur_temp)
            except (ValueError, TypeError):
                pass

        for key in ("currentStateDetailed", "currentState"):
            items = dd.get(key, [])
            if items:
                temp = parse_temperature(items[0].get("text", ""))
                if temp is not None:
                    return temp

        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        dd = self.device_data
        if not dd:
            return None

        state = dd.get("state", {})
        if not state:
            return None

        info = state.get("info", {})
        temp = parse_temperature(info.get("text", ""))
        if temp is not None:
            return temp

        pult = dd.get("pult", [])
        for section in pult:
            if section.get("title") == "Temperature":
                for func in section.get("functions", []):
                    if func.get("id") == FUNCTION_ID_TEMPERATURE:
                        val = func.get("state", {}).get("value")
                        if val is not None:
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                pass

        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        dd = self.device_data
        state = dd.get("state", {})
        if not state or not state.get("isOn", False):
            return HVACMode.OFF

        icon_names = state.get("info", {}).get("iconNames", [])

        icon_to_mode = {
            "modeCool_active": HVACMode.COOL,
            "modeHeat_active": HVACMode.HEAT,
            "modeDry_active": HVACMode.DRY,
            "modeFan_active": HVACMode.FAN_ONLY,
            "modeAuto_active": HVACMode.AUTO,
        }
        for icon, mode in icon_to_mode.items():
            if icon in icon_names:
                return mode

        return HVACMode.AUTO

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode."""
        dd = self.device_data
        if not dd:
            return "auto"

        icon_names = dd.get("state", {}).get("info", {}).get("iconNames", [])

        if "fanSpeedAuto_active" in icon_names:
            return "auto"

        for icon_name in icon_names:
            if icon_name.startswith("fanSpeed") and icon_name.endswith("_active"):
                match = re.search(r"fanSpeedM\d+V(\d+)_active", icon_name)
                if match:
                    return match.group(1)
                speed_str = icon_name.replace("fanSpeed", "").replace("_active", "")
                if speed_str.isdigit():
                    return speed_str

        pult = dd.get("pult", [])
        for section in pult:
            for func in section.get("functions", []):
                func_id = func.get("id")
                func_state = func.get("state", {})
                if func_id == FUNCTION_ID_FAN_SPEED_AUTO and func_state.get("isOn", False):
                    return "auto"
                if func_id == FUNCTION_ID_FAN_SPEED:
                    val = func_state.get("value")
                    if val is not None:
                        return str(val)

        return "auto"

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        dd = self.device_data
        if not dd:
            return PRESET_NONE

        func_id_to_preset = FUNCTION_ID_TO_PRESET

        pult = dd.get("pult", [])
        for section in pult:
            for func in section.get("functions", []):
                fid = func.get("id")
                if fid in func_id_to_preset and func.get("state", {}).get("isOn", False):
                    return func_id_to_preset[fid]

        icon_names = dd.get("state", {}).get("info", {}).get("iconNames", [])
        icon_to_preset = {
            "eco_active": FUNCTION_ID_TO_PRESET.get(FUNCTION_ID_ECO, "eco"),
            "turbo_active": FUNCTION_ID_TO_PRESET.get(FUNCTION_ID_TURBO, "turbo"),
            "sleep_active": FUNCTION_ID_TO_PRESET.get(FUNCTION_ID_SLEEP, "sleep"),
        }
        for icon, preset in icon_to_preset.items():
            if icon in icon_names:
                return preset

        return PRESET_NONE

    @property
    def swing_mode(self) -> str | None:
        """Return the current swing mode."""
        dd = self.device_data
        if not dd:
            return SWING_OFF

        pult = dd.get("pult", [])
        vertical_on = False
        horizontal_on = False
        swing_3d_on = False

        for section in pult:
            for func in section.get("functions", []):
                fid = func.get("id")
                is_on = func.get("state", {}).get("isOn", False)
                if fid == FUNCTION_ID_VERTICAL_SWING and is_on:
                    vertical_on = True
                elif fid == FUNCTION_ID_HORIZONTAL_SWING and is_on:
                    horizontal_on = True
                elif fid == FUNCTION_ID_3D_SWING and is_on:
                    swing_3d_on = True

        if swing_3d_on or (vertical_on and horizontal_on):
            return SWING_BOTH
        if vertical_on:
            return FUNCTION_ID_TO_SWING[FUNCTION_ID_VERTICAL_SWING]
        if horizontal_on:
            return FUNCTION_ID_TO_SWING[FUNCTION_ID_HORIZONTAL_SWING]

        icon_names = dd.get("state", {}).get("info", {}).get("iconNames", [])
        if "swing3D_active" in icon_names:
            return SWING_BOTH
        if "swingVertical_active" in icon_names:
            return FUNCTION_ID_TO_SWING[FUNCTION_ID_VERTICAL_SWING]
        if "swingHorizontal_active" in icon_names:
            return FUNCTION_ID_TO_SWING[FUNCTION_ID_HORIZONTAL_SWING]

        return SWING_OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        if temperature < self._attr_min_temp or temperature > self._attr_max_temp:
            _LOGGER.warning(
                "Temperature %s is out of range [%s, %s]",
                temperature, self._attr_min_temp, self._attr_max_temp,
            )
            return

        try:
            await self.coordinator.api.async_control_device(
                int(self._device_id), FUNCTION_ID_TEMPERATURE, int(temperature),
            )
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set temperature for device %s: %s", self._device_id, err)
            raise

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            try:
                await self.coordinator.api.async_control_device(
                    int(self._device_id), FUNCTION_ID_POWER, False,
                )
            except Exception as err:
                _LOGGER.error("Failed to turn off device %s: %s", self._device_id, err)
                raise
        else:
            # Отправляем Power только если устройство выключено — иначе одна команда (режим)
            current_mode = self.hvac_mode
            if current_mode == HVACMode.OFF:
                try:
                    await self.coordinator.api.async_control_device(
                        int(self._device_id), FUNCTION_ID_POWER, True,
                    )
                except Exception as err:
                    _LOGGER.warning("Failed to turn on device %s: %s", self._device_id, err)

            function_id = HVAC_MODE_TO_FUNCTION_ID.get(hvac_mode.value)
            if function_id:
                try:
                    await self.coordinator.api.async_control_device(
                        int(self._device_id), function_id, None,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to set HVAC mode %s for device %s: %s",
                        hvac_mode.value, self._device_id, err,
                    )
                    raise
            else:
                _LOGGER.warning("Unknown HVAC mode: %s", hvac_mode)

        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode not in (self._attr_fan_modes or []):
            _LOGGER.warning("Invalid fan mode: %s", fan_mode)
            return

        try:
            if fan_mode == "auto":
                await self.coordinator.api.async_control_device(
                    int(self._device_id), FUNCTION_ID_FAN_SPEED_AUTO, True,
                )
            else:
                speed_value = int(fan_mode)
                await self.coordinator.api.async_control_device(
                    int(self._device_id), FUNCTION_ID_FAN_SPEED, speed_value,
                )
            await self.coordinator.async_request_refresh()
        except ValueError:
            _LOGGER.warning("Invalid fan mode value: %s", fan_mode)
        except Exception as err:
            _LOGGER.error("Failed to set fan mode for device %s: %s", self._device_id, err)
            raise

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in (self._attr_preset_modes or []):
            _LOGGER.warning("Invalid preset mode: %s", preset_mode)
            return

        try:
            current = self.preset_mode
            if current and current != PRESET_NONE and current != preset_mode:
                func_id = PRESET_MODE_TO_FUNCTION_ID.get(current)
                if func_id:
                    try:
                        await self.coordinator.api.async_control_device(
                            int(self._device_id), func_id, False,
                        )
                    except Exception:
                        _LOGGER.debug("Failed to turn off preset %s", current)

            if preset_mode != PRESET_NONE:
                function_id = PRESET_MODE_TO_FUNCTION_ID.get(preset_mode)
                if function_id:
                    await self.coordinator.api.async_control_device(
                        int(self._device_id), function_id, True,
                    )

            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set preset mode for device %s: %s", self._device_id, err)
            raise

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new swing mode."""
        if swing_mode not in (self._attr_swing_modes or []):
            _LOGGER.warning("Invalid swing mode: %s", swing_mode)
            return

        try:
            current = self.swing_mode
            if current and current != SWING_OFF and current != swing_mode:
                func_id = SWING_MODE_TO_FUNCTION_ID.get(current)
                if func_id:
                    try:
                        await self.coordinator.api.async_control_device(
                            int(self._device_id), func_id, False,
                        )
                    except Exception:
                        _LOGGER.debug("Failed to turn off swing %s", current)

            if swing_mode != SWING_OFF:
                function_id = SWING_MODE_TO_FUNCTION_ID.get(swing_mode)
                if function_id:
                    await self.coordinator.api.async_control_device(
                        int(self._device_id), function_id, True,
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daichi climate entities from a config entry."""
    coordinator: DaichiDataUpdateCoordinator = entry.runtime_data

    if coordinator.data is None:
        await coordinator.async_request_refresh()

    entities = []
    for device_id, device_data in (coordinator.data or {}).items():
        entities.append(
            DaichiClimateEntity(coordinator, str(device_id), device_data)
        )

    async_add_entities(entities, update_before_add=True)
