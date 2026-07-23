import json
import uuid
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config_loader import load_config
from chrome_parser import parse_chrome_paste
from curl_builder import build_curl_from_request, request_from_parsed
from curl_parser import parse_curl
from executor import execute_form_request, execute_parsed
from history_service import record_history
from models import (
    ApiRequestItem,
    EnvironmentConfig,
    ExecuteCurlRequest,
    ExecuteRequestPayload,
    ExecuteResponse,
    FolderItem,
    ProjectCollection,
    WorkspaceIndex,
)
from postman_import import import_postman_collection
from storage import (
    create_environment,
    create_project,
    delete_project,
    ensure_data_layout,
    list_environments,
    list_history,
    list_projects,
    load_environment,
    load_project,
    load_workspace_index,
    register_project,
    save_environment,
    save_project,
    save_workspace_index,
)

app = FastAPI(title="ApiDog", version="2.0.0")
config = load_config()
ensure_data_layout()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:19527",
        "http://localhost:19527",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = __import__("pathlib").Path(__file__).resolve().parent.parent / "frontend" / "dist"


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)


class CreateFolderRequest(BaseModel):
    name: str = Field(min_length=1)
    parent_folder_id: str | None = None


class CreateRequestPayload(BaseModel):
    name: str = Field(min_length=1)
    folder_id: str | None = None


class ActiveWorkspaceRequest(BaseModel):
    active_project_id: str | None = None
    active_environment_id: str | None = None


class CurlConvertRequest(BaseModel):
    curl_text: str = Field(min_length=1)


class ImportPostmanResponse(BaseModel):
    project: ProjectCollection
    imported_variables: dict[str, str] = Field(default_factory=dict)


def _get_variables(environment_id: str | None) -> dict[str, str]:
    env_id = environment_id or load_workspace_index().active_environment_id or "default"
    try:
        return load_environment(env_id).variables
    except FileNotFoundError:
        return {}


def _append_folder(
    tree: list,
    parent_folder_id: str | None,
    folder: FolderItem,
) -> bool:
    if not parent_folder_id:
        tree.append(folder)
        return True
    for node in tree:
        if isinstance(node, FolderItem) and node.id == parent_folder_id:
            node.children.append(folder)
            return True
        if isinstance(node, FolderItem) and _append_folder(node.children, parent_folder_id, folder):
            return True
    return False


def _append_request(tree: list, folder_id: str | None, request: ApiRequestItem) -> bool:
    if not folder_id:
        tree.append(request)
        return True
    for node in tree:
        if isinstance(node, FolderItem) and node.id == folder_id:
            node.children.append(request)
            return True
        if isinstance(node, FolderItem) and _append_request(node.children, folder_id, request):
            return True
    return False


def _remove_node(tree: list, node_id: str) -> bool:
    for index, node in enumerate(tree):
        if node.id == node_id:
            tree.pop(index)
            return True
        if isinstance(node, FolderItem) and _remove_node(node.children, node_id):
            return True
    return False


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ApiDog", "version": "2.0.0"}


@app.get("/api/config")
async def get_config():
    return load_config()


@app.get("/api/workspace")
async def get_workspace():
    index = load_workspace_index()
    return {
        "index": index,
        "projects": list_projects(),
        "environments": list_environments(),
    }


@app.put("/api/workspace/active")
async def set_active_workspace(payload: ActiveWorkspaceRequest):
    index = load_workspace_index()
    if payload.active_project_id is not None:
        index.active_project_id = payload.active_project_id
    if payload.active_environment_id is not None:
        index.active_environment_id = payload.active_environment_id
    save_workspace_index(index)
    return index


@app.get("/api/projects")
async def get_projects():
    return list_projects()


@app.get("/api/projects/{project_id}", response_model=ProjectCollection)
async def get_project(project_id: str):
    try:
        return load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects", response_model=ProjectCollection)
async def post_project(payload: CreateProjectRequest):
    project = create_project(payload.name)
    index = load_workspace_index()
    index.active_project_id = project.id
    save_workspace_index(index)
    return project


@app.put("/api/projects/{project_id}", response_model=ProjectCollection)
async def put_project(project_id: str, project: ProjectCollection):
    if project_id != project.id:
        raise HTTPException(status_code=400, detail="项目 ID 不一致")
    try:
        load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return save_project(project)


@app.delete("/api/projects/{project_id}")
async def remove_project(project_id: str):
    try:
        delete_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/projects/{project_id}/folders", response_model=ProjectCollection)
