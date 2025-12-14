"""Daichi Comfort Cloud integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed

from .const import DOMAIN
from .coordinator import DaichiDataUpdateCoordinator
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Daichi from a config entry."""
    coordinator = DaichiDataUpdateCoordinator(hass, entry)
    
    try:
        # Fetch initial data so we have data when entities are added
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        # Auth failed, let Home Assistant handle reauth
        raise
    except CannotConnect as err:
        raise ConfigEntryNotReady(f"Unable to connect to Daichi API: {err}") from err
    except Exception as err:
        _LOGGER.exception("Unexpected error setting up Daichi integration")
        raise ConfigEntryNotReady(f"Unexpected error: {err}") from err
    
    # Store coordinator in runtime_data
    entry.runtime_data = coordinator
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: DaichiDataUpdateCoordinator = entry.runtime_data
    await coordinator.api.async_close()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

