"""Проверка применения команд управления устройством."""
from __future__ import annotations

from typing import Any

from .const import (
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
    FUNCTION_ID_SOUND_OFF,
    FUNCTION_ID_SLEEP,
)


def _get_pult_function(device_data: dict[str, Any], function_id: int) -> dict[str, Any] | None:
    """Вернуть функцию из pult по id или None."""
    for section in device_data.get("pult", []):
        for func in section.get("functions", []):
            if func.get("id") == function_id:
                return func
    return None


def _get_pult_function_state(device_data: dict[str, Any], function_id: int) -> dict[str, Any]:
    """Вернуть state функции из pult или пустой dict."""
    func = _get_pult_function(device_data, function_id)
    return (func or {}).get("state", {})


# Иконки режимов в state.info.iconNames
HVAC_FUNCTION_ID_TO_ICON = {
    FUNCTION_ID_COOL: "modeCool_active",
    FUNCTION_ID_HEAT: "modeHeat_active",
    FUNCTION_ID_AUTO: "modeAuto_active",
    FUNCTION_ID_DRY: "modeDry_active",
    FUNCTION_ID_FAN: "modeFan_active",
}


def verify_control_applied(
    device_data: dict[str, Any],
    function_id: int,
    value: Any,
) -> bool:
    """
    Проверить, что команда применилась по актуальному состоянию устройства.
    Возвращает True, если состояние совпадает с ожидаемым.
    """
    if not device_data:
        return False

    state = device_data.get("state", {})
    icon_names = state.get("info", {}).get("iconNames", [])

    if function_id == FUNCTION_ID_POWER:
        is_on = state.get("isOn", False)
        expected = bool(value) if value is not None else True
        return is_on == expected

    if function_id == FUNCTION_ID_TEMPERATURE:
        st = _get_pult_function_state(device_data, FUNCTION_ID_TEMPERATURE)
        current_val = st.get("value")
        if current_val is None:
            return False
        try:
            return int(current_val) == int(value)
        except (TypeError, ValueError):
            return False

    if function_id in HVAC_FUNCTION_ID_TO_ICON:
        # Режим работы (applyable): проверяем, что устройство включено и иконка режима активна
        if not state.get("isOn", False):
            return False
        expected_icon = HVAC_FUNCTION_ID_TO_ICON.get(function_id)
        return expected_icon in icon_names if expected_icon else False

    if function_id == FUNCTION_ID_FAN_SPEED_AUTO:
        st = _get_pult_function_state(device_data, FUNCTION_ID_FAN_SPEED_AUTO)
        return bool(st.get("isOn", False))

    if function_id == FUNCTION_ID_FAN_SPEED:
        st = _get_pult_function_state(device_data, FUNCTION_ID_FAN_SPEED)
        current_val = st.get("value")
        if current_val is None:
            return False
        try:
            return int(current_val) == int(value)
        except (TypeError, ValueError):
            return False

    # Переключаемые функции: 359,360,361 (swing), 363,364,365,366 (preset/sound/sleep)
    toggle_function_ids = {
        FUNCTION_ID_VERTICAL_SWING,
        FUNCTION_ID_HORIZONTAL_SWING,
        FUNCTION_ID_3D_SWING,
        FUNCTION_ID_ECO,
        FUNCTION_ID_TURBO,
        FUNCTION_ID_SOUND_OFF,
        FUNCTION_ID_SLEEP,
    }
    if function_id in toggle_function_ids:
        st = _get_pult_function_state(device_data, function_id)
        current = bool(st.get("isOn", False))
        expected = bool(value) if value is not None else True
        return current == expected

    # Неизвестная функция — считаем применённой
    return True
