"""Data update coordinator for Daichi."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
            session=async_get_clientsession(hass),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Daichi API."""
        try:
            if not self.api.is_authenticated:
                await self.api.async_authenticate()

            devices = await self.api.async_get_devices(force_refresh=True)

            if not devices:
                _LOGGER.warning("No devices found in Daichi account")
                return {}

            device_ids = [d["id"] for d in devices if d.get("id")]
            full_infos = await self.api.async_get_device_states(device_ids)

            device_states: dict[str, Any] = {}
            for device in devices:
                device_id = device.get("id")
                if not device_id:
                    _LOGGER.warning("Device missing ID: %s", device)
                    continue

                full_info = full_infos.get(device_id)
                if full_info:
                    device_states[str(device_id)] = {**device, **full_info}
                else:
                    device_states[str(device_id)] = device

            return device_states
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("Authentication failed") from err
        except CannotConnect as err:
            raise UpdateFailed(f"Error communicating with Daichi API: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error updating Daichi data")
            raise UpdateFailed(f"Unexpected error: {err}") from err
