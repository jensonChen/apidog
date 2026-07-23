<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { ElMessage } from "element-plus";
import ProjectSidebar from "./components/ProjectSidebar.vue";
import RequestEditor from "./components/RequestEditor.vue";
import ResponsePanel from "./components/ResponsePanel.vue";
import HistoryPanel from "./components/HistoryPanel.vue";
import SessionTabBar from "./components/SessionTabBar.vue";
import TitleBar from "./components/TitleBar.vue";
import type {
  ApiRequestItem,
  HistoryItem,
  ProjectCollection,
  WorkspaceContextState,
} from "./types";
import {
  convertRequestToCurl,
  fetchConfig,
  fetchHistory,
  fetchProject,
  fetchWorkspace,
} from "./api/client";
import {
  createEmptyTab,
  createTabFromRequest,
} from "./composables/workbenchTabs";
import { findRequestParentFolderId } from "./composables/workspaceContext";

const SIDEBAR_WIDTH_STORAGE_KEY = "aw-sidebar-width";
const SIDEBAR_WIDTH_DEFAULT = 300;
const SIDEBAR_WIDTH_MIN = 220;
const SIDEBAR_WIDTH_MAX = 520;

const projects = ref<Array<{ id: string; name: string; file: string }>>([]);
const project = ref<ProjectCollection | null>(null);
const historyItems = ref<HistoryItem[]>([]);
const tabs = ref([createEmptyTab()]);
const activeTabId = ref(tabs.value[0].id);
const workspaceContext = ref<WorkspaceContextState>({
  lastClickedFolderId: null,
});
const sidebarWidth = ref(SIDEBAR_WIDTH_DEFAULT);
const isResizingSidebar = ref(false);
const desktopShell = ref(false);
const emptyHintVisible = computed(() => !project.value);

const activeTab = computed({
  get() {
    return (
      tabs.value.find((tab) => tab.id === activeTabId.value) || tabs.value[0]
    );
  },
  set(nextTab) {
    const index = tabs.value.findIndex((tab) => tab.id === nextTab.id);
    if (index >= 0) {
      tabs.value[index] = nextTab;
    }
  },
});

function clampSidebarWidth(width: number): number {
  return Math.min(SIDEBAR_WIDTH_MAX, Math.max(SIDEBAR_WIDTH_MIN, width));
}

function loadSidebarWidth() {
  const raw = localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY);
  if (!raw) {
    return;
  }
  const parsed = Number(raw);
  if (Number.isFinite(parsed)) {
    sidebarWidth.value = clampSidebarWidth(parsed);
  }
}

function persistSidebarWidth() {
  localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth.value));
}

function handleSidebarResizeMove(event: MouseEvent) {
  if (!isResizingSidebar.value) {
    return;
  }
  sidebarWidth.value = clampSidebarWidth(event.clientX);
}

function handleSidebarResizeEnd() {
  if (!isResizingSidebar.value) {
    return;
  }
  isResizingSidebar.value = false;
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  persistSidebarWidth();
}

function startSidebarResize(event: MouseEvent) {
  event.preventDefault();
  isResizingSidebar.value = true;
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
}

async function loadWorkspace() {
  const workspace = await fetchWorkspace();
  projects.value = workspace.projects;

  const activeProjectId =
    workspace.index.active_project_id || workspace.projects[0]?.id || "";

  if (activeProjectId) {
    project.value = await fetchProject(activeProjectId);
  } else {
    project.value = null;
  }
  historyItems.value = await fetchHistory(20);
}

async function openRequestInNewTab(request: ApiRequestItem) {
  const sourceFolderId = project.value
    ? findRequestParentFolderId(project.value.tree, request.id)
    : null;
  const tab = createTabFromRequest(request, sourceFolderId);
  if (tab.draft) {
    tab.curlText = await convertRequestToCurl(tab.draft);
  }
  tabs.value.push(tab);
  activeTabId.value = tab.id;
}

function handleWorkspaceContextUpdate(folderId: string | null) {
  workspaceContext.value.lastClickedFolderId = folderId;
}

function handleAddTab() {
  const tab = createEmptyTab();
  tabs.value.push(tab);
  activeTabId.value = tab.id;
}

function handleSelectTab(tabId: string) {
  activeTabId.value = tabId;
}

