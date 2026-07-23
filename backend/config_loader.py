"""Load runtime config and resolve data / resource directories."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from app_constants import (
    APP_DATA_FOLDER_NAME,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_SECONDS,
    ENV_DATA_DIR,
    ENV_DESKTOP_SHELL,
    ENV_DESKTOP_SHELL_TRUE,
    ENV_USE_APPDATA,
    ENV_USE_APPDATA_TRUE,
    FRONTEND_DEV_PORT,
)

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resolve_resource_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return ROOT_DIR


def should_use_appdata() -> bool:
    if os.environ.get(ENV_DATA_DIR):
        return False
    if is_frozen():
        return True
    return os.environ.get(ENV_USE_APPDATA) == ENV_USE_APPDATA_TRUE


def resolve_data_dir() -> Path:
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        return Path(override).expanduser().resolve()
    if should_use_appdata():
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("环境变量 APPDATA 未设置，无法定位用户数据目录")
        return Path(appdata) / APP_DATA_FOLDER_NAME
    return ROOT_DIR / "data"


def resolve_frontend_dist() -> Path:
    resource_root = resolve_resource_root()
    return resource_root / "frontend" / "dist"


def resolve_app_icon() -> Path | None:
    resource_root = resolve_resource_root()
    candidates = [
        resource_root / "frontend" / "public" / "app.ico",
        resource_root / "frontend" / "dist" / "app.ico",
        resource_root / "frontend" / "public" / "favicon.png",
        resource_root / "frontend" / "dist" / "favicon.png",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def resolve_config_path(data_dir: Path | None = None) -> Path:
    base = data_dir if data_dir is not None else resolve_data_dir()
    return base / "config.json"


DEFAULT_CONFIG = {
    "port": DEFAULT_PORT,
    "default_timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
    "frontend_dev_port": FRONTEND_DEV_PORT,
    "desktop_shell": False,
}


def load_config() -> dict:
    data_dir = resolve_data_dir()
    config_path = resolve_config_path(data_dir)
    if not config_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        merged = dict(DEFAULT_CONFIG)
    else:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"配置文件格式无效: {config_path}")
        merged = dict(DEFAULT_CONFIG)
        merged.update(raw)

    merged["desktop_shell"] = (
        os.environ.get(ENV_DESKTOP_SHELL) == ENV_DESKTOP_SHELL_TRUE or bool(merged.get("desktop_shell"))
    )
    return merged


# Backward-compatible module aliases used across the backend.
DATA_DIR = resolve_data_dir()
CONFIG_PATH = resolve_config_path(DATA_DIR)
