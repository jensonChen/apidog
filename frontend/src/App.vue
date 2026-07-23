<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { ElMessage } from "element-plus";
import ProjectSidebar from "./components/ProjectSidebar.vue";
import RequestEditor from "./components/RequestEditor.vue";
import ResponsePanel from "./components/ResponsePanel.vue";
import HistoryPanel from "./components/HistoryPanel.vue";
import SessionTabBar from "./components/SessionTabBar.vue";
import type {
  ApiRequestItem,
  HistoryItem,
  ProjectCollection,
  WorkspaceContextState,
} from "./types";
import {
  convertRequestToCurl,
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
  <div class="layout" :class="{ resizing: isResizingSidebar }">
    <ProjectSidebar
      v-if="project"
      :project-id="project.id"
      :project-name="project.name"
      :tree="project.tree"
      :projects="projects"
      :width="sidebarWidth"
      @select-request="openRequestInNewTab"
      @project-changed="handleProjectChanged"
      @update-workspace-context="handleWorkspaceContextUpdate"
    />

    <div
      v-if="project"
      class="sidebar-resizer"
      title="拖动调整左侧宽度"
      @mousedown="startSidebarResize"
    />

    <div class="center-column">
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="awBrandBg" x1="12" y1="8" x2="54" y2="58">
                  <stop stop-color="#243140" />
                  <stop offset="1" stop-color="#1a2430" />
                </linearGradient>
                <linearGradient id="awBrandDog" x1="18" y1="16" x2="46" y2="48">
                  <stop stop-color="#7ec4b4" />
                  <stop offset="1" stop-color="#5a9fad" />
                </linearGradient>
              </defs>
              <rect width="64" height="64" rx="14" fill="url(#awBrandBg)" />
              <rect
                x="8"
                y="8"
                width="48"
                height="48"
                rx="12"
                fill="#2a3848"
                opacity="0.55"
              />
              <path
                fill="url(#awBrandDog)"
                d="M22 42c-1.2-6.2 1.4-12.8 6.8-16.2 2.2-1.4 3.4-3.8 3.1-6.4l-.2-1.6c-.2-1.4 1.2-2.4 2.4-1.8l4.2 2.1c1.4.7 3 .9 4.5.6l3.8-.8c1.5-.3 2.8 1.1 2.3 2.5l-1.4 3.7c-.5 1.4-.2 2.9.8 4 2.6 2.8 3.8 6.8 3.1 10.7-.8 4.6-4.4 8.2-9 9.1-6.8 1.3-13.3-2.2-15.4-5.9z"
              />
              <circle cx="34.5" cy="30.5" r="2.1" fill="#1a2430" />
              <circle cx="35.1" cy="30" r="0.7" fill="#d7efe8" />
              <circle cx="46.5" cy="18.5" r="3.2" fill="#c9a66b" />
              <circle
                cx="46.5"
                cy="18.5"
                r="5.2"
                fill="none"
                stroke="#c9a66b"
                stroke-opacity="0.35"
                stroke-width="1.5"
              />
            </svg>
          </div>
          <div>
            <h1>ApiDog</h1>
          </div>
        </div>
      </header>

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
</template>

<style scoped>
.layout {
  display: flex;
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
  padding: 16px 14px 16px 0;
  overflow: hidden;
  gap: 2px;
}

.right-column {
  width: 440px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 16px 16px 0;
  min-height: 0;
  overflow: hidden;
}

.topbar {
  margin-bottom: 8px;
  padding: 0 4px;
  flex-shrink: 0;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: var(--aw-shadow);
  border: 1px solid var(--aw-border);
}

.brand-mark svg {
  width: 100%;
  height: 100%;
  display: block;
}

.topbar h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
  letter-spacing: 0.01em;
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
}
</style>
