<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import type { WorkbenchTab, WorkspaceContextState } from "../types";
import {
  convertCurlToRequest,
  convertRequestToCurl,
  executeRequest,
  parseChromePaste,
} from "../api/client";
import { attachResponse } from "../composables/workbenchTabs";
import {
  canUpdateExistingRequest,
  prepareTabForSaveDialog,
  saveNewRequest,
  updateExistingRequest,
} from "../composables/saveNewRequest";
import { suggestRequestName } from "../composables/workspaceContext";
import SaveRequestDialog from "./SaveRequestDialog.vue";

const tab = defineModel<WorkbenchTab>({ required: true });

const props = defineProps<{
  projectId: string;
  projectName: string;
  projectTree: import("../types").TreeNode[];
  projects: Array<{ id: string; name: string; file: string }>;
  workspaceContext: WorkspaceContextState;
}>();

const emit = defineEmits<{
  saved: [];
  executed: [];
}>();

const loading = ref(false);
const saving = ref(false);
const preparingSave = ref(false);
const saveDialogVisible = ref(false);

const isUpdateSave = computed(() =>
  canUpdateExistingRequest(tab.value, props.projectTree),
);

const saveShortcutHint = computed(() =>
  isUpdateSave.value
    ? "Ctrl+S 更新当前接口 · Ctrl+Enter 发送"
    : "Ctrl+S 保存为新接口 · Ctrl+Enter 发送",
);

const suggestedSaveName = computed(() =>
  suggestRequestName(tab.value.draft, tab.value.parsedPreview),
);

const defaultSaveFolderId = computed(() => {
  if (tab.value.sourceFolderId) {
    return tab.value.sourceFolderId;
  }
  if (props.workspaceContext.lastClickedFolderId) {
    return props.workspaceContext.lastClickedFolderId;
  }
  return null;
});

async function applyParsedRequest(request: import("../types").ApiRequestItem) {
  tab.value.draft = request;
  tab.value.parsedPreview = { method: request.method, url: request.url };
  tab.value.curlText = await convertRequestToCurl(request);
}

async function handleParseChrome() {
  if (!tab.value.chromeText.trim()) {
    ElMessage.warning("请先粘贴 Chrome 网络面板复制的内容");
    return;
  }
  try {
    const result = await parseChromePaste(
      tab.value.chromeText,
      tab.value.payloadExtra,
    );
    await applyParsedRequest(result.request);
    tab.value.title = result.request.name;
    ElMessage.success("已解析，可直接发送");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "解析失败");
  }
}

async function handleSendChrome() {
  if (!tab.value.chromeText.trim()) {
    ElMessage.warning("请先粘贴 Chrome 内容");
    return;
  }
  loading.value = true;
  try {
    const parsed = await parseChromePaste(
      tab.value.chromeText,
      tab.value.payloadExtra,
    );
    await applyParsedRequest(parsed.request);
    const result = await executeRequest({
      method: parsed.request.method,
      url: parsed.request.url,
      headers: parsed.request.headers,
      body_type: parsed.request.body_type,
      body: parsed.request.body,
      follow_redirects: parsed.request.follow_redirects,
      project_id: props.projectId,
      request_id: parsed.request.id,
      request_name: parsed.request.name,
    });
    attachResponse(tab.value, result);
    emit("executed");
    if (result.error) {
      ElMessage.error(result.error);
    } else {
      ElMessage.success(`完成 ${result.status_code} · ${result.elapsed_ms}ms`);
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "发送失败");
  } finally {
    loading.value = false;
  }
}

async function syncFormToCurl() {
  if (!tab.value.draft) {
    return;
  }
  tab.value.curlText = await convertRequestToCurl(tab.value.draft);
}

async function syncCurlToForm() {
  try {
    const parsed = await convertCurlToRequest(tab.value.curlText);
    await applyParsedRequest({
      ...parsed,
      name: tab.value.draft?.name || parsed.name,
    });
    ElMessage.success("已从 Curl 同步到表单");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Curl 解析失败");
  }
}

function addHeader() {
  tab.value.draft?.headers.push({ key: "", value: "", enabled: true });
}

function removeHeader(index: number) {
  tab.value.draft?.headers.splice(index, 1);
}

