"""Domain error types."""

from __future__ import annotations


class EhmError(Exception):
    """Base error for the EHM system."""


class DataQualityError(EhmError):
    """Raised when input data fails a mandatory quality gate."""


class PolicyViolationError(EhmError):
    """Raised when a recommendation attempts to cross the advisory-only boundary."""
