import type {
  ApiRequestItem,
  EnvironmentConfig,
  ExecuteResponse,
  HistoryItem,
  ProjectCollection,
  WorkspaceIndex,
} from "../types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `请求失败: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchWorkspace(): Promise<{
  index: WorkspaceIndex;
  projects: Array<{ id: string; name: string; file: string }>;
  environments: EnvironmentConfig[];
}> {
  return requestJson("/api/workspace");
}

export async function fetchConfig(): Promise<{
  port: number;
  default_timeout_seconds: number;
  frontend_dev_port: number;
  desktop_shell?: boolean;
}> {
  return requestJson("/api/config");
}

export async function exportWorkspace(): Promise<void> {
  const response = await fetch("/api/workspace/export");
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `导出失败: HTTP ${response.status}`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const matched = /filename=\"?([^\";]+)\"?/i.exec(disposition);
  const filename = matched?.[1] || "ApiDog-workspace.zip";
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function fetchProject(
  projectId: string,
): Promise<ProjectCollection> {
  return requestJson(`/api/projects/${projectId}`);
}

export async function saveProject(
  project: ProjectCollection,
): Promise<ProjectCollection> {
  return requestJson(`/api/projects/${project.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(project),
  });
}

export async function createProject(name: string): Promise<ProjectCollection> {
  return requestJson("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function deleteProject(projectId: string): Promise<void> {
  await requestJson(`/api/projects/${projectId}`, { method: "DELETE" });
}

export async function addFolder(
  projectId: string,
  name: string,
  parentFolderId?: string,
): Promise<ProjectCollection> {
  return requestJson(`/api/projects/${projectId}/folders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, parent_folder_id: parentFolderId ?? null }),
  });
}

export async function addRequest(
  projectId: string,
  name: string,
  folderId?: string,
): Promise<ProjectCollection> {
  return requestJson(`/api/projects/${projectId}/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, folder_id: folderId ?? null }),
  });
}

export async function deleteNode(
  projectId: string,
  nodeId: string,
): Promise<ProjectCollection> {
  return requestJson(`/api/projects/${projectId}/nodes/${nodeId}`, {
    method: "DELETE",
  });
}

export async function setActiveWorkspace(payload: {
  active_project_id?: string;
  active_environment_id?: string;
}): Promise<WorkspaceIndex> {
  return requestJson("/api/workspace/active", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function saveEnvironment(
  environment: EnvironmentConfig,
): Promise<EnvironmentConfig> {
  return requestJson(`/api/environments/${environment.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(environment),
  });
}

export async function parseChromePaste(
  chromeText: string,
  payloadExtra = "",
  requestName = "Chrome 导入",
): Promise<{ request: ApiRequestItem; curl_text: string }> {
  return requestJson("/api/parse/chrome", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chrome_text: chromeText,
      payload_extra: payloadExtra,
      request_name: requestName,
    }),
  });
}

export async function executeRequest(payload: {
  method: string;
  url: string;
  headers: ApiRequestItem["headers"];
  body_type: ApiRequestItem["body_type"];
  body: string;
  follow_redirects: boolean;
  project_id?: string;
  request_id?: string;
  request_name?: string;
}): Promise<ExecuteResponse> {
  return requestJson("/api/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function executeCurl(payload: {
  curl_text: string;
  environment_id?: string;
  project_id?: string;
  request_id?: string;
  request_name?: string;
}): Promise<ExecuteResponse> {
  return requestJson("/api/execute-curl", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function convertRequestToCurl(
  request: ApiRequestItem,
): Promise<string> {
  const result = await requestJson<{ curl_text: string }>(
    "/api/convert/request-to-curl",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
  return result.curl_text;
}

export async function convertCurlToRequest(
  curlText: string,
): Promise<ApiRequestItem> {
  return requestJson("/api/convert/curl-to-request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ curl_text: curlText }),
  });
}

export async function importPostman(file: File): Promise<{
  project: ProjectCollection;
  imported_variables: Record<string, string>;
}> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/import/postman", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `导入失败: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchHistory(limit = 30): Promise<HistoryItem[]> {
  return requestJson(`/api/history?limit=${limit}`);
}
