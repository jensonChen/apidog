import type {
  ApiRequestItem,
  FolderItem,
  TreeNode,
  WorkbenchTab,
  WorkspaceContextState,
} from "../types";

export const ROOT_FOLDER_VALUE = "__root__";

export interface FolderOption {
  id: string;
  label: string;
}

function findParentInFolder(
  folder: FolderItem,
  requestId: string,
): string | null {
  for (const child of folder.children) {
    if (child.type === "request" && child.id === requestId) {
      return folder.id;
    }
    if (child.type === "folder") {
      const found = findParentInFolder(child, requestId);
      if (found) {
        return found;
      }
    }
  }
  return null;
}

export function findRequestParentFolderId(
  tree: TreeNode[],
  requestId: string,
): string | null {
  for (const node of tree) {
    if (node.type === "request" && node.id === requestId) {
      return null;
    }
    if (node.type === "folder") {
      const inChildren = findParentInFolder(node, requestId);
      if (inChildren) {
        return inChildren;
      }
    }
  }
  return null;
}

export function collectFolderOptions(
  nodes: TreeNode[],
  prefix = "",
): FolderOption[] {
  const options: FolderOption[] = [];
  for (const node of nodes) {
    if (node.type === "folder") {
      const label = prefix ? `${prefix} / ${node.name}` : node.name;
      options.push({ id: node.id, label });
      options.push(...collectFolderOptions(node.children, label));
    }
  }
  return options;
}

export function resolveDefaultFolderId(
  tab: WorkbenchTab,
  context: WorkspaceContextState,
): string | null {
  if (tab.sourceFolderId) {
    return tab.sourceFolderId;
  }
  if (context.lastClickedFolderId) {
    return context.lastClickedFolderId;
  }
  return null;
}

const NAME_HINT_MAX_LENGTH = 16;
const NAME_FALLBACK_NEW = "新接口";

function truncateHint(text: string, maxLength: number): string {
  const trimmed = text.trim();
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength)}…`;
}

function extractQueryHint(parsedUrl: URL): string {
  for (const [key, value] of parsedUrl.searchParams.entries()) {
    if (!key) {
      continue;
    }
    if (value) {
      return `${key}=${truncateHint(value, 10)}`;
    }
    return key;
  }
  return "";
}

function extractBodyHint(body: string, bodyType: string): string {
  if (!body.trim() || bodyType === "none") {
    return "";
  }
  try {
    const parsed = JSON.parse(body) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      const entries = Object.entries(parsed as Record<string, unknown>);
      for (const [key, value] of entries) {
        if (typeof value === "string" && value.trim()) {
          return `${key}=${truncateHint(value, 10)}`;
        }
        if (typeof value === "number" || typeof value === "boolean") {
          return `${key}=${String(value)}`;
        }
      }
      if (entries[0]) {
        return truncateHint(entries[0][0], NAME_HINT_MAX_LENGTH);
      }
    }
  } catch {
    return truncateHint(body.replace(/\s+/g, " "), NAME_HINT_MAX_LENGTH);
  }
  return "";
}

export function suggestRequestName(
  draft: ApiRequestItem | null,
  parsedPreview: { method: string; url: string } | null,
): string {
  const url = draft?.url || parsedPreview?.url || "";
  if (!url.trim()) {
    return draft?.name?.trim() || NAME_FALLBACK_NEW;
  }
  try {
    const normalized = url.includes("://") ? url : `http://${url}`;
    const parsed = new URL(normalized);
    const host = parsed.hostname || parsed.host;
    const pathSegment = parsed.pathname.split("/").filter(Boolean).pop() || "";
    const method = (draft?.method || parsedPreview?.method || "").toUpperCase();
    const queryHint = extractQueryHint(parsed);
    const bodyHint = extractBodyHint(
      draft?.body || "",
      draft?.body_type || "none",
    );
    const distinguish = queryHint || bodyHint || method;

    let base = "";
    if (host && pathSegment) {
      base = `${host} ${pathSegment}`;
    } else if (host) {
      base = method ? `${host} ${method}` : host;
    } else {
      base = pathSegment || draft?.name?.trim() || NAME_FALLBACK_NEW;
    }

    if (distinguish && !base.includes(distinguish)) {
      return `${base} · ${truncateHint(distinguish, NAME_HINT_MAX_LENGTH)}`;
    }
    return base;
  } catch {
    return draft?.name?.trim() || NAME_FALLBACK_NEW;
  }
}

export function createNewRequestId(): string {
  const suffix = Math.random().toString(36).slice(2, 10);
  return `req-${Date.now().toString(36)}-${suffix}`;
}

export function appendRequestToTree(
  tree: TreeNode[],
  folderId: string | null,
  request: ApiRequestItem,
): boolean {
  if (!folderId) {
    tree.push(request);
    return true;
  }
  for (const node of tree) {
    if (node.type === "folder" && node.id === folderId) {
      node.children.push(request);
      return true;
    }
    if (
      node.type === "folder" &&
      appendRequestToTree(node.children, folderId, request)
    ) {
      return true;
    }
  }
  return false;
}

export function updateRequestInTree(
  tree: TreeNode[],
  request: ApiRequestItem,
): boolean {
  for (let index = 0; index < tree.length; index += 1) {
    const node = tree[index];
    if (node.type === "request" && node.id === request.id) {
      tree[index] = request;
      return true;
    }
    if (node.type === "folder" && updateRequestInTree(node.children, request)) {
      return true;
    }
  }
  return false;
}

export function requestExistsInTree(
  tree: TreeNode[],
  requestId: string,
): boolean {
  for (const node of tree) {
    if (node.type === "request" && node.id === requestId) {
      return true;
    }
    if (
      node.type === "folder" &&
      requestExistsInTree(node.children, requestId)
    ) {
      return true;
    }
  }
  return false;
}

export function findProjectByName(
  projects: Array<{ id: string; name: string }>,
  name: string,
): { id: string; name: string } | undefined {
  const trimmed = name.trim();
  return projects.find((item) => item.name === trimmed);
}

export function findFolderByName(
  tree: TreeNode[],
  name: string,
): FolderItem | undefined {
  const trimmed = name.trim();
  for (const node of tree) {
    if (node.type === "folder") {
      if (node.name === trimmed) {
        return node;
      }
      const nested = findFolderByName(node.children, name);
      if (nested) {
        return nested;
      }
    }
  }
  return undefined;
}
