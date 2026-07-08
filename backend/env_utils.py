import re


def resolve_variables(text: str, variables: dict[str, str]) -> str:
    if not text:
        return text

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return variables.get(key, match.group(0))

    return re.sub(r"\{\{([^}]+)\}\}", replace, text)


def normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        return cleaned
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    return f"http://{cleaned}"
