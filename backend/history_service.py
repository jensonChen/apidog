from datetime import datetime, timezone

from models import ExecuteCurlRequest, ExecuteRequestPayload, ExecuteResponse
from storage import append_history


def build_history_entry(
    payload: ExecuteRequestPayload | ExecuteCurlRequest,
    result: ExecuteResponse,
) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": payload.project_id,
        "request_id": payload.request_id,
        "request_name": payload.request_name,
        "method": result.parsed_method,
        "url": result.parsed_url,
        "resolved_url": result.resolved_url,
        "status_code": result.status_code,
        "elapsed_ms": result.elapsed_ms,
        "ok": result.ok,
        "error": result.error,
    }


def record_history(
    payload: ExecuteRequestPayload | ExecuteCurlRequest,
    result: ExecuteResponse,
) -> None:
    append_history(build_history_entry(payload, result))
