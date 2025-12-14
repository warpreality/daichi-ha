"""Data update coordinator for Daichi."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import DaichiApiClient
from .const import UPDATE_INTERVAL
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)


class DaichiDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the Daichi API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
            config_entry=entry,
        )
        
        self.api = DaichiApiClient(
            username=entry.data["username"],
            password=entry.data["password"],
            daichi_api=entry.data.get("daichi_api"),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Daichi API."""
        try:
            # Ensure we're authenticated
            if not self.api._access_token:
                await self.api.async_authenticate()
            
            # Clear cache to get fresh data on each update
            self.api.clear_cache()
            
            # Get devices (places) - they already contain state information
            devices = await self.api.async_get_devices(force_refresh=True)
            
            if not devices:
                _LOGGER.warning("No devices found in Daichi account")
                return {}
            
            # Process devices - they already contain state in the response
            device_states: dict[str, Any] = {}
            for device in devices:
                device_id = device.get("id")
                if not device_id:
                    _LOGGER.warning("Device missing ID: %s", device)
                    continue
                
                # Device data from /buildings/{id}/places already contains state
                # But we might want to get full device info with pult (functions) for better control
                try:
                    # Get full device info (includes pult with functions)
                    full_device_info = await self.api.async_get_device_state(device_id)
                    
                    # Merge device data with full info
                    # Full info has pult (functions), device from places has state
                    device_states[str(device_id)] = {
                        **device,  # Contains state from places endpoint
                        **full_device_info,  # Contains pult and other info
                    }
                    _LOGGER.debug("Updated state for device %s", device_id)
                except CannotConnect as err:
                    _LOGGER.warning(
                        "Failed to fetch full info for device %s: %s. Using basic device data.",
                        device_id,
                        err,
                    )
                    # Use device data from places (already has state)
                    device_states[str(device_id)] = device
                except Exception as err:
                    _LOGGER.exception(
                        "Unexpected error fetching full info for device %s: %s",
                        device_id,
                        err,
                    )
                    # Use device data from places (already has state)
                    device_states[str(device_id)] = device
            
            return device_states
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("Authentication failed") from err
        except CannotConnect as err:
            raise UpdateFailed(f"Error communicating with Daichi API: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error updating Daichi data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

