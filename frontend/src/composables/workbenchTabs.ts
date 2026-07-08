import type { ApiRequestItem, ExecuteResponse, WorkbenchTab } from "../types";

function createTabId(): string {
  return `tab-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export function createEmptyTab(title = "新请求"): WorkbenchTab {
  return {
    id: createTabId(),
    title,
    editMode: "chrome",
    draft: null,
    chromeText: "",
    payloadExtra: "",
    curlText: "",
    parsedPreview: null,
    response: null,
  };
}

export function createTabFromRequest(request: ApiRequestItem): WorkbenchTab {
  return {
    id: createTabId(),
    title: request.name || "未命名接口",
    editMode: "form",
    draft: JSON.parse(JSON.stringify(request)),
    chromeText: "",
    payloadExtra: "",
    curlText: "",
    parsedPreview: { method: request.method, url: request.url },
    response: null,
  };
}

export function tabTitleFromResponse(
  tab: WorkbenchTab,
  result: ExecuteResponse,
): string {
  if (tab.draft?.name && tab.draft.name !== "Chrome 导入") {
    return tab.draft.name;
  }
  const url = result.resolved_url || result.parsed_url || tab.parsedPreview?.url;
  if (!url) {
    return tab.title;
  }
  try {
    const path = new URL(url).pathname.split("/").filter(Boolean).pop();
    return path || tab.title;
  } catch {
    return tab.title;
  }
}

export function attachResponse(tab: WorkbenchTab, result: ExecuteResponse): void {
  tab.response = result;
  tab.title = tabTitleFromResponse(tab, result);
}
