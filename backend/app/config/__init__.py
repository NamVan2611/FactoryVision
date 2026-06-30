"""Configuration package.

Exposes the application :class:`Settings` singleton via :func:`get_settings`.
"""

from app.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
