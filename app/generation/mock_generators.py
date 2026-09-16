"""Deterministic image/video generators; no files or network are used."""

from typing import Any

from app.schemas.generation_job import MediaGenerationInput


class MockImageGenerator:
    def generate(self, generation_input: MediaGenerationInput) -> dict[str, Any]:
        return {
            "asset_type": "image",
            "mock": True,
            "url": f"mock://images/job-{generation_input.job_id}.png",
            "width": 1024,
            "height": 1024,
            "generator": "mock_image_generator",
        }


class MockVideoGenerator:
    def generate(self, generation_input: MediaGenerationInput) -> dict[str, Any]:
        return {
            "asset_type": "video",
            "mock": True,
            "url": f"mock://videos/job-{generation_input.job_id}.mp4",
            "duration_sec": 15,
            "generator": "mock_video_generator",
        }
