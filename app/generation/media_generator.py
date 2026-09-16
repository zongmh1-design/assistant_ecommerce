"""Small provider-neutral contract for one media generation attempt."""

from typing import Any, Protocol

from app.schemas.generation_job import MediaGenerationInput


class MediaGeneratorError(Exception):
    """Controlled generator failure suitable for the job error boundary."""


class MediaGenerator(Protocol):
    def generate(self, generation_input: MediaGenerationInput) -> dict[str, Any]: ...
