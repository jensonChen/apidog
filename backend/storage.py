import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config_loader import DATA_DIR
from models import (
    ApiRequestItem,
    EnvironmentConfig,
    FolderItem,
    ProjectCollection,
    TreeNode,
    WorkspaceIndex,
)

COLLECTIONS_DIR = DATA_DIR / "collections"
ENVIRONMENTS_DIR = DATA_DIR / "environments"
HISTORY_DIR = DATA_DIR / "history"
INDEX_PATH = DATA_DIR / "workspace.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_project() -> ProjectCollection:
    return ProjectCollection(
        id="proj-gctsql",
        name="gctSqlAssistant",
        updated_at=_now_iso(),
        tree=[
            FolderItem(
                id="folder-health",
                name="健康检查",
                children=[
                    ApiRequestItem(
                        id="req-starter",
                        name="starter 健康检查",
                        method="GET",
                        url="{{baseUrl}}/starter",
                    ),
                    ApiRequestItem(
                        id="req-model",
                        name="get_current_model",
                        method="GET",
                        url="{{baseUrl}}/get_current_model",
                    ),
                ],
            ),
            FolderItem(
                id="folder-nl2sql",
                name="问数接口",
                children=[
                    ApiRequestItem(
                        id="req-sync",
                        name="问数-同步",
                        method="POST",
                        url="{{baseUrl}}/pii_post_query",
                        headers=[
                            {"key": "Content-Type", "value": "application/json", "enabled": True}
                        ],
                        body_type="json",
                        body=(
                            '{\n  "chatMessageList": [\n    {\n'
                            '      "textType": "currQuery",\n'
                            '      "content": "查询员工总数"\n    }\n  ],\n'
                            '  "isNewConversation": true,\n'
                            '  "session_id": "api-workbench-test-001"\n}'
                        ),
                    ),
                    ApiRequestItem(
                        id="req-async-start",
                        name="问数-异步发起",
                        method="POST",
                        url="{{baseUrl}}/pii_post_query/start",
                        headers=[
                            {"key": "Content-Type", "value": "application/json", "enabled": True}
                        ],
                        body_type="json",
                        body=(
                            '{\n  "chatMessageList": [\n    {\n'
                            '      "textType": "currQuery",\n'
                            '      "content": "查询员工总数"\n    }\n  ],\n'
                            '  "isNewConversation": true,\n'
                            '  "session_id": "api-workbench-test-002"\n}'
                        ),
                    ),
                    ApiRequestItem(
                        id="req-async-poll",
                        name="问数-异步轮询",
                        method="GET",
                        url="{{baseUrl}}/harness/trace/{{traceId}}",
                    ),
                ],
            ),
        ],
    )


def _default_environment() -> EnvironmentConfig:
    return EnvironmentConfig(
        id="default",
        name="默认环境",
        variables={
            "baseUrl": "http://127.0.0.1:9019",
            "traceId": "在这里填trace_id",
        },
    )


def ensure_data_layout() -> None:
    COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    ENVIRONMENTS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    default_env_path = ENVIRONMENTS_DIR / "default.json"
    if not default_env_path.exists():
        _write_json(default_env_path, _default_environment().model_dump())

    if not INDEX_PATH.exists():
        project = _default_project()
        project_path = COLLECTIONS_DIR / f"{project.id}.json"
        _write_json(project_path, project.model_dump())
        index = WorkspaceIndex(
            active_project_id=project.id,
            active_environment_id="default",
            projects=[{"id": project.id, "name": project.name, "file": project_path.name}],
        )
        _write_json(INDEX_PATH, index.model_dump())
        return

    index = WorkspaceIndex.model_validate(_read_json(INDEX_PATH))
    if not index.projects:
        project = _default_project()
        project_path = COLLECTIONS_DIR / f"{project.id}.json"
        _write_json(project_path, project.model_dump())
        index.active_project_id = project.id
        index.projects = [{"id": project.id, "name": project.name, "file": project_path.name}]
        _write_json(INDEX_PATH, index.model_dump())


def load_workspace_index() -> WorkspaceIndex:
    ensure_data_layout()
    return WorkspaceIndex.model_validate(_read_json(INDEX_PATH))


def save_workspace_index(index: WorkspaceIndex) -> None:
    _write_json(INDEX_PATH, index.model_dump())


def _project_path(project_id: str) -> Path:
    index = load_workspace_index()
    matched = next((item for item in index.projects if item["id"] == project_id), None)
    if not matched:
        raise FileNotFoundError(f"项目不存在: {project_id}")
    return COLLECTIONS_DIR / matched["file"]


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
    _write_json(COLLECTIONS_DIR / file_name, project.model_dump())

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

    project_file = COLLECTIONS_DIR / matched["file"]
    if project_file.exists():
        project_file.unlink()

    index.projects = [item for item in index.projects if item["id"] != project_id]
    if index.active_project_id == project_id:
        index.active_project_id = index.projects[0]["id"] if index.projects else ""
    save_workspace_index(index)


def list_environments() -> list[EnvironmentConfig]:
    ensure_data_layout()
    environments: list[EnvironmentConfig] = []
    for path in sorted(ENVIRONMENTS_DIR.glob("*.json")):
        environments.append(EnvironmentConfig.model_validate(_read_json(path)))
    return environments


def load_environment(environment_id: str) -> EnvironmentConfig:
    path = ENVIRONMENTS_DIR / f"{environment_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"环境不存在: {environment_id}")
    return EnvironmentConfig.model_validate(_read_json(path))


def save_environment(environment: EnvironmentConfig) -> EnvironmentConfig:
    _write_json(ENVIRONMENTS_DIR / f"{environment.id}.json", environment.model_dump())
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
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    history_path = HISTORY_DIR / f"{day}.jsonl"
    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_history(limit: int = 50) -> list[dict]:
    if not HISTORY_DIR.exists():
        return []

    files = sorted(HISTORY_DIR.glob("*.jsonl"), reverse=True)
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
