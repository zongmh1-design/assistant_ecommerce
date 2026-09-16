"""Central FastAPI dependencies for replaceable generation providers."""

from app.generation.media_generator import MediaGenerator
from app.generation.mock_generators import MockImageGenerator, MockVideoGenerator


def get_image_generator() -> MediaGenerator:
    return MockImageGenerator()


def get_video_generator() -> MediaGenerator:
    return MockVideoGenerator()
