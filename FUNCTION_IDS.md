# Function IDs for Daichi Device Control

## Complete List of Function IDs

### Basic Functions

| Function ID | Name | Type | Range/Values | BLE Tag | Description |
|-------------|------|------|--------------|---------|-------------|
| 350 | Power | boolean | true/false | power | Turn device on/off |
| 351 | Temperature | number | 16-30 | setTemp | Set temperature (°C) |

### Operating Modes (Mode of operation)

| Function ID | Name | applyable | BLE Tag | BLE Command | Description |
|-------------|------|-----------|---------|-------------|-------------|
| 352 | Cool | true | mode | cool | Cooling mode |
| 353 | Heat | true | mode | heat | Heating mode |
| 354 | Auto | true | mode | auto | Automatic mode |
| 355 | Dry | true | mode | dry | Dehumidification mode |
| 356 | Fan | true | mode | vent | Ventilation mode |

**Note:** For operating modes, `applyable: true` means the function needs to be activated.

### Fan Speed

| Function ID | Name | Type | Range | applyable | BLE Tag | Description |
|-------------|------|------|-------|-----------|---------|-------------|
| 357 | Auto | boolean | - | true | fanSpeed | Automatic speed (BLE command: "0") |
| 358 | Fan speed | number | 1-5 | false | fanSpeed | Fan speed (1-5) |

**Note:** Function ID 357 (Auto) is a linkedFunction for 358.

### Swing

| Function ID | Name | applyable | BLE Tag | BLE On Command | BLE Off Command | Description |
|-------------|------|-----------|---------|----------------|-----------------|-------------|
| 359 | Vertical swing | false | flow | vert_on | off | Vertical swing |
| 360 | Horizontal swing | false | flow | horizont_on | off | Horizontal swing |
| 361 | 3D swing | false | flow | 3d_on | off | 3D swing |

### Additional Modes

| Function ID | Name | applyable | ignorePowerOff | BLE Tag | BLE On Command | BLE Off Command | Description |
|-------------|------|-----------|----------------|---------|----------------|-----------------|-------------|
| 362 | Comfortable Sleep | false | true | none | on | off | Comfortable sleep (with parameters) |
| 363 | Eco | false | false | economy | on | off | Eco mode |
| 364 | Turbo | false | false | powerfull | on | off | Turbo mode |
| 365 | Sound Off | false | true | beepOff | on | off | Silent mode (sound off) |
| 366 | Sleep | false | false | sleep | on | off | Sleep mode |
| 332 | Heating +8°C | false | false | heat8 | on | off | Heating +8°C |

## Features

### applyable

- `applyable: true` - Function is activated via control request (e.g., operating modes)
- `applyable: false` - Function is toggled (on/off)

### ignorePowerOff

- `ignorePowerOff: true` - Function works even when device is off (e.g., Sound Off, Comfortable Sleep)
- `ignorePowerOff: false` - Function works only when device is on

### linkedFunction

Some functions are linked to others:
- Function ID 351 (Temperature) has linkedFunction 350 (Power)
- Function ID 358 (Fan speed) has linkedFunction 357 (Auto)

## Home Assistant Mapping

### Operating Mode (HVAC Mode)

| Home Assistant Mode | Function ID | Value |
|---------------------|-------------|-------|
| `off` | 350 | false |
| `cool` | 352 | true (applyable) |
| `heat` | 353 | true (applyable) |
| `dry` | 355 | true (applyable) |
| `fan_only` | 356 | true (applyable) |
| `auto` | 354 | true (applyable) |

### Fan Speed (Fan Mode)

| Home Assistant Fan Mode | Function ID | Value |
|-------------------------|-------------|-------|
| `auto` | 357 | true |
| `1` | 358 | 1 |
| `2` | 358 | 2 |
| `3` | 358 | 3 |
| `4` | 358 | 4 |
| `5` | 358 | 5 |

### Temperature

| Parameter | Function ID | Value |
|-----------|-------------|-------|
| Target Temperature | 351 | number (16-30) |

### Power On/Off

| Parameter | Function ID | Value |
|-----------|-------------|-------|
| Power | 350 | boolean |
