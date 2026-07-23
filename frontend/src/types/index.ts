export interface HeaderItem {
  key: string;
  value: string;
  enabled: boolean;
}

export interface ApiRequestItem {
  type: "request";
  id: string;
  name: string;
  method: string;
  url: string;
  headers: HeaderItem[];
  body_type: "none" | "json" | "raw";
  body: string;
  follow_redirects: boolean;
}

export interface FolderItem {
  type: "folder";
  id: string;
  name: string;
  children: TreeNode[];
}

export type TreeNode = ApiRequestItem | FolderItem;

export interface ProjectCollection {
  id: string;
  name: string;
  updated_at: string;
  tree: TreeNode[];
}

export interface EnvironmentConfig {
  id: string;
  name: string;
  variables: Record<string, string>;
}

export interface WorkspaceIndex {
  active_project_id: string;
  active_environment_id: string;
  projects: Array<{ id: string; name: string; file: string }>;
}

export interface ExecuteResponse {
  ok: boolean;
  status_code: number | null;
  elapsed_ms: number;
  response_headers: Record<string, string>;
  body_text: string;
  body_json: Record<string, unknown> | unknown[] | null;
  error: string | null;
  parsed_method: string | null;
  parsed_url: string | null;
  resolved_url: string | null;
}

export interface HistoryItem {
  timestamp: string;
  project_id?: string | null;
  request_id?: string | null;
  request_name?: string | null;
  method?: string | null;
  url?: string | null;
  resolved_url?: string | null;
  status_code?: number | null;
  elapsed_ms?: number;
  ok?: boolean;
  error?: string | null;
}

export interface WorkspaceContextState {
  lastClickedFolderId: string | null;
}

export interface WorkbenchTab {
  id: string;
  title: string;
  editMode: "chrome" | "form" | "curl";
  draft: ApiRequestItem | null;
  /** 是否已落库：侧栏打开或首次保存成功后为 true，保存时更新而非新增 */
  isPersisted: boolean;
  sourceFolderId: string | null;
  chromeText: string;
  payloadExtra: string;
  curlText: string;
  parsedPreview: { method: string; url: string } | null;
  response: ExecuteResponse | null;
}
