"""Export workspace data as a zip archive."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from config_loader import resolve_data_dir

EXPORT_FORMAT_VERSION = 1
EXPORT_MANIFEST_NAME = "apidog-export.json"
EXPORT_INCLUDE_DIRS = ("collections", "environments")
EXPORT_INCLUDE_FILES = ("workspace.json",)


def build_workspace_export_zip() -> tuple[bytes, str]:
    data_dir = resolve_data_dir()
    if not data_dir.exists():
        raise FileNotFoundError(f"数据目录不存在: {data_dir}")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write_manifest(archive)
        for relative_name in EXPORT_INCLUDE_FILES:
            file_path = data_dir / relative_name
            if file_path.is_file():
                archive.write(file_path, arcname=relative_name)
        for dirname in EXPORT_INCLUDE_DIRS:
            folder = data_dir / dirname
            if not folder.is_dir():
                continue
            for file_path in sorted(folder.rglob("*")):
                if file_path.is_file():
                    archive.write(file_path, arcname=str(file_path.relative_to(data_dir)))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"ApiDog-workspace-{stamp}.zip"
    return buffer.getvalue(), filename


def _write_manifest(archive: zipfile.ZipFile) -> None:
    payload = (
        "{\n"
        f'  "format": "apidog-workspace",\n'
        f'  "version": {EXPORT_FORMAT_VERSION}\n'
        "}\n"
    )
    archive.writestr(EXPORT_MANIFEST_NAME, payload)
