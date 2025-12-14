# Function IDs для управления устройствами Daichi

## Полный список Function IDs

### Основные функции

| Function ID | Название | Тип | Диапазон/Значения | BLE Tag | Описание |
|-------------|----------|-----|-------------------|---------|----------|
| 350 | Power | boolean | true/false | power | Включение/выключение устройства |
| 351 | Temperature | number | 16-30 | setTemp | Установка температуры (°C) |

### Режимы работы (Mode of operation)

| Function ID | Название | applyable | BLE Tag | BLE Command | Описание |
|-------------|----------|-----------|---------|-------------|----------|
| 352 | Cool | true | mode | cool | Режим охлаждения |
| 353 | Heat | true | mode | heat | Режим обогрева |
| 354 | Auto | true | mode | auto | Автоматический режим |
| 355 | Dry | true | mode | dry | Режим осушения |
| 356 | Fan | true | mode | vent | Режим вентиляции |

**Примечание:** Для режимов работы `applyable: true` означает, что нужно активировать функцию.

### Скорость вентилятора (Fan speed)

| Function ID | Название | Тип | Диапазон | applyable | BLE Tag | Описание |
|-------------|----------|-----|----------|-----------|---------|----------|
| 357 | Auto | boolean | - | true | fanSpeed | Автоматическая скорость (BLE command: "0") |
| 358 | Fan speed | number | 1-5 | false | fanSpeed | Скорость вентилятора (1-5) |

**Примечание:** Function ID 357 (Auto) является linkedFunction для 358.

### Swing (Качание)

| Function ID | Название | applyable | BLE Tag | BLE On Command | BLE Off Command | Описание |
|-------------|----------|-----------|---------|----------------|-----------------|----------|
| 359 | Vertical swing | false | flow | vert_on | off | Вертикальное качание |
| 360 | Horizontal swing | false | flow | horizont_on | off | Горизонтальное качание |
| 361 | 3D swing | false | flow | 3d_on | off | 3D качание |

### Дополнительные режимы (Additional modes)

| Function ID | Название | applyable | ignorePowerOff | BLE Tag | BLE On Command | BLE Off Command | Описание |
|-------------|----------|-----------|----------------|---------|----------------|-----------------|----------|
| 362 | Comfortable Sleep | false | true | none | on | off | Комфортный сон (с параметрами) |
| 363 | Eco | false | false | economy | on | off | Эко режим |
| 364 | Turbo | false | false | powerfull | on | off | Турбо режим |
| 365 | Sound Off | false | true | beepOff | on | off | Тихий режим (отключение звука) |
| 366 | Sleep | false | false | sleep | on | off | Режим сна |
| 332 | Heating +8°C | false | false | heat8 | on | off | Обогрев +8°C |

## Особенности

### applyable

- `applyable: true` - Функция активируется через запрос управления (например, режимы работы)
- `applyable: false` - Функция переключается (on/off)

### ignorePowerOff

- `ignorePowerOff: true` - Функция работает даже при выключенном устройстве (например, Sound Off, Comfortable Sleep)
- `ignorePowerOff: false` - Функция работает только при включенном устройстве

### Параметры

Некоторые функции могут иметь параметры в поле `parameters`:

- **Comfortable Sleep (362)**: 
  ```json
  {
    "comfortSleepParameters": {
      "temp": 22,
      "sleepTime": 480
    }
  }
  ```

### linkedFunction

Некоторые функции связаны с другими:
- Function ID 351 (Temperature) имеет linkedFunction 350 (Power)
- Function ID 358 (Fan speed) имеет linkedFunction 357 (Auto)

## Маппинг для Home Assistant

### Режим работы (HVAC Mode)

| Home Assistant Mode | Function ID | Значение |
|---------------------|-------------|----------|
| `off` | 350 | false |
| `cool` | 352 | true (applyable) |
| `heat` | 353 | true (applyable) |
| `dry` | 355 | true (applyable) |
| `fan_only` | 356 | true (applyable) |
| `auto` | 354 | true (applyable) |

### Скорость вентилятора (Fan Mode)

| Home Assistant Fan Mode | Function ID | Значение |
|-------------------------|-------------|----------|
| `auto` | 357 | true |
| `1` | 358 | 1 |
| `2` | 358 | 2 |
| `3` | 358 | 3 |
| `4` | 358 | 4 |
| `5` | 358 | 5 |

### Температура

| Параметр | Function ID | Значение |
|----------|-------------|----------|
| Target Temperature | 351 | number (16-30) |

### Включение/выключение

| Параметр | Function ID | Значение |
|----------|-------------|----------|
| Power | 350 | boolean |
