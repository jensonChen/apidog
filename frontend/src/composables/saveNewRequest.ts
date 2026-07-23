import { ElMessage } from "element-plus";
import type { ApiRequestItem, ProjectCollection, WorkbenchTab } from "../types";
import {
  addFolder,
  convertCurlToRequest,
  createProject,
  fetchProject,
  parseChromePaste,
  saveProject,
  setActiveWorkspace,
} from "../api/client";
import {
  appendRequestToTree,
  createNewRequestId,
  findFolderByName,
  findProjectByName,
  requestExistsInTree,
  updateRequestInTree,
} from "./workspaceContext";

export interface SaveFormValues {
  requestName: string;
  projectName: string;
  folderName: string;
  folderId: string | null;
  isNewProject: boolean;
  isNewFolder: boolean;
}

export interface SaveNewRequestPayload {
  tab: WorkbenchTab;
  form: SaveFormValues;
  projects: Array<{ id: string; name: string; file: string }>;
  currentProjectId: string;
  currentProjectName: string;
}

export interface UpdateExistingRequestPayload {
  tab: WorkbenchTab;
  projectId: string;
  projectName: string;
  projectTree: ProjectCollection["tree"];
}

function preservePersistedIdentity(
  tab: WorkbenchTab,
  parsed: ApiRequestItem,
): ApiRequestItem {
  if (!tab.isPersisted || !tab.draft) {
    return parsed;
  }
  return {
    ...parsed,
    id: tab.draft.id,
    name: tab.draft.name || parsed.name,
  };
}

async function ensureDraftReady(tab: WorkbenchTab): Promise<ApiRequestItem> {
  if (tab.editMode === "chrome") {
    if (!tab.chromeText.trim()) {
      throw new Error("请先粘贴 Chrome 内容");
    }
    const parsed = await parseChromePaste(tab.chromeText, tab.payloadExtra);
    const request = preservePersistedIdentity(tab, parsed.request);
    tab.draft = request;
    tab.parsedPreview = {
      method: request.method,
      url: request.url,
    };
    tab.curlText = parsed.curl_text;
    return request;
  }
  if (tab.editMode === "curl") {
    if (!tab.curlText.trim()) {
      throw new Error("请先输入 Curl 命令");
    }
    const parsed = await convertCurlToRequest(tab.curlText);
    const request = preservePersistedIdentity(tab, {
      ...parsed,
      name: tab.draft?.name || parsed.name,
    });
    tab.draft = request;
    tab.parsedPreview = { method: request.method, url: request.url };
    return request;
  }
  if (!tab.draft) {
    throw new Error("没有可保存的请求内容");
  }
  return tab.draft;
}

async function resolveTargetProject(
  form: SaveFormValues,
  projects: SaveNewRequestPayload["projects"],
  currentProjectId: string,
  currentProjectName: string,
): Promise<ProjectCollection> {
  const existing = findProjectByName(projects, form.projectName);
  if (existing) {
    return fetchProject(existing.id);
  }
  if (
    form.projectName.trim() === currentProjectName.trim() &&
    currentProjectId
  ) {
    return fetchProject(currentProjectId);
  }
  const created = await createProject(form.projectName.trim());
  await setActiveWorkspace({ active_project_id: created.id });
  return created;
}

async function resolveTargetFolder(
  project: ProjectCollection,
  form: SaveFormValues,
): Promise<{ project: ProjectCollection; folderId: string | null }> {
  if (!form.folderName.trim()) {
    return { project, folderId: form.folderId };
  }
  const existingFolder = findFolderByName(project.tree, form.folderName);
  if (existingFolder) {
    return { project, folderId: existingFolder.id };
  }
  if (form.isNewFolder) {
    const updated = await addFolder(project.id, form.folderName.trim());
    const createdFolder = findFolderByName(updated.tree, form.folderName);
    if (!createdFolder) {
      throw new Error(`创建模块「${form.folderName.trim()}」失败`);
    }
    return { project: updated, folderId: createdFolder.id };
  }
  return { project, folderId: form.folderId };
}

function buildNewRequest(
  draft: ApiRequestItem,
  requestName: string,
): ApiRequestItem {
  return {
    ...JSON.parse(JSON.stringify(draft)),
    type: "request",
    id: createNewRequestId(),
    name: requestName.trim(),
  };
}

export function canUpdateExistingRequest(
  tab: WorkbenchTab,
  projectTree: ProjectCollection["tree"],
): boolean {
  if (!tab.isPersisted || !tab.draft?.id) {
    return false;
  }
  return requestExistsInTree(projectTree, tab.draft.id);
}

export async function updateExistingRequest(
  payload: UpdateExistingRequestPayload,
): Promise<{ project: ProjectCollection; request: ApiRequestItem }> {
  const draft = await ensureDraftReady(payload.tab);
  if (!draft.id) {
    throw new Error("当前接口缺少 ID，无法更新");
  }
  if (!requestExistsInTree(payload.projectTree, draft.id)) {
    throw new Error("当前接口已不在项目中，请改为保存为新接口");
  }

  const updatedRequest: ApiRequestItem = {
    ...JSON.parse(JSON.stringify(draft)),
    type: "request",
    id: draft.id,
    name: draft.name.trim() || draft.name,
  };

  const tree = JSON.parse(
    JSON.stringify(payload.projectTree),
  ) as ProjectCollection["tree"];
  if (!updateRequestInTree(tree, updatedRequest)) {
    throw new Error("更新接口失败：未找到原记录");
  }

  const project = await saveProject({
    id: payload.projectId,
    name: payload.projectName,
    updated_at: "",
    tree,
  });

  payload.tab.draft = updatedRequest;
  payload.tab.isPersisted = true;
  payload.tab.title = updatedRequest.name;

  return { project, request: updatedRequest };
}

export async function saveNewRequest(
  payload: SaveNewRequestPayload,
): Promise<{ project: ProjectCollection; request: ApiRequestItem }> {
  const draft = await ensureDraftReady(payload.tab);
  if (!payload.form.requestName.trim()) {
    throw new Error("请填写接口名称");
  }
  if (!payload.form.projectName.trim()) {
    throw new Error("请选择或输入所属项目");
  }

  let project = await resolveTargetProject(
    payload.form,
    payload.projects,
    payload.currentProjectId,
    payload.currentProjectName,
  );

  const resolvedFolder = await resolveTargetFolder(project, payload.form);
  project = resolvedFolder.project;
  const folderId = resolvedFolder.folderId;
  if (payload.form.isNewFolder && !folderId) {
    throw new Error("新模块创建失败，请重试");
  }

  const newRequest = buildNewRequest(draft, payload.form.requestName);
  const tree = JSON.parse(
    JSON.stringify(project.tree),
  ) as ProjectCollection["tree"];
  const inserted = appendRequestToTree(tree, folderId, newRequest);
  if (!inserted) {
    throw new Error("未能将接口放入目标模块，请重新选择模块后保存");
  }

  project = await saveProject({
    id: project.id,
    name: project.name,
    updated_at: project.updated_at,
    tree,
  });

  payload.tab.draft = newRequest;
  payload.tab.isPersisted = true;
  payload.tab.sourceFolderId = folderId;
  payload.tab.title = newRequest.name;

  return { project, request: newRequest };
}

export async function prepareTabForSaveDialog(
  tab: WorkbenchTab,
): Promise<ApiRequestItem | null> {
  try {
    return await ensureDraftReady(tab);
  } catch (error) {
    const message = error instanceof Error ? error.message : "请先完善请求内容";
    ElMessage.error(message);
    return null;
  }
}
