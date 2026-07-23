import re
from dataclasses import dataclass, field


@dataclass
class ParsedCurl:
    method: str = "GET"
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    follow_redirects: bool = False


def _join_line_continuations(curl_text: str) -> str:
    lines = curl_text.strip().splitlines()
    merged: list[str] = []
    buffer = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if buffer:
            buffer = f"{buffer} {stripped}"
        else:
            buffer = stripped

        if buffer.endswith("\\"):
            buffer = buffer[:-1].rstrip()
            continue

        merged.append(buffer)
        buffer = ""

    if buffer:
        merged.append(buffer)

    text = " ".join(merged)
    return re.sub(r"^\s*curl\s+", "", text, flags=re.IGNORECASE).strip()


def _extract_quoted_value(text: str, flag: str) -> tuple[str, str | None]:
    patterns = [
        rf"(?:^|\s){re.escape(flag)}\s+'((?:[^'\\]|\\.)*)'",
        rf'(?:^|\s){re.escape(flag)}\s+"((?:[^"\\]|\\.)*)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if not match:
            continue
        value = match.group(1)
        remaining = (text[: match.start()] + text[match.end() :]).strip()
        return remaining, value
    return text, None


def _extract_all_headers(text: str) -> tuple[str, dict[str, str]]:
    headers: dict[str, str] = {}
    remaining = text

    while True:
        before = remaining
        remaining, header_value = _extract_quoted_value(remaining, "--header")
        if header_value is None:
            remaining, header_value = _extract_quoted_value(remaining, "-H")

        if header_value is None:
            break

        if ":" not in header_value:
            raise ValueError(f"Header 格式无效: {header_value}")

        name, value = header_value.split(":", 1)
        headers[name.strip()] = value.strip()

        if remaining == before:
            break

    return remaining, headers


def parse_curl(curl_text: str) -> ParsedCurl:
    if not curl_text.strip():
        raise ValueError("curl 内容不能为空")

    text = _join_line_continuations(curl_text)
    parsed = ParsedCurl()

    if re.search(r"(?:^|\s)(?:--location|-L)(?:\s|$)", text, re.IGNORECASE):
        parsed.follow_redirects = True

    method_match = re.search(
        r"(?:^|\s)(?:-X|--request)\s+([A-Za-z]+)",
        text,
        re.IGNORECASE,
    )
    if method_match:
        parsed.method = method_match.group(1).upper()

    text, body = _extract_quoted_value(text, "--data-binary")
    if body is None:
        text, body = _extract_quoted_value(text, "--data-raw")
    if body is None:
        text, body = _extract_quoted_value(text, "--data")
    if body is None:
        text, body = _extract_quoted_value(text, "-d")

    if body is not None:
        parsed.body = body
        if parsed.method == "GET":
            parsed.method = "POST"

    text, parsed.headers = _extract_all_headers(text)

    url_match = re.search(r"['\"]?(https?://[^\s'\"\\]+)['\"]?", text, re.IGNORECASE)
    if not url_match:
        raise ValueError("未找到请求 URL，请检查 curl 命令")

    parsed.url = url_match.group(1).rstrip("})],;")
    return parsed
