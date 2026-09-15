"""Replaceable contract for legal parsing of publicly accessible product links."""

from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.store import Platform


class PublicLinkParseResult(BaseModel):
    name: str
    platform: Platform
    price: Decimal | None
    title: str | None
    main_image: HttpUrl | None
    selling_points: list[str]
    review_keywords: list[str] = Field(default_factory=list)
    sales_hint: str | None = None
    data_source: str

    model_config = ConfigDict(extra="forbid")


class PublicLinkParserError(Exception):
    """A controlled parser failure safe to expose through task error state."""


class PublicLinkParser(Protocol):
    def parse(self, source_url: str) -> PublicLinkParseResult: ...
