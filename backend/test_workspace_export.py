"""Tests for workspace export zip."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import storage
from app_constants import ENV_DATA_DIR
from workspace_export import EXPORT_MANIFEST_NAME, build_workspace_export_zip


def test_build_workspace_export_zip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    storage.ensure_data_layout()
    storage.create_project("demo-export")

    payload, filename = build_workspace_export_zip()
    assert filename.startswith("ApiDog-workspace-")
    assert filename.endswith(".zip")

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert EXPORT_MANIFEST_NAME in names
        assert "workspace.json" in names
        assert any(name.startswith("collections/") for name in names)
        assert any(name.startswith("environments/") for name in names)