async def add_folder(project_id: str, payload: CreateFolderRequest):
    project = load_project(project_id)
    folder = FolderItem(id=f"folder-{uuid.uuid4().hex[:8]}", name=payload.name, children=[])
    if not _append_folder(project.tree, payload.parent_folder_id, folder):
        raise HTTPException(status_code=404, detail="父文件夹不存在")
    return save_project(project)


@app.post("/api/projects/{project_id}/requests", response_model=ProjectCollection)
async def add_request(project_id: str, payload: CreateRequestPayload):
    project = load_project(project_id)
    request = ApiRequestItem(
        id=f"req-{uuid.uuid4().hex[:8]}",
        name=payload.name,
        method="GET",
        url="{{baseUrl}}/",
    )
    if not _append_request(project.tree, payload.folder_id, request):
        raise HTTPException(status_code=404, detail="目标文件夹不存在")
    return save_project(project)


@app.delete("/api/projects/{project_id}/nodes/{node_id}", response_model=ProjectCollection)
async def remove_node(project_id: str, node_id: str):
    project = load_project(project_id)
    if not _remove_node(project.tree, node_id):
        raise HTTPException(status_code=404, detail="节点不存在")
    return save_project(project)


@app.get("/api/environments")
async def get_environments():
    return list_environments()


@app.get("/api/environments/{environment_id}", response_model=EnvironmentConfig)
async def get_environment(environment_id: str):
    try:
        return load_environment(environment_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/environments", response_model=EnvironmentConfig)
async def post_environment(payload: CreateProjectRequest):
    return create_environment(payload.name)


@app.put("/api/environments/{environment_id}", response_model=EnvironmentConfig)
async def put_environment(environment_id: str, environment: EnvironmentConfig):
    if environment_id != environment.id:
        raise HTTPException(status_code=400, detail="环境 ID 不一致")
    return save_environment(environment)


@app.get("/api/history")
async def get_history(limit: int = 50):
    return list_history(limit=limit)


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_request(payload: ExecuteRequestPayload):
    timeout_seconds = payload.timeout_seconds or config["default_timeout_seconds"]
    variables = _get_variables(payload.environment_id)
    result = await execute_form_request(payload, timeout_seconds, variables)
    record_history(payload, result)
    return result


@app.post("/api/execute-curl", response_model=ExecuteResponse)
async def execute_curl(payload: ExecuteCurlRequest):
    timeout_seconds = payload.timeout_seconds or config["default_timeout_seconds"]
    try:
        parsed = parse_curl(payload.curl_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    variables = _get_variables(payload.environment_id)
    result = await execute_parsed(parsed, timeout_seconds, variables)
    record_history(payload, result)
    return result


class ParseChromeRequest(BaseModel):
    chrome_text: str = Field(min_length=1)
    payload_extra: str = ""
    request_name: str = "Chrome 导入"


class ParseChromeResponse(BaseModel):
    request: ApiRequestItem
    curl_text: str


@app.post("/api/parse/chrome", response_model=ParseChromeResponse)
async def parse_chrome(payload: ParseChromeRequest):
    try:
        request = parse_chrome_paste(
            payload.chrome_text,
            payload.payload_extra,
            payload.request_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ParseChromeResponse(
        request=request,
        curl_text=build_curl_from_request(request),
    )


@app.post("/api/convert/curl-to-request", response_model=ApiRequestItem)
async def convert_curl_to_request(payload: CurlConvertRequest):
    try:
        parsed = parse_curl(payload.curl_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return request_from_parsed(parsed)


@app.post("/api/convert/request-to-curl")
async def convert_request_to_curl(request: ApiRequestItem):
    return {"curl_text": build_curl_from_request(request)}


@app.post("/api/import/postman", response_model=ImportPostmanResponse)
async def import_postman(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Postman 文件不是有效 JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Postman 集合格式无效")

    project, imported_variables = import_postman_collection(payload)
    saved = register_project(project)
    index = load_workspace_index()
    index.active_project_id = saved.id
    save_workspace_index(index)

    if imported_variables:
        try:
            environment = load_environment("default")
            merged = dict(environment.variables)
            merged.update(imported_variables)
            environment.variables = merged
            save_environment(environment)
        except FileNotFoundError:
            pass

    return ImportPostmanResponse(project=saved, imported_variables=imported_variables)


if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=config["port"], reload=False)
