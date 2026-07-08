import json
import re
import uuid
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from curl_builder import build_curl_from_request
from models import ApiRequestItem, HeaderItem

URL_LABELS = ("请求网址", "request url")
METHOD_LABELS = ("请求方法", "request method")

RESPONSE_ONLY_HEADERS = {
    "content-length",
    "content-type",
    "date",
    "server",
    "set-cookie",
    "transfer-encoding",
    "x-content-type-options",
    "x-frame-options",
    "x-xss-protection",
}

SKIP_HEADERS = {
    "host",
    "connection",
    "accept-encoding",
    "user-agent",
    "referer",
}

GENERAL_STOP_WORDS = {
    "状态代码",
    "status code",
    "远程地址",
    "remote address",
    "引荐来源网址政策",
    "referrer policy",
    "strict-origin-when-cross-origin",
}


def _is_url(text: str) -> bool:
    return text.startswith(("http://", "https://"))


def _find_labeled_value(lines: list[str], labels: tuple[str, ...]) -> str:
    lower_labels = {label.lower() for label in labels}
    for index, line in enumerate(lines):
        if line.lower() in lower_labels and index + 1 < len(lines):
            return lines[index + 1].strip()
    return ""


def _find_request_header_start(lines: list[str]) -> int:
    method_index = -1
    for index, line in enumerate(lines):
        lower = line.lower()
        if lower in {"get", "post", "put", "delete", "patch", "head", "options"}:
            method_index = index
            break

    search_from = method_index + 1 if method_index >= 0 else 0
    for index in range(search_from, len(lines)):
        if lines[index].lower() == "accept":
            return index
    return search_from


def _parse_header_pairs(lines: list[str], start_index: int) -> dict[str, str]:
    headers: dict[str, str] = {}
    index = start_index
    while index < len(lines):
        key = lines[index].strip()
        if not key or key.lower() in GENERAL_STOP_WORDS:
            index += 1
            continue
        if _is_url(key) or key.lower() in {"get", "post", "put", "delete", "patch"}:
            index += 1
            continue
        if ":" in key and index == start_index:
            name, value = key.split(":", 1)
            headers[name.strip()] = value.strip()
            index += 1
            continue
        if index + 1 >= len(lines):
            break
        value = lines[index + 1].strip()
        if not value or value.lower() in GENERAL_STOP_WORDS:
            index += 1
            continue
        if _is_url(value):
            index += 1
            continue
        headers[key] = value
        index += 2
    return headers


def _filter_request_headers(headers: dict[str, str]) -> dict[str, str]:
    filtered: dict[str, str] = {}
    for key, value in headers.items():
        lower = key.lower()
        if lower in RESPONSE_ONLY_HEADERS and lower != "content-type":
            continue
        if lower in SKIP_HEADERS:
            continue
        filtered[key] = value
    return filtered


def _merge_query_to_url(url: str, query_text: str) -> str:
    query_text = query_text.strip()
    if not query_text or query_text.startswith("{"):
        return url
    parsed = urlparse(url)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    extra = dict(parse_qsl(query_text.lstrip("?"), keep_blank_values=True))
    existing.update(extra)
    new_query = urlencode(existing, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def parse_chrome_paste(
    chrome_text: str,
    payload_extra: str = "",
    request_name: str = "Chrome 导入",
) -> ApiRequestItem:
    combined_extra = payload_extra.strip()
    source_text = chrome_text.strip()

    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("粘贴内容为空")

    url = _find_labeled_value(lines, URL_LABELS)
    if not url:
        for line in lines:
            if _is_url(line):
                url = line
                break
    if not url:
        raise ValueError("未找到请求网址，请确认已复制 Chrome 网络面板内容")

    method = _find_labeled_value(lines, METHOD_LABELS).upper()
    if method not in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
        for line in lines:
            if line.upper() in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                method = line.upper()
                break
    if not method:
        method = "GET"

    header_start = _find_request_header_start(lines)
    raw_headers = _parse_header_pairs(lines, header_start)
    headers = _filter_request_headers(raw_headers)

    body_type = "none"
    body = ""
    if combined_extra:
        if _looks_like_json(combined_extra):
            body = combined_extra.strip()
            body_type = "json"
            method = "POST" if method == "GET" else method
            if "content-type" not in {key.lower() for key in headers}:
                headers["Content-Type"] = "application/json"
        else:
            url = _merge_query_to_url(url, combined_extra)
            method = "GET"

    if "?" not in url and method == "GET" and not combined_extra:
        pass

    header_items = [
        HeaderItem(key=key, value=value, enabled=True)
        for key, value in headers.items()
    ]

    return ApiRequestItem(
        id=f"req-{uuid.uuid4().hex[:8]}",
        name=request_name,
        method=method,
        url=url,
        headers=header_items,
        body_type=body_type,
        body=body,
        follow_redirects=True,
    )
