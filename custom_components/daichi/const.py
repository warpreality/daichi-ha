"""Constants for the Daichi integration."""
from __future__ import annotations

DOMAIN = "daichi"

# Configuration keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DAICHI_API = "daichi_api"

# Default values
DEFAULT_DAICHI_API = "https://web.daichicloud.ru/api/v4"
DEFAULT_CLIENT_ID = "sOJO7B6SqgaKudTfCzqLAy540cCuDzpI"

# Update interval
UPDATE_INTERVAL = 60  # seconds

# Function IDs для управления устройством
# См. FUNCTION_IDS.md для полного списка

# Основные функции
FUNCTION_ID_POWER = 350
FUNCTION_ID_TEMPERATURE = 351

# Режимы работы (Mode of operation)
FUNCTION_ID_COOL = 352
FUNCTION_ID_HEAT = 353
FUNCTION_ID_AUTO = 354
FUNCTION_ID_DRY = 355
FUNCTION_ID_FAN = 356

# Скорость вентилятора (Fan speed)
FUNCTION_ID_FAN_SPEED_AUTO = 357
FUNCTION_ID_FAN_SPEED = 358

# Swing (Качание)
FUNCTION_ID_VERTICAL_SWING = 359
FUNCTION_ID_HORIZONTAL_SWING = 360
FUNCTION_ID_3D_SWING = 361

# Дополнительные режимы (Additional modes)
FUNCTION_ID_COMFORTABLE_SLEEP = 362
FUNCTION_ID_ECO = 363
FUNCTION_ID_TURBO = 364
FUNCTION_ID_SOUND_OFF = 365
FUNCTION_ID_SLEEP = 366
FUNCTION_ID_HEATING_PLUS_8 = 332

# Маппинг режимов Home Assistant на Function IDs
HVAC_MODE_TO_FUNCTION_ID = {
    "off": FUNCTION_ID_POWER,
    "cool": FUNCTION_ID_COOL,
    "heat": FUNCTION_ID_HEAT,
    "dry": FUNCTION_ID_DRY,
    "fan_only": FUNCTION_ID_FAN,
    "auto": FUNCTION_ID_AUTO,
}

# Маппинг скорости вентилятора Home Assistant на Function IDs
FAN_MODE_TO_FUNCTION_ID = {
    "auto": FUNCTION_ID_FAN_SPEED_AUTO,
    "1": FUNCTION_ID_FAN_SPEED,
    "2": FUNCTION_ID_FAN_SPEED,
    "3": FUNCTION_ID_FAN_SPEED,
    "4": FUNCTION_ID_FAN_SPEED,
    "5": FUNCTION_ID_FAN_SPEED,
}

# Preset modes (дополнительные режимы работы)
# Note: Comfortable Sleep requires additional parameters (temp, sleepTime)
# so it cannot be activated via simple preset, it's not included here.
PRESET_NONE = "none"
PRESET_ECO = "eco"
PRESET_TURBO = "turbo"
PRESET_SLEEP = "sleep"

PRESET_MODE_TO_FUNCTION_ID = {
    PRESET_ECO: FUNCTION_ID_ECO,
    PRESET_TURBO: FUNCTION_ID_TURBO,
    PRESET_SLEEP: FUNCTION_ID_SLEEP,
}

# Swing modes
SWING_OFF = "off"
SWING_VERTICAL = "vertical"
SWING_HORIZONTAL = "horizontal"
SWING_BOTH = "both"

SWING_MODE_TO_FUNCTION_ID = {
    SWING_VERTICAL: FUNCTION_ID_VERTICAL_SWING,
    SWING_HORIZONTAL: FUNCTION_ID_HORIZONTAL_SWING,
    SWING_BOTH: FUNCTION_ID_3D_SWING,
}

