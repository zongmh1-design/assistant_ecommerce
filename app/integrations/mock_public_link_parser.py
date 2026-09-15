"""Deterministic demonstration parser; it performs no network request."""

from decimal import Decimal
from urllib.parse import urlparse

from app.integrations.public_link_parser import (
    PublicLinkParseResult,
    PublicLinkParserError,
)
from app.models.store import Platform


class MockPublicLinkParser:
    def parse(self, source_url: str) -> PublicLinkParseResult:
        normalized_url = source_url.rstrip("/")
        if normalized_url == "https://example.com/fail":
            raise PublicLinkParserError("Mock demo parser failed for the configured test URL")

        slug = urlparse(normalized_url).path.rstrip("/").split("/")[-1] or "sample-product"
        if slug == "phone-case-001":
            return PublicLinkParseResult(
                name="轻薄磁吸手机壳（Mock 演示）",
                platform=Platform.OTHER,
                price=Decimal("59.90"),
                title="轻薄磁吸防摔手机壳（Mock 演示数据）",
                main_image="https://example.com/mock-assets/phone-case-001.jpg",
                selling_points=["磁吸", "轻薄", "防摔"],
                review_keywords=["磁吸", "手感", "防护"],
                sales_hint="Mock 演示销量提示，不代表真实平台数据",
                data_source="mock_demo",
            )

        return PublicLinkParseResult(
            name=f"{slug} 演示竞品",
            platform=Platform.OTHER,
            price=Decimal("99.00"),
            title=f"{slug} 公开链接解析预览（Mock 演示）",
            main_image=f"https://example.com/mock-assets/{slug}.jpg",
            selling_points=["示例卖点一", "示例卖点二", "示例卖点三"],
            review_keywords=["示例关键词"],
            sales_hint="Mock 演示数据",
            data_source="mock_demo",
        )
