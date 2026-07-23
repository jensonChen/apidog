<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { ApiRequestItem, FolderItem, TreeNode } from "../types";
import {
  addFolder,
  addRequest,
  createProject,
  deleteNode,
  deleteProject,
  importPostman,
  saveProject,
  setActiveWorkspace,
} from "../api/client";
import { findRequestParentFolderId } from "../composables/workspaceContext";

const props = defineProps<{
  projectId: string;
  projectName: string;
  tree: TreeNode[];
  projects: Array<{ id: string; name: string; file: string }>;
  width: number;
}>();

const emit = defineEmits<{
  selectRequest: [request: ApiRequestItem];
  projectChanged: [];
  updateWorkspaceContext: [folderId: string | null];
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const dragging = ref(false);

interface TreeRow {
  id: string;
  label: string;
  type: "folder" | "request";
  method?: string;
  node: TreeNode;
  children?: TreeRow[];
}

const treeData = ref<TreeRow[]>([]);

function buildTreeRows(nodes: TreeNode[]): TreeRow[] {
  return nodes.map((node) => {
    if (node.type === "folder") {
      return {
        id: node.id,
        label: node.name,
        type: "folder",
        node,
        children: buildTreeRows(node.children),
      };
    }
    return {
      id: node.id,
      label: node.name,
      type: "request",
      method: node.method,
      node,
    };
  });
}

function treeRowsToNodes(rows: TreeRow[]): TreeNode[] {
  return rows.map((row) => {
    if (row.type === "folder") {
      const folder = row.node as FolderItem;
      return {
        type: "folder" as const,
        id: folder.id,
        name: folder.name,
        children: treeRowsToNodes(row.children || []),
      };
    }
    return {
      ...(row.node as ApiRequestItem),
    };
  });
}

watch(
  () => props.tree,
  (nodes) => {
    if (dragging.value) {
      return;
    }
    treeData.value = buildTreeRows(nodes);
  },
  { immediate: true, deep: true },
);

function handleNodeClick(row: TreeRow) {
  if (row.type === "folder") {
    emit("updateWorkspaceContext", row.id);
    return;
  }
  const parentFolderId = findRequestParentFolderId(props.tree, row.id);
  emit("updateWorkspaceContext", parentFolderId);
  emit("selectRequest", row.node as ApiRequestItem);
}

function allowDrop(
  draggingNode: { data: TreeRow },
  dropNode: { data: TreeRow },
  type: "prev" | "inner" | "next",
): boolean {
  if (dropNode.data.type === "request" && type === "inner") {
    return false;
  }
  if (draggingNode.data.type === "folder" && dropNode.data.type === "request") {
    return type !== "inner";
  }
  return true;
}

async function handleNodeDrop() {
  dragging.value = false;
  try {
    const nextTree = treeRowsToNodes(treeData.value);
    await saveProject({
      id: props.projectId,
      name: props.projectName,
      updated_at: "",
      tree: nextTree,
    });
    ElMessage.success("已更新目录结构");
    emit("projectChanged");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "拖拽保存失败");
    treeData.value = buildTreeRows(props.tree);
  }
}

function handleNodeDragStart() {
  dragging.value = true;
}

function handleNodeDragEnd() {
  dragging.value = false;
}

async function handleCreateProject() {
  const { value } = await ElMessageBox.prompt("请输入项目名称", "新建项目", {
    confirmButtonText: "创建",
    cancelButtonText: "取消",
  });
  if (!value?.trim()) {
    return;
  }
  await createProject(value.trim());
  ElMessage.success("项目已创建");
  emit("projectChanged");
}

async function handleAddFolder() {
  const { value } = await ElMessageBox.prompt("请输入模块名称", "新建模块", {
    confirmButtonText: "创建",
    cancelButtonText: "取消",
  });
  if (!value?.trim()) {
    return;
  }
  await addFolder(props.projectId, value.trim());
  ElMessage.success("模块已创建");
  emit("projectChanged");
}

async function handleAddRequest() {
  const { value } = await ElMessageBox.prompt("请输入接口名称", "新建接口", {
    confirmButtonText: "创建",
    cancelButtonText: "取消",
  });
  if (!value?.trim()) {
    return;
  }
  const project = await addRequest(props.projectId, value.trim());
  ElMessage.success("接口已创建");
  emit("projectChanged");
  const created = findFirstRequest(project.tree);
  if (created) {
    emit("selectRequest", created);
  }
}

function findFirstRequest(nodes: TreeNode[]): ApiRequestItem | null {
  for (const node of nodes) {
    if (node.type === "request") {
      return node;
    }
    if (node.type === "folder") {
      const found = findFirstRequest(node.children);
      if (found) {
        return found;
      }
    }
  }
  return null;
}

async function handleDeleteNode(row: TreeRow) {
  await ElMessageBox.confirm(`确定删除「${row.label}」吗？`, "删除确认", {
    type: "warning",
  });
  await deleteNode(props.projectId, row.id);
  ElMessage.success("已删除");
  emit("projectChanged");
}

async function handleDeleteProject() {
  await ElMessageBox.confirm(
    `确定删除项目「${props.projectName}」吗？`,
    "删除项目",
    {
      type: "warning",
    },
  );
  await deleteProject(props.projectId);
  ElMessage.success("项目已删除");
  emit("projectChanged");
}

function triggerImport() {
  fileInputRef.value?.click();
}

async function handleImportFile(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  target.value = "";
  if (!file) {
    return;
  }
  try {
    await importPostman(file);
    ElMessage.success(`已导入 Postman 集合：${file.name}`);
    emit("projectChanged");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "导入失败");
  }
}

