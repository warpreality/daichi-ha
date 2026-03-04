"""Config flow for Daichi integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DAICHI_API,
    DEFAULT_DAICHI_API,
    DOMAIN,
)
from .api import DaichiApiClient
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    client = DaichiApiClient(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        daichi_api=data.get(CONF_DAICHI_API, DEFAULT_DAICHI_API),
        session=async_get_clientsession(hass),
    )

    try:
        await client.async_authenticate()
        await client.async_get_devices()
    except InvalidAuth:
        raise
    except Exception as err:
        raise CannotConnect from err

    return {"title": f"Daichi ({data[CONF_USERNAME]})"}


class DaichiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daichi."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error in config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_DAICHI_API, default=DEFAULT_DAICHI_API): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any],
    ) -> FlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            new_data = {**reauth_entry.data, **user_input}
            try:
                await validate_input(self.hass, new_data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry, data=new_data,
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=data_schema,
            errors=errors,
        )
