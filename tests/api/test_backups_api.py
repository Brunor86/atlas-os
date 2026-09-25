from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.services.backup_intelligence.inventory import BackupInventoryService


def test_backups_api_is_read_only_and_returns_inventory(
    tmp_path,
    monkeypatch,
):
    from atlas.api import backups as api

    manifest = tmp_path / "backup-intelligence.json"
    manifest.write_text(
        '{"version": 1, "items": []}'
    )

    monkeypatch.setattr(
        api,
        "service",
        BackupInventoryService(
            manifest_path=manifest,
        ),
    )

    app = FastAPI()
    app.include_router(api.router)

    with TestClient(app) as client:
        response = client.get("/api/backups")
        post = client.post("/api/backups")

    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["items"] == []
    assert post.status_code == 405