async function handleProjectSelect(projectId: string) {
  await setActiveWorkspace({ active_project_id: projectId });
  emit("projectChanged");
}

const HTTP_METHOD_POST = "POST";
const HTTP_METHOD_PUT = "PUT";
const HTTP_METHOD_PATCH = "PATCH";
const HTTP_METHOD_DELETE = "DELETE";
const HTTP_METHOD_GET = "GET";

function methodClass(method?: string): string {
  const normalized = (method || HTTP_METHOD_GET).toUpperCase();
  if (normalized === HTTP_METHOD_POST) {
    return "method-post";
  }
  if (normalized === HTTP_METHOD_PUT || normalized === HTTP_METHOD_PATCH) {
    return "method-put";
  }
  if (normalized === HTTP_METHOD_DELETE) {
    return "method-delete";
  }
  return "method-get";
}
</script>

<template>
  <aside class="sidebar" :style="{ width: `${width}px` }">
    <div class="sidebar-head">
      <h2>接口集合</h2>
      <span class="drag-hint">可拖拽整理</span>
    </div>

    <div class="toolbar">
      <el-select
        :model-value="projectId"
        placeholder="选择项目"
        style="width: 100%"
        @change="handleProjectSelect"
      >
        <el-option
          v-for="item in projects"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>
      <div class="toolbar-row">
        <el-button size="small" @click="handleCreateProject"
          >新建项目</el-button
        >
        <el-button
          size="small"
          type="danger"
          plain
          @click="handleDeleteProject"
        >
          删项目
        </el-button>
      </div>
      <div class="toolbar-row">
        <el-button size="small" @click="handleAddFolder">新建模块</el-button>
        <el-button size="small" @click="handleAddRequest">新建接口</el-button>
      </div>
      <el-button
        size="small"
        type="primary"
        plain
        style="width: 100%"
        @click="triggerImport"
      >
        导入 Postman
      </el-button>
      <input
        ref="fileInputRef"
        type="file"
        accept="application/json,.json"
        hidden
        @change="handleImportFile"
      />
    </div>

    <el-tree
      :data="treeData"
      node-key="id"
      default-expand-all
      highlight-current
      draggable
      :allow-drop="allowDrop"
      class="tree"
      @node-click="handleNodeClick"
      @node-drag-start="handleNodeDragStart"
      @node-drag-end="handleNodeDragEnd"
      @node-drop="handleNodeDrop"
    >
      <template #default="{ data }">
        <div class="tree-node" :class="data.type">
          <div class="node-main">
            <span
              v-if="data.type === 'folder'"
              class="folder-mark"
              aria-hidden="true"
            >
              <svg viewBox="0 0 16 16" width="14" height="14">
                <path
                  fill="currentColor"
                  d="M1.5 3.5A1.5 1.5 0 0 1 3 2h3.2c.3 0 .6.1.8.3L8.3 3.5H13A1.5 1.5 0 0 1 14.5 5v7A1.5 1.5 0 0 1 13 13.5H3A1.5 1.5 0 0 1 1.5 12V3.5z"
                />
              </svg>
            </span>
            <span v-else class="method-badge" :class="methodClass(data.method)">
              {{ (data.method || "GET").slice(0, 4) }}
            </span>
            <span class="node-label">{{ data.label }}</span>
          </div>
          <el-button
            link
            type="danger"
            size="small"
            class="delete-btn"
            @click.stop="handleDeleteNode(data)"
          >
            删
          </el-button>
        </div>
      </template>
    </el-tree>
  </aside>
</template>

<style scoped>
.sidebar {
  flex-shrink: 0;
  background: var(--aw-bg-panel);
  border-right: 1px solid var(--aw-border);
  padding: 18px 16px;
  box-sizing: border-box;
  overflow: auto;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.12);
}

.sidebar-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
  gap: 8px;
}

.sidebar-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
  color: var(--aw-text);
}

.drag-hint {
  font-size: 11px;
  color: var(--aw-text-muted);
  letter-spacing: 0.02em;
}

.toolbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.toolbar-row {
  display: flex;
  gap: 8px;
}

.toolbar-row .el-button {
  flex: 1;
}

.tree {
  background: transparent;
}

.tree-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 2px 6px 2px 0;
  gap: 6px;
  font-size: 13px;
  border-radius: 6px;
}

.tree-node.folder .node-label {
  font-weight: 650;
  color: var(--aw-text);
}

.tree-node.request .node-label {
  font-weight: 450;
  color: var(--aw-text-muted);
}

.node-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.folder-mark {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 18px;
  border-radius: 4px;
  color: var(--aw-warn);
  background: var(--aw-warn-soft);
  flex-shrink: 0;
}

.method-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 18px;
  padding: 0 4px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.02em;
  font-family: var(--aw-mono);
  flex-shrink: 0;
}

.method-get {
  color: var(--aw-send);
  background: var(--aw-send-soft);
}

.method-post {
  color: var(--aw-accent);
  background: var(--aw-accent-soft);
}

.method-put {
  color: var(--aw-warn);
  background: var(--aw-warn-soft);
}

.method-delete {
  color: var(--aw-danger);
  background: var(--aw-danger-soft);
}

.node-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  opacity: 0.55;
  flex-shrink: 0;
}

.tree-node:hover .delete-btn {
  opacity: 1;
}

:deep(.el-tree-node__content) {
  height: 34px;
  border-radius: 6px;
}

:deep(.el-tree-node.is-drop-inner > .el-tree-node__content) {
  background: var(--aw-accent-soft);
  outline: 1px dashed var(--aw-accent);
}
</style>