function handleCloseTab(tabId: string) {
  if (tabs.value.length === 1) {
    tabs.value = [createEmptyTab()];
    activeTabId.value = tabs.value[0].id;
    return;
  }
  const index = tabs.value.findIndex((tab) => tab.id === tabId);
  if (index < 0) {
    return;
  }
  tabs.value.splice(index, 1);
  if (activeTabId.value === tabId) {
    activeTabId.value = tabs.value[Math.max(0, index - 1)].id;
  }
}

function handleCloseAllTabs() {
  tabs.value = [createEmptyTab()];
  activeTabId.value = tabs.value[0].id;
}

async function handleProjectChanged() {
  await loadWorkspace();
}

async function handleExecuted() {
  historyItems.value = await fetchHistory(20);
}

onMounted(() => {
  loadSidebarWidth();
  window.addEventListener("mousemove", handleSidebarResizeMove);
  window.addEventListener("mouseup", handleSidebarResizeEnd);
  fetchConfig()
    .then((config) => {
      desktopShell.value = Boolean(config.desktop_shell);
    })
    .catch(() => {
      desktopShell.value = false;
    });
  loadWorkspace().catch((error) => {
    ElMessage.error(error instanceof Error ? error.message : "加载失败");
  });
});

onUnmounted(() => {
  window.removeEventListener("mousemove", handleSidebarResizeMove);
  window.removeEventListener("mouseup", handleSidebarResizeEnd);
});
</script>

<template>
  <div
    class="layout"
    :class="{ resizing: isResizingSidebar, desktop: desktopShell }"
  >
    <TitleBar :desktop-shell="desktopShell">
      <p v-if="emptyHintVisible" class="chrome-hint">
        请先在左侧选择或创建一个项目
      </p>
    </TitleBar>

    <div class="workbench">
      <ProjectSidebar
        :project-id="project?.id || ''"
        :project-name="project?.name || ''"
        :tree="project?.tree || []"
        :projects="projects"
        :width="sidebarWidth"
        @select-request="openRequestInNewTab"
        @project-changed="handleProjectChanged"
        @update-workspace-context="handleWorkspaceContextUpdate"
      />

      <div
        class="sidebar-resizer"
        title="拖动调整左侧宽度"
        @mousedown="startSidebarResize"
      />

      <div class="center-column">
        <SessionTabBar
          :tabs="tabs"
          :active-tab-id="activeTabId"
          @select="handleSelectTab"
          @add="handleAddTab"
          @close="handleCloseTab"
          @close-all="handleCloseAllTabs"
        />

        <RequestEditor
          v-if="activeTab"
          v-model="activeTab"
          :project-id="project?.id || ''"
          :project-name="project?.name || ''"
          :project-tree="project?.tree || []"
          :projects="projects"
          :workspace-context="workspaceContext"
          @saved="handleProjectChanged"
          @executed="handleExecuted"
        />
      </div>

      <div class="right-column">
        <ResponsePanel
          :result="activeTab?.response || null"
          :tab-title="activeTab?.title"
        />
        <HistoryPanel :items="historyItems" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 8%, var(--aw-glow-a), transparent 36%),
    radial-gradient(circle at 88% 0%, var(--aw-glow-b), transparent 32%),
    var(--aw-bg);
}

.layout.resizing {
  cursor: col-resize;
}

.chrome-hint {
  margin: 0;
  font-size: 12px;
  color: var(--aw-warn);
  background: var(--aw-warn-soft);
  border: 1px solid color-mix(in srgb, var(--aw-warn) 35%, transparent);
  border-radius: 999px;
  padding: 4px 12px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.workbench {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: stretch;
  padding: 12px;
  gap: 0;
  overflow: hidden;
}

.sidebar-resizer {
  width: 6px;
  flex-shrink: 0;
  margin-left: -3px;
  margin-right: -3px;
  position: relative;
  z-index: 5;
  cursor: col-resize;
  background: transparent;
}

.sidebar-resizer::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: 2px;
  width: 2px;
  background: transparent;
  transition: background 0.15s ease;
}

.sidebar-resizer:hover::after,
.layout.resizing .sidebar-resizer::after {
  background: var(--aw-accent);
}

.center-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin: 0 12px;
  padding: 10px 12px 12px;
  background: var(--aw-bg-panel);
  border: 1px solid var(--aw-border);
  border-radius: var(--aw-radius);
  box-shadow: var(--aw-shadow);
}

.right-column {
  width: 420px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 1200px) {
  .right-column {
    width: 360px;
  }
}
</style>

<style>
html,
body,
#app {
  height: 100%;
  overflow: hidden;
  background: var(--aw-bg);
}
</style>
