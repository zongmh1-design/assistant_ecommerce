"""Replaceable media generator contracts and local implementations."""

from app.generation.media_generator import MediaGenerator, MediaGeneratorError
from app.generation.mock_generators import MockImageGenerator, MockVideoGenerator

__all__ = [
    "MediaGenerator",
    "MediaGeneratorError",
    "MockImageGenerator",
    "MockVideoGenerator",
]
