"""Exceptions for the Daichi integration."""


class DaichiException(Exception):
    """Base exception for Daichi errors."""


class CannotConnect(DaichiException):
    """Error to indicate we cannot connect."""


class InvalidAuth(DaichiException):
    """Error to indicate there is invalid auth."""


class DeviceNotFound(DaichiException):
    """Error to indicate device not found."""

