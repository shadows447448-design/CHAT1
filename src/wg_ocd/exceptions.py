"""Custom exceptions for wg-ocd."""


class WGOCDError(Exception):
    """Base exception for domain-level errors."""


class ValidationError(WGOCDError):
    """Raised when user input is invalid."""


class CommandExecutionError(WGOCDError):
    """Raised when a system command or workflow step fails."""
