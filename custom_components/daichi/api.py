"""API client for Daichi Comfort Cloud."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import aiohttp

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
    HVAC_MODE_TO_FUNCTION_ID,
    FAN_MODE_TO_FUNCTION_ID,
    DEFAULT_CLIENT_ID,
)
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
RETRY_BACKOFF = 2.0  # multiplier for exponential backoff


class DaichiApiClient:
    """Client for Daichi Comfort Cloud API."""

    def __init__(
        self,
        username: str,
        password: str,
        daichi_api: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        base_url = daichi_api or "https://web.daichicloud.ru/api/v4"
        self.daichi_api = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._buildings: list[dict[str, Any]] | None = None
        self._devices: list[dict[str, Any]] | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def async_close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def async_authenticate(self) -> bool:
        """Authenticate with Daichi API using two-step process."""
        try:
            session = await self._get_session()
            _LOGGER.debug("Authenticating with Daichi API")
            
            # Step 1: Check email/credentials
            credentials_url = f"{self.daichi_api}/user/credentials"
            credentials_payload = {"email": self.username}
            
            async with session.post(
                credentials_url, json=credentials_payload, headers={"Content-Type": "application/json"}
            ) as credentials_response:
                if credentials_response.status not in (200, 201):
                    error_text = await credentials_response.text()
                    _LOGGER.error(
                        "Email check failed: %s - %s",
                        credentials_response.status,
                        error_text,
                    )
                    raise InvalidAuth("Email check failed")
            
            # Step 2: Get token
            token_url = f"{self.daichi_api}/token"
            token_payload = {
                "email": self.username,
                "password": self.password,
                "clientId": DEFAULT_CLIENT_ID,
            }
            
            async with session.post(
                token_url, json=token_payload, headers={"Content-Type": "application/json"}
            ) as token_response:
                if token_response.status == 401:
                    raise InvalidAuth("Invalid credentials")
                if token_response.status != 200:
                    error_text = await token_response.text()
                    _LOGGER.error(
                        "Token request failed: %s - %s",
                        token_response.status,
                        error_text,
                    )
                    raise CannotConnect(f"Authentication failed: {token_response.status}")
                
                data = await token_response.json()
                
                # Extract access token from response
                # Token is in data.access_token format: {done: true, data: {access_token: "..."}}
                token_data = data.get("data", {})
                self._access_token = (
                    token_data.get("access_token")
                    or token_data.get("token")
                    or data.get("access_token")
                    or data.get("token")
                    or data.get("accessToken")
                    or data.get("access")
                )
                
                # If token is in Bearer format, extract just the token part
                if self._access_token and self._access_token.startswith("Bearer "):
                    self._access_token = self._access_token[7:]
                
                # Check if token is in cookies (session-based auth)
                if not self._access_token:
                    # Try to get token from cookies
                    cookies = token_response.cookies
                    for cookie in cookies:
                        if "token" in cookie.key.lower() or "auth" in cookie.key.lower():
                            self._access_token = cookie.value
                            break
                
                if not self._access_token:
                    _LOGGER.warning(
                        "No access token in response. Response data: %s",
                        data,
                    )
                    # Try to continue with session-based auth (cookies)
                    # The session should maintain cookies automatically
                
                _LOGGER.debug("Authentication successful")
                return True
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during authentication: %s", err)
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.error("Authentication failed: %s", err)
            if isinstance(err, (InvalidAuth, CannotConnect)):
                raise
            raise InvalidAuth from err

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Home Assistant Daichi Integration",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers
    
    def _generate_cmd_id(self) -> int:
        """Generate a unique command ID for device control."""
        # Generate a random number (similar to the example: 67902906)
        # In production, might want to use timestamp-based ID
        return random.randint(10000000, 99999999)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request with retry logic."""
        session = await self._get_session()
        last_exception: Exception | None = None
        
        for attempt in range(MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    response = await session.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = await session.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Check for auth errors
                if response.status == 401:
                    _LOGGER.debug("Got 401, attempting re-authentication...")
                    await self.async_authenticate()
                    # Update headers with new token
                    if "headers" in kwargs:
                        kwargs["headers"] = self._get_headers()
                    continue
                
                # For server errors, retry with backoff
                if response.status >= 500:
                    _LOGGER.warning(
                        "Server error %s on attempt %d/%d for %s",
                        response.status,
                        attempt + 1,
                        MAX_RETRIES,
                        url,
                    )
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                        await asyncio.sleep(delay)
                        continue
                
                return response
                
            except aiohttp.ClientError as err:
                last_exception = err
                _LOGGER.warning(
                    "Network error on attempt %d/%d for %s: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    url,
                    err,
                )
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                    await asyncio.sleep(delay)
                continue
            except asyncio.TimeoutError as err:
                last_exception = err
                _LOGGER.warning(
                    "Timeout on attempt %d/%d for %s",
                    attempt + 1,
                    MAX_RETRIES,
                    url,
                )
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                    await asyncio.sleep(delay)
                continue
        
        # All retries exhausted
        if last_exception:
            raise CannotConnect(f"Failed after {MAX_RETRIES} attempts: {last_exception}") from last_exception
        raise CannotConnect(f"Failed after {MAX_RETRIES} attempts")

    async def async_get_buildings(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Get list of buildings.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data.
        """
        if self._buildings is None or force_refresh:
            try:
                url = f"{self.daichi_api}/buildings"
                
                response = await self._request_with_retry("GET", url, headers=self._get_headers())
                async with response:
                    if response.status != 200:
                        error_text = await response.text()
                        _LOGGER.error(
                            "Failed to fetch buildings: %s - %s",
                            response.status,
                            error_text,
                        )
                        raise CannotConnect(f"Failed to fetch buildings: {response.status}")
                    
                    response_data = await response.json()
                    
                    # Data is in format {done: true, data: [...]}
                    if isinstance(response_data, dict) and "data" in response_data:
                        self._buildings = response_data["data"]
                    else:
                        self._buildings = response_data
                
                _LOGGER.debug("Fetched %d buildings", len(self._buildings or []))
            except CannotConnect:
                raise
            except Exception as err:
                _LOGGER.error("Failed to fetch buildings: %s", err)
                raise CannotConnect(f"Failed to fetch buildings: {err}") from err
        return self._buildings or []

    async def async_get_devices(
        self, 
        building_id: int | None = None, 
        force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Get list of devices.
        
        Devices are included in buildings response under "places" field.
        
        Args:
            building_id: Optional building ID. If provided, fetches devices from that building.
                        If None, fetches all devices from all buildings.
            force_refresh: If True, bypass cache and fetch fresh data.
        """
        if self._devices is None or force_refresh:
            try:
                # Get buildings (devices are included as "places" in building data)
                buildings = await self.async_get_buildings(force_refresh=force_refresh)
                all_devices = []
                
                for building in buildings:
                    # Filter by building_id if specified
                    if building_id and building.get("id") != building_id:
                        continue
                    
                    # Devices are in the "places" field of each building
                    places = building.get("places", [])
                    if places:
                        all_devices.extend(places)
                        _LOGGER.debug(
                            "Found %d devices in building '%s'",
                            len(places),
                            building.get("title", "Unknown"),
                        )
                
                self._devices = all_devices
                _LOGGER.debug("Fetched %d devices total", len(self._devices or []))
            except CannotConnect:
                raise
            except Exception as err:
                _LOGGER.error("Failed to fetch devices: %s", err)
                raise CannotConnect(f"Failed to fetch devices: {err}") from err
        return self._devices or []

    async def async_get_device_state(self, device_id: int) -> dict[str, Any]:
        """Get state of a specific device.
        
        The device info endpoint returns full device information including state.
        """
        try:
            # Device state is included in the device info endpoint
            url = f"{self.daichi_api}/devices/{device_id}"
            
            response = await self._request_with_retry("GET", url, headers=self._get_headers())
            async with response:
                if response.status == 404:
                    raise CannotConnect(f"Device {device_id} not found")
                elif response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(
                        "Failed to fetch device state: %s - %s",
                        response.status,
                        error_text,
                    )
                    raise CannotConnect(f"Failed to fetch device state: {response.status}")
                
                response_data = await response.json()
                
                # Data is in format {done: true, data: {...}}
                if isinstance(response_data, dict) and "data" in response_data:
                    device_data = response_data["data"]
                else:
                    device_data = response_data
                
                _LOGGER.debug("Fetched state for device %s", device_id)
                return device_data
        except CannotConnect:
            raise
        except Exception as err:
            _LOGGER.error("Failed to fetch device state: %s", err)
            raise CannotConnect(f"Failed to fetch device state: {err}") from err

    async def async_control_device(
        self,
        device_id: int,
        function_id: int,
        value: int | bool | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Control a device function.
        
        Args:
            device_id: Device ID to control
            function_id: Function ID (see FUNCTION_IDS.md for list)
            value: Value to set (can be int, bool, or None for some functions)
            parameters: Optional parameters for functions that require them
            
        API payload format:
            {
                "cmdId": <random_int>,
                "value": {
                    "functionId": <function_id>,
                    "isOn": true/false (for power/mode functions),
                    "value": <number> (for temperature),
                    "parameters": null or {...}
                },
                "conflictResolveData": null
            }
        """
        try:
            url = f"{self.daichi_api}/devices/{device_id}/ctrl"
            
            # Generate unique command ID
            cmd_id = self._generate_cmd_id()
            
            # Build the "value" object based on function type
            value_obj: dict[str, Any] = {
                "functionId": function_id,
                "parameters": parameters,
            }
            
            # Power (350) and mode functions (352=Cool, 353=Heat, etc.) use "isOn"
            # Temperature (351) and fan speed use "value"
            if function_id == FUNCTION_ID_POWER:
                # Power on/off uses isOn
                value_obj["isOn"] = bool(value) if value is not None else True
            elif function_id in (FUNCTION_ID_COOL, FUNCTION_ID_HEAT, FUNCTION_ID_AUTO, 
                                 FUNCTION_ID_DRY, FUNCTION_ID_FAN):
                # Mode functions use isOn: true to activate
                value_obj["isOn"] = True
            elif function_id == FUNCTION_ID_TEMPERATURE:
                # Temperature uses value
                value_obj["value"] = value
            elif function_id == FUNCTION_ID_FAN_SPEED:
                # Fan speed uses value
                value_obj["value"] = value
            elif function_id == FUNCTION_ID_FAN_SPEED_AUTO:
                # Auto fan speed uses isOn
                value_obj["isOn"] = True
            else:
                # For other functions (presets, swing, etc.) use isOn
                # as they are toggle-style functions
                if isinstance(value, bool):
                    value_obj["isOn"] = value
                elif value is not None:
                    value_obj["value"] = value
                else:
                    value_obj["isOn"] = True
            
            # Build request payload according to API structure
            payload = {
                "cmdId": cmd_id,
                "value": value_obj,
                "conflictResolveData": None,
            }
            
            # Add query parameter
            url_with_params = f"{url}?ignoreConflicts=false"
            
            response = await self._request_with_retry(
                "POST", url_with_params, json=payload, headers=self._get_headers()
            )
            async with response:
                if response.status == 409:
                    # Conflict - need to resolve (e.g., cancel Comfortable Sleep)
                    conflict_data = await response.json()
                    _LOGGER.debug(
                        "Conflict detected for device %s: %s",
                        device_id,
                        conflict_data.get("title", "Unknown conflict"),
                    )
                    
                    # Extract conflictResolveData from the response
                    actions = conflict_data.get("actions", [])
                    for action in actions:
                        if action.get("behaviour") == "REQUEST" and action.get("conflictResolveData"):
                            conflict_resolve_data = action["conflictResolveData"]
                            _LOGGER.info(
                                "Auto-resolving conflict for device %s: %s",
                                device_id,
                                conflict_data.get("title"),
                            )
                            
                            # Retry the request with conflictResolveData
                            payload["conflictResolveData"] = conflict_resolve_data
                            retry_response = await self._request_with_retry(
                                "POST", url_with_params, json=payload, headers=self._get_headers()
                            )
                            async with retry_response:
                                if retry_response.status != 200:
                                    retry_error = await retry_response.text()
                                    _LOGGER.error(
                                        "Failed to resolve conflict: %s - %s",
                                        retry_response.status,
                                        retry_error,
                                    )
                                    raise CannotConnect(f"Failed to resolve conflict: {retry_response.status}")
                                
                                result = await retry_response.json()
                                _LOGGER.debug(
                                    "Conflict resolved for device %s, function %s",
                                    device_id,
                                    function_id,
                                )
                                return result
                    
                    # No resolvable action found
                    _LOGGER.error(
                        "Cannot resolve conflict for device %s: %s",
                        device_id,
                        conflict_data.get("title"),
                    )
                    raise CannotConnect(f"Conflict cannot be resolved: {conflict_data.get('title')}")
                
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(
                        "Failed to control device: %s - %s",
                        response.status,
                        error_text,
                    )
                    raise CannotConnect(f"Failed to control device: {response.status}")
                
                result = await response.json()
                
                # Check if command was successful
                if not result.get("done", False):
                    errors = result.get("errors")
                    update_required = result.get("updateRequired", False)
                    
                    if errors:
                        _LOGGER.warning(
                            "Device control command not done. Errors: %s",
                            errors,
                        )
                    
                    if update_required:
                        _LOGGER.info(
                            "Device %s requires update after control command",
                            device_id,
                        )
                
                _LOGGER.debug(
                    "Controlled device %s, function %s, value %s",
                    device_id,
                    function_id,
                    value,
                )
                return result
        except CannotConnect:
            raise
        except Exception as err:
            _LOGGER.error("Failed to control device: %s", err)
            raise CannotConnect(f"Failed to control device: {err}") from err
    
    def clear_cache(self) -> None:
        """Clear cached data (buildings and devices)."""
        self._buildings = None
        self._devices = None
        _LOGGER.debug("Cleared API cache")