async function handleUpdateCurrent() {
  saving.value = true;
  try {
    await updateExistingRequest({
      tab: tab.value,
      projectId: props.projectId,
      projectName: props.projectName,
      projectTree: props.projectTree,
    });
    ElMessage.success("已更新当前接口");
    emit("saved");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "更新失败");
  } finally {
    saving.value = false;
  }
}

async function openSaveDialog() {
  preparingSave.value = true;
  try {
    const draft = await prepareTabForSaveDialog(tab.value);
    if (!draft) {
      return;
    }
    saveDialogVisible.value = true;
  } finally {
    preparingSave.value = false;
  }
}

async function handleSave() {
  if (saving.value || preparingSave.value) {
    return;
  }
  if (!props.projectId || !props.projectName) {
    ElMessage.warning("请先在左侧选择或创建一个项目");
    return;
  }
  if (isUpdateSave.value) {
    await handleUpdateCurrent();
    return;
  }
  await openSaveDialog();
}

async function handleSaveConfirm(
  form: import("../composables/saveNewRequest").SaveFormValues,
) {
  saving.value = true;
  try {
    await saveNewRequest({
      tab: tab.value,
      form,
      projects: props.projects,
      currentProjectId: props.projectId,
      currentProjectName: props.projectName,
    });
    saveDialogVisible.value = false;
    ElMessage.success("已保存为新接口");
    emit("saved");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleSendForm() {
  if (!tab.value.draft || loading.value) {
    return;
  }
  loading.value = true;
  try {
    const result = await executeRequest({
      method: tab.value.draft.method,
      url: tab.value.draft.url,
      headers: tab.value.draft.headers,
      body_type: tab.value.draft.body_type,
      body: tab.value.draft.body,
      follow_redirects: tab.value.draft.follow_redirects,
      project_id: props.projectId,
      request_id: tab.value.draft.id,
      request_name: tab.value.draft.name,
    });
    attachResponse(tab.value, result);
    emit("executed");
    if (result.error) {
      ElMessage.error(result.error);
    } else {
      ElMessage.success(`完成 ${result.status_code} · ${result.elapsed_ms}ms`);
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "发送失败");
  } finally {
    loading.value = false;
  }
}

function handleKeydown(event: KeyboardEvent) {
  const isMod = event.ctrlKey || event.metaKey;
  if (!isMod) {
    return;
  }
  if (event.key.toLowerCase() === "s") {
    event.preventDefault();
    void handleSave();
    return;
  }
  if (event.key === "Enter") {
    event.preventDefault();
    if (tab.value.editMode === "chrome") {
      void handleSendChrome();
    } else {
      void handleSendForm();
    }
  }
}

watch(
  () => tab.value.editMode,
  async (mode) => {
    if (mode === "curl" && tab.value.draft) {
      await syncFormToCurl();
    }
  },
);

onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <section class="editor panel">
    <div class="editor-head">
      <el-radio-group v-model="tab.editMode" size="small" class="mode-switch">
        <el-radio-button value="chrome">Chrome 粘贴</el-radio-button>
        <el-radio-button value="form">表单模式</el-radio-button>
        <el-radio-button value="curl">Curl 模式</el-radio-button>
      </el-radio-group>
      <span class="shortcut-hint">{{ saveShortcutHint }}</span>
      <el-button :loading="saving || preparingSave" @click="handleSave">
        保存
      </el-button>
      <el-button
        type="primary"
        class="send-btn"
        :loading="loading"
        @click="
          tab.editMode === 'chrome' ? handleSendChrome() : handleSendForm()
        "
      >
        发送
      </el-button>
    </div>

    <div v-if="tab.editMode === 'chrome'" class="chrome-panel">
      <label class="field-label">Chrome 标头</label>
      <el-input
        v-model="tab.chromeText"
        type="textarea"
        :rows="12"
        placeholder="粘贴网络面板「标头」全文：请求网址 / 方法 / authorization / cookie ..."
        class="mono code-area"
      />
      <label class="field-label">GET 参数 或 POST JSON（可选）</label>
      <el-input
        v-model="tab.payloadExtra"
        type="textarea"
        :rows="5"
        placeholder='GET: a=1&b=2  或  POST: {"page":1}'
        class="mono code-area"
      />
      <div class="chrome-actions">
        <el-button plain @click="handleParseChrome">解析预览</el-button>
      </div>
      <div v-if="tab.parsedPreview" class="preview-bar">
        <el-tag>{{ tab.parsedPreview.method }}</el-tag>
        <span class="preview-url">{{ tab.parsedPreview.url }}</span>
      </div>
    </div>

    <div v-else-if="tab.editMode === 'form' && tab.draft" class="form-panel">
      <el-input
        v-model="tab.draft.name"
        placeholder="接口名称（保存时可再确认）"
        class="name-input"
      />
      <div class="url-row">
        <el-select v-model="tab.draft.method" class="method-select">
          <el-option label="GET" value="GET" />
          <el-option label="POST" value="POST" />
          <el-option label="PUT" value="PUT" />
          <el-option label="DELETE" value="DELETE" />
          <el-option label="PATCH" value="PATCH" />
        </el-select>
        <el-input
          v-model="tab.draft.url"
          placeholder="完整 URL，可省略 http://"
        />
      </div>
      <h3 class="section-title">Headers</h3>
      <div
        v-for="(header, index) in tab.draft.headers"
        :key="index"
        class="header-row"
      >
        <el-checkbox v-model="header.enabled" />
        <el-input v-model="header.key" placeholder="Key" />
        <el-input v-model="header.value" placeholder="Value" />
        <el-button link type="danger" @click="removeHeader(index)"
          >删</el-button
        >
      </div>
      <el-button size="small" plain @click="addHeader">添加 Header</el-button>
      <h3 class="section-title">Body</h3>
      <el-select v-model="tab.draft.body_type" class="body-type-select">
        <el-option label="无 Body" value="none" />
        <el-option label="JSON" value="json" />
        <el-option label="Raw" value="raw" />
      </el-select>
      <el-input
        v-if="tab.draft.body_type !== 'none'"
        v-model="tab.draft.body"
        type="textarea"
        :rows="8"
        class="mono code-area"
      />
    </div>

    <div v-else-if="tab.editMode === 'curl'" class="curl-panel">
      <div class="curl-actions">
        <el-button size="small" plain @click="syncCurlToForm"
          >同步到表单</el-button
        >
      </div>
      <el-input
        v-model="tab.curlText"
        type="textarea"
        :rows="18"
        class="mono code-area"
      />
    </div>

    <div v-else class="empty">从左侧打开接口，或切换到 Chrome / Curl 模式</div>

    <SaveRequestDialog
      v-model="saveDialogVisible"
      :suggested-name="suggestedSaveName"
      :default-project-id="projectId"
      :default-project-name="projectName"
      :default-folder-id="defaultSaveFolderId"
      :projects="projects"
      :project-tree="projectTree"
      @confirm="handleSaveConfirm"
    />
  </section>
</template>

<style scoped>
.panel {
  background: var(--aw-bg-panel);
  border: 1px solid var(--aw-border);
  border-radius: var(--aw-radius);
  box-shadow: var(--aw-shadow);
}

.editor {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow: auto;
}

.editor-head {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--aw-bg-panel);
  padding-bottom: 8px;
}

.mode-switch {
  margin-right: auto;
}

.shortcut-hint {
  font-size: 12px;
  color: var(--aw-text-muted);
  white-space: nowrap;
}

.send-btn {
  --el-button-bg-color: var(--aw-send-deep);
  --el-button-border-color: var(--aw-send-deep);
  --el-button-hover-bg-color: var(--aw-send);
  --el-button-hover-border-color: var(--aw-send);
}

.field-label {
  display: block;
  margin: 8px 0 6px;
  font-size: 12px;
  color: var(--aw-text-muted);
  font-weight: 600;
}

.chrome-actions {
  margin-top: 10px;
}

.preview-bar {
  margin-top: 10px;
  padding: 10px 12px;
  background: var(--aw-bg-input);
  border-radius: 8px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.preview-url {
  font-size: 12px;
  color: var(--aw-text-muted);
  word-break: break-all;
}

.empty {
  color: var(--aw-text-muted);
  padding: 40px 0;
  text-align: center;
}

.name-input {
  margin-bottom: 10px;
}

.section-title {
  margin: 14px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--aw-text-muted);
}

.url-row,
.header-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.method-select {
  width: 110px;
  flex-shrink: 0;
}

.body-type-select {
  width: 160px;
  margin-bottom: 8px;
}

.header-row .el-input {
  flex: 1;
}

.code-area :deep(textarea) {
  font-family: var(--aw-mono);
  font-size: 13px;
  line-height: 1.55;
}

.curl-panel {
  margin-top: 4px;
}

.curl-actions {
  margin-bottom: 8px;
}
</style>
