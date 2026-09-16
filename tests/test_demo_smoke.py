"""The smoke runner uses only HTTP calls even under the SQLite test app."""

from app.models.user import UserRole
from scripts.smoke_test_demo_flow import run_smoke


def test_http_smoke_runs_complete_flow(client, auth_headers_factory):
    auth_headers_factory(UserRole.ADMIN)
    result = run_smoke(client, "admin_1", "RolePassword123!")
    assert result["status"] == "PASS"
    assert result["product_id"] > 0
    assert result["review_report_id"] > 0
