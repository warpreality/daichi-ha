"""Config flow for Daichi integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DAICHI_API,
    DEFAULT_DAICHI_API,
    DOMAIN,
)
from .api import DaichiApiClient
from .exceptions import CannotConnect, InvalidAuth


async def validate_input(hass: HomeAssistant, data: dict[str, str]) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    client = DaichiApiClient(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        daichi_api=data.get(CONF_DAICHI_API, DEFAULT_DAICHI_API),
    )
    
    try:
        await client.async_authenticate()
        devices = await client.async_get_devices()
    except InvalidAuth:
        raise
    except Exception as err:
        raise CannotConnect from err
    finally:
        await client.async_close()
    
    # Return info that will be stored in the config entry
    return {"title": f"Daichi ({data[CONF_USERNAME]})"}


class DaichiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daichi."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
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

