"""Import Postman collections or ApiDog native project/workspace files."""

from __future__ import annotations

import json
import uuid
import zipfile
from io import BytesIO
from typing import Any

from models import EnvironmentConfig, ProjectCollection
from postman_import import import_postman_collection
from storage import (
    DEFAULT_ENVIRONMENT_ID,
    ensure_data_layout,
    load_environment,
    load_workspace_index,
    register_project,
    save_environment,
    save_workspace_index,
)
from workspace_export import EXPORT_MANIFEST_NAME

IMPORT_KIND_POSTMAN = "postman"
IMPORT_KIND_APIDOG_PROJECT = "apidog_project"
IMPORT_KIND_APIDOG_WORKSPACE = "apidog_workspace"


def detect_json_import_kind(payload: dict[str, Any]) -> str:
    if _looks_like_postman(payload):
        return IMPORT_KIND_POSTMAN
    if _looks_like_apidog_project(payload):
        return IMPORT_KIND_APIDOG_PROJECT
    raise ValueError(
        "无法识别文件格式。请导入：Postman Collection(.json)、ApiDog 项目(.json)，或 ApiDog 导出包(.zip)"
    )


def _looks_like_postman(payload: dict[str, Any]) -> bool:
    if not isinstance(payload.get("info"), dict):
        return False
    return isinstance(payload.get("item"), list)


def _looks_like_apidog_project(payload: dict[str, Any]) -> bool:
    if not isinstance(payload.get("name"), str):
        return False
    if not isinstance(payload.get("tree"), list):
        return False
    return True


def import_apidog_project_payload(payload: dict[str, Any]) -> ProjectCollection:
    project = ProjectCollection.model_validate(payload)
    project.id = f"proj-{uuid.uuid4().hex[:8]}"
    return register_project(project)


def import_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    kind = detect_json_import_kind(payload)
    if kind == IMPORT_KIND_POSTMAN:
        project, imported_variables = import_postman_collection(payload)
        saved = register_project(project)
        _activate_project(saved.id)
        _merge_default_environment(imported_variables)
        return {
            "kind": kind,
            "project": saved,
            "imported_variables": imported_variables,
            "message": f"已导入 Postman 集合：{saved.name}",
        }

    saved = import_apidog_project_payload(payload)
    _activate_project(saved.id)
    return {
        "kind": kind,
        "project": saved,
        "imported_variables": {},
        "message": f"已导入 ApiDog 项目：{saved.name}",
    }


def import_workspace_zip(raw: bytes) -> dict[str, Any]:
    ensure_data_layout()
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        names = set(archive.namelist())
        if EXPORT_MANIFEST_NAME not in names and "workspace.json" not in names:
            raise ValueError("不是有效的 ApiDog 导出包（缺少 workspace.json）")

        imported_projects = 0
        for name in sorted(names):
            if not name.startswith("collections/") or not name.endswith(".json"):
                continue
            payload = json.loads(archive.read(name).decode("utf-8"))
            if not isinstance(payload, dict):
                continue
            import_apidog_project_payload(payload)
            imported_projects += 1

        for name in sorted(names):
            if not name.startswith("environments/") or not name.endswith(".json"):
                continue
            payload = json.loads(archive.read(name).decode("utf-8"))
            if not isinstance(payload, dict):
                continue
            environment = EnvironmentConfig.model_validate(payload)
            if environment.id == DEFAULT_ENVIRONMENT_ID:
                try:
                    existing = load_environment(DEFAULT_ENVIRONMENT_ID)
                    merged = dict(existing.variables)
                    merged.update(environment.variables)
                    existing.variables = merged
                    if environment.name:
                        existing.name = environment.name
                    save_environment(existing)
                    continue
                except FileNotFoundError:
                    pass
            save_environment(environment)

    index = load_workspace_index()
    if index.projects:
        _activate_project(index.projects[-1]["id"])
    return {
        "kind": IMPORT_KIND_APIDOG_WORKSPACE,
        "project": None,
        "imported_variables": {},
        "message": f"已导入 ApiDog 工作区，共 {imported_projects} 个项目",
        "imported_projects": imported_projects,
    }


def _activate_project(project_id: str) -> None:
    index = load_workspace_index()
    index.active_project_id = project_id
    save_workspace_index(index)


def _merge_default_environment(imported_variables: dict[str, str]) -> None:
    if not imported_variables:
        return
    try:
        environment = load_environment(DEFAULT_ENVIRONMENT_ID)
    except FileNotFoundError:
        return
    merged = dict(environment.variables)
    merged.update(imported_variables)
    environment.variables = merged
    save_environment(environment)
