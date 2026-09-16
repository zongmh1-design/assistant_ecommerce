"""HTTP-only smoke test for the complete single-product demo flow."""

from __future__ import annotations

import argparse
import getpass
import http.client
import json
import os
import sys
from typing import Any, Protocol
from urllib.parse import urljoin, urlsplit


class HttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...
    def post(self, url: str, **kwargs: Any) -> Any: ...


class StdlibResponse:
    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return json.loads(self._body.decode("utf-8"))


class StdlibClient:
    """Small HTTP-only client for local smoke tests without SDK coupling."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

    def __enter__(self) -> "StdlibClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get(self, url: str, **kwargs: Any) -> StdlibResponse:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> StdlibResponse:
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs: Any) -> StdlibResponse:
        parsed = urlsplit(urljoin(self.base_url, url.lstrip("/")))
        connection_class = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_class(
            parsed.hostname,
            parsed.port,
            timeout=self.timeout,
        )
        headers = dict(kwargs.get("headers") or {})
        payload = kwargs.get("json")
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return StdlibResponse(response.status, response.read())
        finally:
            connection.close()


class SmokeFailure(RuntimeError):
    def __init__(self, step: str, message: str) -> None:
        super().__init__(message)
        self.step = step


def run_smoke(client: HttpClient, username: str, password: str) -> dict[str, Any]:
    step = "login"
    login = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    _expect(login, 200, step)
    token = login.json().get("access_token")
    if not token:
        raise SmokeFailure(step, "login response did not contain an access token")
    headers = {"Authorization": f"Bearer {token}"}

    step = "current user"
    _expect(client.get("/api/v1/auth/me", headers=headers), 200, step)

    step = "demo data"
    demo_response = client.post("/api/v1/workspace/demo-data", headers=headers)
    _expect(demo_response, 200, step)
    demo = demo_response.json()
    if demo.get("status") not in {"completed", "already_exists"}:
        raise SmokeFailure(
            demo.get("failed_step") or step,
            f"demo initialization returned {demo.get('error_code') or 'partial'}",
        )
    product_id = demo["product_id"]

    checks: list[tuple[str, Any, Any]] = [
        ("store", client.get(f"/api/v1/stores/{demo['store_id']}", headers=headers), lambda b: b["id"] == demo["store_id"]),
        ("product", client.get(f"/api/v1/products/{product_id}", headers=headers), lambda b: b["id"] == product_id),
        ("competitors", client.get(f"/api/v1/products/{product_id}/competitors", headers=headers), lambda b: b["total"] >= 2),
        ("diagnosis", client.get(f"/api/v1/products/{product_id}/diagnoses", headers=headers), lambda b: b["total"] >= 1),
        ("creative plans", client.get(f"/api/v1/products/{product_id}/creative-plans", headers=headers), _valid_plans),
        ("performance records", client.get(f"/api/v1/products/{product_id}/performance-records", headers=headers), lambda b: b["total"] >= 3),
        ("review report", client.get(f"/api/v1/products/{product_id}/review-reports/{demo['review_report_id']}", headers=headers), lambda b: b["id"] == demo["review_report_id"]),
    ]
    for name, response, predicate in checks:
        _expect(response, 200, name)
        if not predicate(response.json()):
            raise SmokeFailure(name, "response did not satisfy the demo invariant")

    step = "sku inventory"
    skus_response = client.get(f"/api/v1/products/{product_id}/skus", headers=headers)
    _expect(skus_response, 200, step)
    skus = skus_response.json()["items"]
    if len(skus) < 2:
        raise SmokeFailure(step, "expected at least two SKUs")
    for sku in skus:
        inventory = client.get(f"/api/v1/skus/{sku['id']}/inventory", headers=headers)
        movements = client.get(f"/api/v1/skus/{sku['id']}/inventory/movements", headers=headers)
        _expect(inventory, 200, step)
        _expect(movements, 200, step)
        if inventory.json()["stock_qty"] <= 0 or movements.json()["total"] < 2:
            raise SmokeFailure(step, f"SKU {sku['id']} has no adjusted demo inventory")

    step = "generation jobs"
    for job_id in (demo["image_job_id"], demo["video_job_id"]):
        response = client.get(
            f"/api/v1/products/{product_id}/generation-jobs/{job_id}", headers=headers
        )
        _expect(response, 200, step)
        if response.json()["job_status"] != "succeeded":
            raise SmokeFailure(step, f"job {job_id} is not succeeded")

    step = "approved assets"
    for asset_id in (demo["approved_image_asset_id"], demo["approved_video_asset_id"]):
        response = client.get(
            f"/api/v1/products/{product_id}/assets/{asset_id}", headers=headers
        )
        _expect(response, 200, step)
        if response.json()["review_status"] != "approved":
            raise SmokeFailure(step, f"asset {asset_id} is not approved")

    step = "promotion link"
    link_response = client.get(
        f"/api/v1/products/{product_id}/promotion-links/{demo['promotion_link_id']}",
        headers=headers,
    )
    _expect(link_response, 200, step)
    link = link_response.json()
    if link["status"] != "active":
        raise SmokeFailure(step, "promotion link is not active")
    redirect = client.get(
        f"/api/v1/r/{link['tracking_code']}", follow_redirects=False,
        headers={"User-Agent": "DemoSmokeTest/1.0"},
    )
    _expect(redirect, 302, "promotion redirect")

    step = "ad recommendation"
    recommendation = client.get(
        f"/api/v1/products/{product_id}/ad-recommendations/{demo['ad_recommendation_id']}",
        headers=headers,
    )
    _expect(recommendation, 200, step)
    if recommendation.json()["confirm_status"] != "confirmed":
        raise SmokeFailure(step, "ad recommendation is not confirmed")

    step = "ad experiment"
    experiment = client.get(
        f"/api/v1/products/{product_id}/ad-experiments/{demo['ad_experiment_id']}",
        headers=headers,
    )
    _expect(experiment, 200, step)
    if experiment.json()["experiment_status"] != "finished":
        raise SmokeFailure(step, "ad experiment is not finished")

    return {
        "status": "PASS",
        "product_id": product_id,
        "review_report_id": demo["review_report_id"],
        "demo_status": demo["status"],
    }


def _expect(response: Any, expected_status: int, step: str) -> None:
    if response.status_code != expected_status:
        raise SmokeFailure(
            step, f"expected HTTP {expected_status}, got HTTP {response.status_code}"
        )


def _valid_plans(body: dict[str, Any]) -> bool:
    items = body.get("items", [])
    selected = {item["plan_type"] for item in items if item["status"] == "selected"}
    return len(items) >= 6 and selected == {"main_image", "video_script"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the backend demo flow through HTTP only")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEMO_BASE_URL", "http://127.0.0.1:8000"),
        help="Running FastAPI base URL",
    )
    parser.add_argument("--username", default=os.getenv("DEMO_ADMIN_USERNAME"))
    args = parser.parse_args()
    username = args.username or input("Admin username: ").strip()
    password = os.getenv("DEMO_ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    try:
        with StdlibClient(base_url=args.base_url, timeout=30.0) as client:
            result = run_smoke(client, username, password)
    except SmokeFailure as exc:
        print(f"FAIL - {exc.step}: {exc}")
        return 1
    except Exception as exc:
        print(f"FAIL - connection/runtime: {type(exc).__name__}")
        return 1
    print(
        f"PASS - product_id={result['product_id']} "
        f"review_report_id={result['review_report_id']} "
        f"demo_status={result['demo_status']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
