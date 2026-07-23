"""Tests for smart workspace import."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import storage
from app_constants import ENV_DATA_DIR
from workspace_export import EXPORT_MANIFEST_NAME, build_workspace_export_zip
from workspace_import import import_json_payload, import_workspace_zip


def test_import_apidog_project_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    storage.ensure_data_layout()
    payload = {
        "id": "proj-old",
        "name": "本地项目",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "tree": [
            {
                "type": "request",
                "id": "req-1",
                "name": "ping",
                "method": "GET",
                "url": "http://127.0.0.1/health",
                "headers": [],
                "body_type": "none",
                "body": "",
                "follow_redirects": True,
            }
        ],
    }
    result = import_json_payload(payload)
    assert result["kind"] == "apidog_project"
    assert result["project"] is not None
    assert result["project"].name == "本地项目"
    assert len(result["project"].tree) == 1
    index = storage.load_workspace_index()
    assert index.active_project_id == result["project"].id


def test_import_postman_like_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    storage.ensure_data_layout()
    payload = {
        "info": {"name": "Demo Collection"},
        "item": [
            {
                "name": "health",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": "http://127.0.0.1/starter",
                },
            }
        ],
    }
    result = import_json_payload(payload)
    assert result["kind"] == "postman"
    assert result["project"].name == "Demo Collection"
    assert len(result["project"].tree) == 1


def test_import_workspace_zip_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path / "src"))
    storage.ensure_data_layout()
    storage.create_project("zip-demo")
    payload, _filename = build_workspace_export_zip()

    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path / "dst"))
    storage.ensure_data_layout()
    result = import_workspace_zip(payload)
    assert result["kind"] == "apidog_workspace"
    assert result["imported_projects"] >= 1
    assert storage.list_projects()
