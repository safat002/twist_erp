"""Compatibility exports for metadata services.

This module re-exports the legacy functions and classes expected at
`apps.metadata.services` from `_legacy.py`.
"""

from .._legacy import MetadataScope, create_metadata_version, get_active_metadata, resolve_metadata  # noqa: F401

