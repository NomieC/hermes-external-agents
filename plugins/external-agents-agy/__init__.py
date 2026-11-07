"""Discovered through the documented model-provider lifecycle."""
from providers import register_provider
from .provider_profile import AGYProfile

register_provider(AGYProfile())
