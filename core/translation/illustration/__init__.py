"""
Illustration Generation Module

This module provides functionality to generate illustrations for translation segments
using Google's Gemini image generation API.
"""

from .generator import IllustrationGenerator
from .world_atmosphere_provider import WorldAtmosphereProvider

__all__ = ['IllustrationGenerator', 'WorldAtmosphereProvider']

# Version information
__version__ = '2.0.0'