"""MiOS offline direct-fetch web-extract plugin -- auto-loaded backend.

See provider.py for the why. Registers MiosFetchProvider as a web provider;
config.yaml's web.extract_backend: miosfetch selects it for web_extract calls.
"""
from __future__ import annotations

from plugins.web.miosfetch.provider import MiosFetchProvider


def register(ctx) -> None:
    """Register the MiOS direct-fetch extract provider with the plugin context."""
    ctx.register_web_search_provider(MiosFetchProvider())
