from typing import Literal

from pydantic import BaseModel, Field


class HeaderItem(BaseModel):
    key: str = ""
    value: str = ""
    enabled: bool = True


class ApiRequestItem(BaseModel):
    type: Literal["request"] = "request"
    id: str
    name: str
    method: str = "GET"
    url: str = ""
    headers: list[HeaderItem] = Field(default_factory=list)
    body_type: Literal["none", "json", "raw"] = "none"
    body: str = ""
    follow_redirects: bool = True


class FolderItem(BaseModel):
    type: Literal["folder"] = "folder"
    id: str
    name: str
    children: list["TreeNode"] = Field(default_factory=list)


TreeNode = ApiRequestItem | FolderItem
FolderItem.model_rebuild()


class ProjectCollection(BaseModel):
    id: str
    name: str
    updated_at: str = ""
    tree: list[TreeNode] = Field(default_factory=list)


class EnvironmentConfig(BaseModel):
    id: str
    name: str
    variables: dict[str, str] = Field(default_factory=dict)


class WorkspaceIndex(BaseModel):
    active_project_id: str = ""
    active_environment_id: str = "default"
    projects: list[dict[str, str]] = Field(default_factory=list)


class ExecuteRequestPayload(BaseModel):
    method: str = "GET"
    url: str = Field(min_length=1)
    headers: list[HeaderItem] = Field(default_factory=list)
    body_type: Literal["none", "json", "raw"] = "none"
    body: str = ""
    follow_redirects: bool = True
    timeout_seconds: int | None = None
    environment_id: str | None = None
    project_id: str | None = None
    request_id: str | None = None
    request_name: str | None = None


class ExecuteCurlRequest(BaseModel):
    curl_text: str = Field(min_length=1)
    timeout_seconds: int | None = None
    environment_id: str | None = None
    project_id: str | None = None
    request_id: str | None = None
    request_name: str | None = None


class ExecuteResponse(BaseModel):
    ok: bool
    status_code: int | None = None
    elapsed_ms: int
    response_headers: dict[str, str] = Field(default_factory=dict)
    body_text: str = ""
    body_json: dict | list | None = None
    error: str | None = None
    parsed_method: str | None = None
    parsed_url: str | None = None
    resolved_url: str | None = None
