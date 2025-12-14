# Daichi Comfort Cloud for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/warpreality/daichi-ha.svg?style=flat-square)](https://github.com/warpreality/daichi-ha/releases)

Home Assistant integration for controlling Daichi AC units via the Comfort Cloud API.

## ✅ Features

- 🌡️ **Temperature control** (16-30°C)
- ❄️ **Operating modes**: cool, heat, fan, dry, auto
- 💨 **Fan speed**: auto, 1-5
- 🔄 **Preset modes**: eco, turbo, sleep, comfort sleep
- 🎯 **Swing modes**: vertical, horizontal, 3D
- 📊 **Sensors**: indoor temperature, outdoor temperature, humidity
- 🔄 Automatic state refresh every 60 seconds

## 📦 Installation

### Via HACS (recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Go to HACS → Integrations
3. Click ⋮ → Custom repositories
4. Add the repository:
   - URL: `https://github.com/warpreality/daichi-ha`
   - Category: Integration
5. Find "Daichi Comfort Cloud" and click "Install"
6. Restart Home Assistant

### Manual installation

```bash
# Copy custom_components/daichi into your Home Assistant
cp -r custom_components/daichi /config/custom_components/
```

Restart Home Assistant.

## ⚙️ Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add integration**
3. Find **Daichi Comfort Cloud**
4. Enter your credentials:
   - **Email**: the email you use for Daichi Comfort Cloud
   - **Password**: your password

## 🎮 Supported devices

Works with all Daichi/Midea AC units connected to Comfort Cloud:
- Midea Breezeless series
- And other models supported by Daichi Cloud

## 📋 Supported features

| Feature | Status |
|---------|--------|
| Power on/off | ✅ |
| Set temperature | ✅ |
| Cooling mode | ✅ |
| Heating mode | ✅ |
| Fan-only mode | ✅ |
| Dry mode | ✅ |
| Auto mode | ✅ |
| Fan speed (auto, 1-5) | ✅ |
| Eco mode | ✅ |
| Turbo mode | ✅ |
| Sleep mode | ✅ |
| Comfort Sleep | [ ] |
| Vertical swing | ✅ |
| Horizontal swing | ✅ |
| 3D swing | ✅ |
| Temperature sensor | ✅ |
| Humidity sensor | ✅ |

## 🔧 Debugging

To enable verbose logging, add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.daichi: debug
```

## 📁 Project structure

```
custom_components/
  daichi/
    __init__.py          # Integration setup
    manifest.json        # Metadata
    config_flow.py       # UI setup flow
    const.py             # Constants and Function IDs
    api.py               # API client
    coordinator.py       # Data update coordinator
    climate.py           # Climate entity
    sensor.py            # Sensors
    exceptions.py        # Exceptions
    translations/        # Translations
```

## 📖 API docs

For the full list of Function IDs for device control, see [FUNCTION_IDS.md](FUNCTION_IDS.md).

## ⚠️ Known limitations

- MQTT support for real-time updates is not implemented yet
- Some functions may be unavailable on specific AC models

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🤝 Support

If you run into issues:

1. Enable debug logging
2. Check [Issues](https://github.com/warpreality/daichi-ha/issues)
3. Open a new issue with details and logs
