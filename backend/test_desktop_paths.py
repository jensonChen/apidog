"""Tests for blank workspace bootstrap and data-dir resolution."""

from __future__ import annotations

import os
from pathlib import Path

import config_loader
import storage
from app_constants import ENV_DATA_DIR, ENV_USE_APPDATA


def test_resolve_data_dir_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.delenv(ENV_USE_APPDATA, raising=False)
    assert config_loader.resolve_data_dir() == tmp_path.resolve()


def test_ensure_data_layout_starts_blank(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    storage.ensure_data_layout()
    index = storage.load_workspace_index()
    assert index.projects == []
    assert index.active_project_id == ""
    environments = storage.list_environments()
    assert len(environments) == 1
    assert environments[0].id == "default"
    assert environments[0].variables == {}


def test_ensure_data_layout_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    storage.ensure_data_layout()
    storage.create_project("demo")
    storage.ensure_data_layout()
    index = storage.load_workspace_index()
    assert len(index.projects) == 1
    assert index.projects[0]["name"] == "demo"
