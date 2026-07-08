import json
import time

import httpx

from curl_parser import ParsedCurl
from env_utils import normalize_url, resolve_variables
from models import ExecuteRequestPayload, ExecuteResponse, HeaderItem


def _headers_to_dict(headers: list[HeaderItem]) -> dict[str, str]:
    result: dict[str, str] = {}
    for header in headers:
        if header.enabled and header.key:
            result[header.key] = header.value
    return result


def _build_response(
    response: httpx.Response | None,
    started: float,
    *,
    error: str | None = None,
    parsed_method: str | None = None,
    parsed_url: str | None = None,
    resolved_url: str | None = None,
) -> ExecuteResponse:
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if error or response is None:
        return ExecuteResponse(
            ok=False,
            elapsed_ms=elapsed_ms,
            error=error,
            parsed_method=parsed_method,
            parsed_url=parsed_url,
            resolved_url=resolved_url,
        )

    body_text = response.text
    body_json = None
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type.lower():
        try:
            body_json = response.json()
        except json.JSONDecodeError:
            body_json = None

    return ExecuteResponse(
        ok=response.is_success,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
        response_headers=dict(response.headers),
        body_text=body_text,
        body_json=body_json,
        parsed_method=parsed_method,
        parsed_url=parsed_url,
        resolved_url=resolved_url,
    )


async def execute_parsed(
    parsed: ParsedCurl,
    timeout_seconds: int,
    variables: dict[str, str] | None = None,
) -> ExecuteResponse:
    started = time.perf_counter()
    variables = variables or {}
    resolved_url = normalize_url(resolve_variables(parsed.url, variables))
    resolved_headers = {
        key: resolve_variables(value, variables)
        for key, value in parsed.headers.items()
    }
    resolved_body = (
        resolve_variables(parsed.body, variables) if parsed.body is not None else None
    )

    request_kwargs: dict = {
        "method": parsed.method,
        "url": resolved_url,
        "headers": resolved_headers or None,
        "timeout": httpx.Timeout(timeout_seconds),
        "follow_redirects": parsed.follow_redirects,
    }
    if resolved_body is not None:
        request_kwargs["content"] = resolved_body.encode("utf-8")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(**request_kwargs)
    except httpx.TimeoutException:
        return _build_response(
            None,
            started,
            error=f"请求超时（>{timeout_seconds} 秒）",
            parsed_method=parsed.method,
            parsed_url=parsed.url,
            resolved_url=resolved_url,
        )
    except httpx.RequestError as exc:
        return _build_response(
            None,
            started,
            error=f"网络错误: {exc}",
            parsed_method=parsed.method,
            parsed_url=parsed.url,
            resolved_url=resolved_url,
        )

    return _build_response(
        response,
        started,
        parsed_method=parsed.method,
        parsed_url=parsed.url,
        resolved_url=resolved_url,
    )


async def execute_form_request(
    payload: ExecuteRequestPayload,
    timeout_seconds: int,
    variables: dict[str, str] | None = None,
) -> ExecuteResponse:
    variables = variables or {}
    resolved_url = resolve_variables(payload.url, variables)
    resolved_headers = [
        HeaderItem(
            key=header.key,
            value=resolve_variables(header.value, variables),
            enabled=header.enabled,
        )
        for header in payload.headers
    ]
    resolved_body = resolve_variables(payload.body, variables)

    parsed = ParsedCurl(
        method=payload.method.upper(),
        url=resolved_url,
        headers=_headers_to_dict(resolved_headers),
        body=resolved_body if payload.body_type != "none" else None,
        follow_redirects=payload.follow_redirects,
    )
    return await execute_parsed(parsed, timeout_seconds, variables)
