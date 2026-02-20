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
    DEFAULT_CLIENT_ID,
)
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)

MAX_RETRIES = 3
RETRY_DELAY = 1.0
RETRY_BACKOFF = 2.0


class DaichiApiClient:
    """Client for Daichi Comfort Cloud API."""

    def __init__(
        self,
        username: str,
        password: str,
        daichi_api: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        base_url = daichi_api or "https://web.daichicloud.ru/api/v4"
        self.daichi_api = base_url.rstrip("/")
        self._external_session = session
        self._own_session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._buildings: list[dict[str, Any]] | None = None
        self._devices: list[dict[str, Any]] | None = None

    @property
    def is_authenticated(self) -> bool:
        """Return True if the client has an access token."""
        return self._access_token is not None

    def _get_session(self) -> aiohttp.ClientSession:
        """Get the aiohttp session."""
        if self._external_session is not None:
            return self._external_session
        if self._own_session is None:
            self._own_session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)
        return self._own_session

    async def async_close(self) -> None:
        """Close the self-managed session (no-op for external sessions)."""
        if self._own_session:
            await self._own_session.close()
            self._own_session = None

    async def async_authenticate(self) -> bool:
        """Authenticate with Daichi API using two-step process."""
        try:
            session = self._get_session()
            _LOGGER.debug("Authenticating with Daichi API")

            credentials_url = f"{self.daichi_api}/user/credentials"
            credentials_payload = {"email": self.username}

            async with session.post(
                credentials_url,
                json=credentials_payload,
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
            ) as credentials_response:
                if credentials_response.status not in (200, 201):
                    error_text = await credentials_response.text()
                    _LOGGER.error(
                        "Email check failed: %s - %s",
                        credentials_response.status,
                        error_text,
                    )
                    raise InvalidAuth("Email check failed")

            token_url = f"{self.daichi_api}/token"
            token_payload = {
                "email": self.username,
                "password": self.password,
                "clientId": DEFAULT_CLIENT_ID,
            }

            async with session.post(
                token_url,
                json=token_payload,
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
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

                token_data = data.get("data", {})
                self._access_token = (
                    token_data.get("access_token")
                    or token_data.get("token")
                    or data.get("access_token")
                    or data.get("token")
                    or data.get("accessToken")
                    or data.get("access")
                )

                if self._access_token and self._access_token.startswith("Bearer "):
                    self._access_token = self._access_token[7:]

                if not self._access_token:
                    cookies = token_response.cookies
                    for cookie in cookies:
                        if "token" in cookie.key.lower() or "auth" in cookie.key.lower():
                            self._access_token = cookie.value
                            break

                if not self._access_token:
                    _LOGGER.warning(
                        "No access token in response. Response data: %s", data,
                    )

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
        return random.randint(10000000, 99999999)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request with retry logic."""
        session = self._get_session()
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    response = await session.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = await session.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if response.status == 401:
                    response.close()
                    _LOGGER.debug("Got 401, attempting re-authentication...")
                    await self.async_authenticate()
                    if "headers" in kwargs:
                        kwargs["headers"] = self._get_headers()
                    continue

                if response.status >= 500:
                    response.close()
                    _LOGGER.warning(
                        "Server error %s on attempt %d/%d for %s",
                        response.status, attempt + 1, MAX_RETRIES, url,
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
                    attempt + 1, MAX_RETRIES, url, err,
                )
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                    await asyncio.sleep(delay)
                continue
            except asyncio.TimeoutError as err:
                last_exception = err
                _LOGGER.warning(
                    "Timeout on attempt %d/%d for %s",
                    attempt + 1, MAX_RETRIES, url,
                )
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                    await asyncio.sleep(delay)
                continue

        if last_exception:
            raise CannotConnect(
                f"Failed after {MAX_RETRIES} attempts: {last_exception}"
            ) from last_exception
        raise CannotConnect(f"Failed after {MAX_RETRIES} attempts")

    async def async_get_buildings(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Get list of buildings."""
        if self._buildings is not None and not force_refresh:
            return self._buildings

        try:
            url = f"{self.daichi_api}/buildings"
            response = await self._request_with_retry("GET", url, headers=self._get_headers())
            async with response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Failed to fetch buildings: %s - %s", response.status, error_text)
                    raise CannotConnect(f"Failed to fetch buildings: {response.status}")

                response_data = await response.json()
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
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Get list of devices from buildings response."""
        if self._devices is not None and not force_refresh:
            return self._devices

        try:
            buildings = await self.async_get_buildings(force_refresh=force_refresh)
            all_devices: list[dict[str, Any]] = []

            for building in buildings:
                if building_id and building.get("id") != building_id:
                    continue
                places = building.get("places", [])
                if places:
                    all_devices.extend(places)
                    _LOGGER.debug(
                        "Found %d devices in building '%s'",
                        len(places), building.get("title", "Unknown"),
                    )

            self._devices = all_devices
            _LOGGER.debug("Fetched %d devices total", len(self._devices))
        except CannotConnect:
            raise
        except Exception as err:
            _LOGGER.error("Failed to fetch devices: %s", err)
            raise CannotConnect(f"Failed to fetch devices: {err}") from err
        return self._devices or []

    async def async_get_device_state(self, device_id: int) -> dict[str, Any]:
        """Get state of a specific device."""
        try:
            url = f"{self.daichi_api}/devices/{device_id}"
            response = await self._request_with_retry("GET", url, headers=self._get_headers())
            async with response:
                if response.status == 404:
                    raise CannotConnect(f"Device {device_id} not found")
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Failed to fetch device state: %s - %s", response.status, error_text)
                    raise CannotConnect(f"Failed to fetch device state: {response.status}")

                response_data = await response.json()
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

    async def async_get_device_states(self, device_ids: list[int]) -> dict[int, dict[str, Any]]:
        """Get states for multiple devices in parallel."""
        async def _fetch_one(did: int) -> tuple[int, dict[str, Any] | None]:
            try:
                data = await self.async_get_device_state(did)
                return (did, data)
            except CannotConnect as err:
                _LOGGER.warning("Failed to fetch info for device %s: %s", did, err)
                return (did, None)
            except Exception as err:
                _LOGGER.exception("Unexpected error fetching device %s: %s", did, err)
                return (did, None)

        results = await asyncio.gather(*[_fetch_one(did) for did in device_ids])
        return {did: data for did, data in results if data is not None}

    async def async_control_device(
        self,
        device_id: int,
        function_id: int,
        value: int | bool | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Control a device function."""
        try:
            url = f"{self.daichi_api}/devices/{device_id}/ctrl"
            cmd_id = self._generate_cmd_id()

            value_obj: dict[str, Any] = {
                "functionId": function_id,
                "parameters": parameters,
            }

            if function_id == FUNCTION_ID_POWER:
                value_obj["isOn"] = bool(value) if value is not None else True
            elif function_id in (
                FUNCTION_ID_COOL, FUNCTION_ID_HEAT, FUNCTION_ID_AUTO,
                FUNCTION_ID_DRY, FUNCTION_ID_FAN,
            ):
                value_obj["isOn"] = True
            elif function_id == FUNCTION_ID_TEMPERATURE:
                value_obj["value"] = value
            elif function_id == FUNCTION_ID_FAN_SPEED:
                value_obj["value"] = value
            elif function_id == FUNCTION_ID_FAN_SPEED_AUTO:
                value_obj["isOn"] = True
            else:
                if isinstance(value, bool):
                    value_obj["isOn"] = value
                elif value is not None:
                    value_obj["value"] = value
                else:
                    value_obj["isOn"] = True

            payload = {
                "cmdId": cmd_id,
                "value": value_obj,
                "conflictResolveData": None,
            }

            url_with_params = f"{url}?ignoreConflicts=false"
            response = await self._request_with_retry(
                "POST", url_with_params, json=payload, headers=self._get_headers(),
            )
            async with response:
                if response.status == 409:
                    conflict_data = await response.json()
                    _LOGGER.debug(
                        "Conflict detected for device %s: %s",
                        device_id, conflict_data.get("title", "Unknown conflict"),
                    )

                    actions = conflict_data.get("actions", [])
                    for action in actions:
                        if action.get("behaviour") == "REQUEST" and action.get("conflictResolveData"):
                            conflict_resolve_data = action["conflictResolveData"]
                            _LOGGER.info(
                                "Auto-resolving conflict for device %s: %s",
                                device_id, conflict_data.get("title"),
                            )
                            payload["conflictResolveData"] = conflict_resolve_data
                            retry_response = await self._request_with_retry(
                                "POST", url_with_params, json=payload, headers=self._get_headers(),
                            )
                            async with retry_response:
                                if retry_response.status != 200:
                                    retry_error = await retry_response.text()
                                    _LOGGER.error(
                                        "Failed to resolve conflict: %s - %s",
                                        retry_response.status, retry_error,
                                    )
                                    raise CannotConnect(
                                        f"Failed to resolve conflict: {retry_response.status}"
                                    )
                                return await retry_response.json()

                    _LOGGER.error(
                        "Cannot resolve conflict for device %s: %s",
                        device_id, conflict_data.get("title"),
                    )
                    raise CannotConnect(
                        f"Conflict cannot be resolved: {conflict_data.get('title')}"
                    )

                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Failed to control device: %s - %s", response.status, error_text)
                    raise CannotConnect(f"Failed to control device: {response.status}")

                result = await response.json()

                if not result.get("done", False):
                    errors = result.get("errors")
                    if errors:
                        _LOGGER.warning("Device control command not done. Errors: %s", errors)
                    if result.get("updateRequired", False):
                        _LOGGER.info("Device %s requires update after control command", device_id)

                _LOGGER.debug("Controlled device %s, function %s, value %s", device_id, function_id, value)
                return result
        except CannotConnect:
            raise
        except Exception as err:
            _LOGGER.error("Failed to control device: %s", err)
            raise CannotConnect(f"Failed to control device: {err}") from err
