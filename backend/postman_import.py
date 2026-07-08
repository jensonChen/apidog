import uuid
from typing import Any

from models import ApiRequestItem, FolderItem, HeaderItem, ProjectCollection, TreeNode


def _postman_url_to_string(url_value: Any) -> str:
    if isinstance(url_value, str):
        return url_value
    if isinstance(url_value, dict):
        raw = url_value.get("raw")
        if isinstance(raw, str) and raw.strip():
            return raw
        protocol = url_value.get("protocol", "http")
        host_parts = url_value.get("host") or []
        path_parts = url_value.get("path") or []
        host = ".".join(str(part) for part in host_parts)
        path = "/".join(str(part) for part in path_parts)
        if host:
            return f"{protocol}://{host}/{path}".rstrip("/")
    return ""


def _parse_postman_request(item: dict[str, Any]) -> ApiRequestItem | None:
    request = item.get("request")
    if not isinstance(request, dict):
        return None

    headers: list[HeaderItem] = []
    for header in request.get("header") or []:
        if not isinstance(header, dict):
            continue
        if header.get("disabled"):
            continue
        headers.append(
            HeaderItem(
                key=str(header.get("key") or ""),
                value=str(header.get("value") or ""),
                enabled=True,
            )
        )

    body_type = "none"
    body = ""
    body_obj = request.get("body")
    if isinstance(body_obj, dict):
        mode = str(body_obj.get("mode") or "raw")
        raw = body_obj.get("raw")
        if isinstance(raw, str) and raw.strip():
            body = raw
            body_type = "json" if mode == "raw" else "raw"

    return ApiRequestItem(
        id=f"req-{uuid.uuid4().hex[:8]}",
        name=str(item.get("name") or "未命名请求"),
        method=str(request.get("method") or "GET").upper(),
        url=_postman_url_to_string(request.get("url")),
        headers=headers,
        body_type=body_type,
        body=body,
        follow_redirects=True,
    )


def _parse_postman_items(items: list[Any]) -> list[TreeNode]:
    nodes: list[TreeNode] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get("item")
        if isinstance(nested, list):
            nodes.append(
                FolderItem(
                    id=f"folder-{uuid.uuid4().hex[:8]}",
                    name=str(item.get("name") or "未命名模块"),
                    children=_parse_postman_items(nested),
                )
            )
            continue

        request_node = _parse_postman_request(item)
        if request_node:
            nodes.append(request_node)
    return nodes


def import_postman_collection(payload: dict[str, Any]) -> tuple[ProjectCollection, dict[str, str]]:
    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
    project_name = str(info.get("name") or "Postman 导入项目")
    tree = _parse_postman_items(payload.get("item") or [])

    project = ProjectCollection(
        id=f"proj-{uuid.uuid4().hex[:8]}",
        name=project_name,
        tree=tree,
    )

    variables: dict[str, str] = {}
    for variable in payload.get("variable") or []:
        if not isinstance(variable, dict):
            continue
        key = str(variable.get("key") or "").strip()
        if not key:
            continue
        variables[key] = str(variable.get("value") or "")

    return project, variables
