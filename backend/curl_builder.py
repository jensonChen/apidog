from models import ApiRequestItem, HeaderItem


def build_curl_from_request(request: ApiRequestItem) -> str:
    lines = ["curl"]
    if request.follow_redirects:
        lines.append("--location")
    lines.append(f"-X {request.method.upper()}")
    lines.append(f"'{request.url}'")

    for header in request.headers:
        if not header.enabled or not header.key:
            continue
        lines.append(f"--header '{header.key}: {header.value}'")

    if request.body_type != "none" and request.body.strip():
        lines.append(f"--data '{request.body}'")

    return " \\\n".join(lines)


def request_from_parsed(parsed, name: str = "未命名请求") -> ApiRequestItem:
    import uuid

    headers = [
        HeaderItem(key=key, value=value, enabled=True)
        for key, value in parsed.headers.items()
    ]
    body_type = "none"
    body = ""
    if parsed.body is not None:
        body_type = "json"
        body = parsed.body

    return ApiRequestItem(
        id=f"req-{uuid.uuid4().hex[:8]}",
        name=name,
        method=parsed.method.upper(),
        url=parsed.url,
        headers=headers,
        body_type=body_type,
        body=body,
        follow_redirects=parsed.follow_redirects,
    )
