import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config_loader import resolve_data_dir
from models import (
    ApiRequestItem,
    EnvironmentConfig,
    FolderItem,
    ProjectCollection,
    TreeNode,
    WorkspaceIndex,
)

DEFAULT_ENVIRONMENT_ID = "default"
DEFAULT_ENVIRONMENT_NAME = "默认环境"


def _collections_dir() -> Path:
    return resolve_data_dir() / "collections"


def _environments_dir() -> Path:
    return resolve_data_dir() / "environments"


def _history_dir() -> Path:
    return resolve_data_dir() / "history"


def _index_path() -> Path:
    return resolve_data_dir() / "workspace.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_environment() -> EnvironmentConfig:
    return EnvironmentConfig(
        id=DEFAULT_ENVIRONMENT_ID,
        name=DEFAULT_ENVIRONMENT_NAME,
        variables={},
    )


def _empty_workspace_index() -> WorkspaceIndex:
    return WorkspaceIndex(
        active_project_id="",
        active_environment_id=DEFAULT_ENVIRONMENT_ID,
        projects=[],
    )


def ensure_data_layout() -> None:
    collections_dir = _collections_dir()
    environments_dir = _environments_dir()
    history_dir = _history_dir()
    index_path = _index_path()

    collections_dir.mkdir(parents=True, exist_ok=True)
    environments_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)

    default_env_path = environments_dir / f"{DEFAULT_ENVIRONMENT_ID}.json"
    if not default_env_path.exists():
        _write_json(default_env_path, _default_environment().model_dump())

    if not index_path.exists():
        _write_json(index_path, _empty_workspace_index().model_dump())


def load_workspace_index() -> WorkspaceIndex:
    ensure_data_layout()
    return WorkspaceIndex.model_validate(_read_json(_index_path()))


def save_workspace_index(index: WorkspaceIndex) -> None:
    _write_json(_index_path(), index.model_dump())


def _project_path(project_id: str) -> Path:
    index = load_workspace_index()
    matched = next((item for item in index.projects if item["id"] == project_id), None)
    if not matched:
        raise FileNotFoundError(f"项目不存在: {project_id}")
    return _collections_dir() / matched["file"]


def list_projects() -> list[dict[str, str]]:
    index = load_workspace_index()
    return index.projects


def load_project(project_id: str) -> ProjectCollection:
    return ProjectCollection.model_validate(_read_json(_project_path(project_id)))


def save_project(project: ProjectCollection) -> ProjectCollection:
    project.updated_at = _now_iso()
    _write_json(_project_path(project.id), project.model_dump())

    index = load_workspace_index()
    for item in index.projects:
        if item["id"] == project.id:
            item["name"] = project.name
            break
    save_workspace_index(index)
    return project


def create_project(name: str) -> ProjectCollection:
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    project = ProjectCollection(id=project_id, name=name, updated_at=_now_iso(), tree=[])
    return register_project(project)


def register_project(project: ProjectCollection) -> ProjectCollection:
    file_name = f"{project.id}.json"
    project.updated_at = _now_iso()
    _write_json(_collections_dir() / file_name, project.model_dump())

    index = load_workspace_index()
    if not any(item["id"] == project.id for item in index.projects):
        index.projects.append({"id": project.id, "name": project.name, "file": file_name})
    else:
        for item in index.projects:
            if item["id"] == project.id:
                item["name"] = project.name
                break
    if not index.active_project_id:
        index.active_project_id = project.id
    save_workspace_index(index)
    return project


def delete_project(project_id: str) -> None:
    index = load_workspace_index()
    matched = next((item for item in index.projects if item["id"] == project_id), None)
    if not matched:
        raise FileNotFoundError(f"项目不存在: {project_id}")

    project_file = _collections_dir() / matched["file"]
    if project_file.exists():
        project_file.unlink()

    index.projects = [item for item in index.projects if item["id"] != project_id]
    if index.active_project_id == project_id:
        index.active_project_id = index.projects[0]["id"] if index.projects else ""
    save_workspace_index(index)


def list_environments() -> list[EnvironmentConfig]:
    ensure_data_layout()
    environments: list[EnvironmentConfig] = []
    for path in sorted(_environments_dir().glob("*.json")):
        environments.append(EnvironmentConfig.model_validate(_read_json(path)))
    return environments


def load_environment(environment_id: str) -> EnvironmentConfig:
    path = _environments_dir() / f"{environment_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"环境不存在: {environment_id}")
    return EnvironmentConfig.model_validate(_read_json(path))


def save_environment(environment: EnvironmentConfig) -> EnvironmentConfig:
    _write_json(_environments_dir() / f"{environment.id}.json", environment.model_dump())
    return environment


def create_environment(name: str) -> EnvironmentConfig:
    environment = EnvironmentConfig(
        id=f"env-{uuid.uuid4().hex[:8]}",
        name=name,
        variables={},
    )
    return save_environment(environment)


def find_request_node(tree: list[TreeNode], request_id: str) -> ApiRequestItem | None:
    for node in tree:
        if isinstance(node, ApiRequestItem) and node.id == request_id:
            return node
        if isinstance(node, FolderItem):
            found = find_request_node(node.children, request_id)
            if found:
                return found
    return None


def upsert_request_node(tree: list[TreeNode], request: ApiRequestItem) -> bool:
    for index, node in enumerate(tree):
        if isinstance(node, ApiRequestItem) and node.id == request.id:
            tree[index] = request
            return True
        if isinstance(node, FolderItem) and upsert_request_node(node.children, request):
            return True
    return False


def append_history(entry: dict) -> None:
    history_dir = _history_dir()
    history_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    history_path = history_dir / f"{day}.jsonl"
    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_history(limit: int = 50) -> list[dict]:
    history_dir = _history_dir()
    if not history_dir.exists():
        return []

    files = sorted(history_dir.glob("*.jsonl"), reverse=True)
    records: list[dict] = []
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            records.append(json.loads(line))
            if len(records) >= limit:
                return records
    return records
