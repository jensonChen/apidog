<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { TreeNode } from "../types";
import {
  ROOT_FOLDER_VALUE,
  collectFolderOptions,
  type FolderOption,
} from "../composables/workspaceContext";
import { fetchProject } from "../api/client";

const visible = defineModel<boolean>({ required: true });

const props = defineProps<{
  suggestedName: string;
  defaultProjectId: string;
  defaultProjectName: string;
  defaultFolderId: string | null;
  projects: Array<{ id: string; name: string; file: string }>;
  projectTree: TreeNode[];
}>();

const emit = defineEmits<{
  confirm: [
    payload: {
      requestName: string;
      projectName: string;
      folderName: string;
      folderId: string | null;
      isNewProject: boolean;
      isNewFolder: boolean;
    },
  ];
}>();

const requestName = ref("");
const projectName = ref("");
const folderPick = ref<string>(ROOT_FOLDER_VALUE);
const activeTree = ref<TreeNode[]>([]);
const loadingFolders = ref(false);

const folderOptions = computed<FolderOption[]>(() =>
  collectFolderOptions(activeTree.value),
);

const isNewProject = computed(() => {
  const trimmed = projectName.value.trim();
  if (!trimmed) {
    return false;
  }
  return !props.projects.some((item) => item.name === trimmed);
});

const isNewFolder = computed(() => {
  const trimmed = folderPick.value.trim();
  if (!trimmed || trimmed === ROOT_FOLDER_VALUE) {
    return false;
  }
  return !folderOptions.value.some((item) => item.id === trimmed);
});

async function loadProjectTreeByName(name: string) {
  const trimmed = name.trim();
  if (!trimmed) {
    activeTree.value = [];
    return;
  }
  const existing = props.projects.find((item) => item.name === trimmed);
  if (!existing) {
    activeTree.value = [];
    folderPick.value = ROOT_FOLDER_VALUE;
    return;
  }
  loadingFolders.value = true;
  try {
    const project = await fetchProject(existing.id);
    activeTree.value = project.tree;
    const stillValid =
      folderPick.value === ROOT_FOLDER_VALUE ||
      collectFolderOptions(project.tree).some(
        (item) => item.id === folderPick.value,
      );
    if (!stillValid) {
      folderPick.value = ROOT_FOLDER_VALUE;
    }
  } finally {
    loadingFolders.value = false;
  }
}

function resetForm() {
  requestName.value = props.suggestedName;
  projectName.value = props.defaultProjectName;
  folderPick.value = props.defaultFolderId ?? ROOT_FOLDER_VALUE;
  activeTree.value = props.projectTree;
}

function handleOpen() {
  resetForm();
}

watch(
  () => projectName.value,
  (name) => {
    void loadProjectTreeByName(name);
  },
);

watch(visible, (isOpen) => {
  if (isOpen) {
    handleOpen();
  }
});

function handleConfirm() {
  if (!requestName.value.trim()) {
    return;
  }
  const pick = folderPick.value.trim();
  const creatingFolder = isNewFolder.value;
  emit("confirm", {
    requestName: requestName.value.trim(),
    projectName: projectName.value.trim(),
    folderName: creatingFolder ? pick : "",
    folderId: creatingFolder || pick === ROOT_FOLDER_VALUE ? null : pick,
    isNewProject: isNewProject.value,
    isNewFolder: creatingFolder,
  });
}
</script>

<template>
  <el-dialog
    v-model="visible"
    title="保存为新接口"
    width="520px"
    :close-on-press-escape="true"
    destroy-on-close
    class="save-request-dialog"
    @open="handleOpen"
  >
    <p class="dialog-hint">
      当前是新请求，将新增一条接口。若从左侧打开已有接口再保存，会直接更新原记录。
    </p>

    <label class="field-label">接口名称 <span class="required">*</span></label>
    <el-input
      v-model="requestName"
      placeholder="例如 192.168.1.10 userList · env=test"
      clearable
    />

    <label class="field-label">所属项目</label>
    <el-select
      v-model="projectName"
      filterable
      allow-create
      default-first-option
      placeholder="选择或输入新项目名称"
      style="width: 100%"
    >
      <el-option
        v-for="item in projects"
        :key="item.id"
        :label="item.name"
        :value="item.name"
      />
    </el-select>
    <p v-if="isNewProject" class="field-tip">
      将创建新项目「{{ projectName }}」
    </p>

    <label class="field-label">所属模块</label>
    <el-select
      v-model="folderPick"
      filterable
      allow-create
      default-first-option
      :loading="loadingFolders"
      placeholder="选择已有模块，或直接输入新模块名"
      style="width: 100%"
    >
      <el-option label="根目录（不放入模块）" :value="ROOT_FOLDER_VALUE" />
      <el-option
        v-for="item in folderOptions"
        :key="item.id"
        :label="item.label"
        :value="item.id"
      />
    </el-select>
    <p v-if="isNewFolder" class="field-tip">
      将创建新模块「{{ folderPick.trim() }}」
    </p>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button
        type="primary"
        :disabled="!requestName.trim() || !projectName.trim()"
        @click="handleConfirm"
      >
        保存为新接口
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--aw-text-muted);
  line-height: 1.5;
}

.field-label {
  display: block;
  margin: 12px 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--aw-text-muted);
}

.field-label:first-of-type {
  margin-top: 0;
}

.required {
  color: var(--aw-danger);
}

.field-tip {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--aw-accent);
}
</style>

<style>
.save-request-dialog .el-dialog {
  background: var(--aw-bg-panel);
}

.save-request-dialog .el-dialog__title {
  color: var(--aw-text);
}
</style>
