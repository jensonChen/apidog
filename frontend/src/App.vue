<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import ProjectSidebar from "./components/ProjectSidebar.vue";
import RequestEditor from "./components/RequestEditor.vue";
import ResponsePanel from "./components/ResponsePanel.vue";
import HistoryPanel from "./components/HistoryPanel.vue";
import SessionTabBar from "./components/SessionTabBar.vue";
import type { ApiRequestItem, HistoryItem, ProjectCollection } from "./types";
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

const projects = ref<Array<{ id: string; name: string; file: string }>>([]);
const project = ref<ProjectCollection | null>(null);
const historyItems = ref<HistoryItem[]>([]);
const tabs = ref([createEmptyTab()]);
const activeTabId = ref(tabs.value[0].id);

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
  const tab = createTabFromRequest(request);
  if (tab.draft) {
    tab.curlText = await convertRequestToCurl(tab.draft);
  }
  tabs.value.push(tab);
  activeTabId.value = tab.id;
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
  loadWorkspace().catch((error) => {
    ElMessage.error(error instanceof Error ? error.message : "加载失败");
  });
});
</script>

<template>
  <div class="layout">
    <ProjectSidebar
      v-if="project"
      :project-id="project.id"
      :project-name="project.name"
      :tree="project.tree"
      :projects="projects"
      @select-request="openRequestInNewTab"
      @project-changed="handleProjectChanged"
    />

    <div class="center-column">
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark">AW</div>
          <div>
            <h1>ApiWorkbench</h1>
            <p>多标签并行 · Chrome 粘贴即测 · 响应右侧固定可见</p>
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
    radial-gradient(
      circle at 12% 8%,
      rgba(126, 179, 232, 0.08),
      transparent 36%
    ),
    radial-gradient(
      circle at 88% 0%,
      rgba(110, 196, 154, 0.06),
      transparent 32%
    ),
    var(--aw-bg);
}

.center-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 14px 12px 14px 0;
  overflow: hidden;
}

.right-column {
  width: 440px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 14px 14px 0;
  min-height: 0;
  overflow: hidden;
}

.topbar {
  margin-bottom: 10px;
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
  background: linear-gradient(145deg, #5a96cc, #6ec49a);
  color: #1f2836;
  font-weight: 700;
  font-size: 14px;
  display: grid;
  place-items: center;
}

.topbar h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.topbar p {
  margin: 3px 0 0;
  color: var(--aw-text-muted);
  font-size: 12px;
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
