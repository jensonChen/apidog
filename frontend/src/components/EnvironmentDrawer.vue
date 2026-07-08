<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import type { EnvironmentConfig } from "../types";
import { saveEnvironment } from "../api/client";

const props = defineProps<{
  environments: EnvironmentConfig[];
  activeEnvironmentId: string;
}>();

const emit = defineEmits<{
  updated: [];
}>();

const visible = defineModel<boolean>({ default: false });
const draft = ref<EnvironmentConfig | null>(null);

const variableRows = computed(() => {
  if (!draft.value) {
    return [];
  }
  return Object.entries(draft.value.variables).map(([key, value]) => ({
    key,
    value,
  }));
});

watch(
  () => [props.activeEnvironmentId, props.environments, visible.value] as const,
  () => {
    if (!visible.value) {
      return;
    }
    const current = props.environments.find(
      (item) => item.id === props.activeEnvironmentId,
    );
    draft.value = current ? JSON.parse(JSON.stringify(current)) : null;
  },
  { immediate: true },
);

function addVariable() {
  if (!draft.value) {
    return;
  }
  const key = `var_${Object.keys(draft.value.variables).length + 1}`;
  draft.value.variables[key] = "";
}

function removeVariable(key: string) {
  if (!draft.value) {
    return;
  }
  delete draft.value.variables[key];
  draft.value = { ...draft.value, variables: { ...draft.value.variables } };
}

function updateVariableKey(oldKey: string, newKey: string) {
  if (!draft.value || !newKey.trim() || oldKey === newKey) {
    return;
  }
  const value = draft.value.variables[oldKey];
  delete draft.value.variables[oldKey];
  draft.value.variables[newKey.trim()] = value;
}

async function handleSave() {
  if (!draft.value) {
    return;
  }
  await saveEnvironment(draft.value);
  ElMessage.success("环境变量已保存");
  emit("updated");
}
</script>

<template>
  <el-drawer v-model="visible" title="环境变量" size="420px">
    <template v-if="draft">
      <p class="hint">
        URL 中可使用 <code v-pre>{{ baseUrl }}</code> 形式引用变量
      </p>
      <div v-for="row in variableRows" :key="row.key" class="var-row">
        <el-input
          :model-value="row.key"
          placeholder="变量名"
          @change="(value: string) => updateVariableKey(row.key, value)"
        />
        <el-input v-model="draft.variables[row.key]" placeholder="变量值" />
        <el-button link type="danger" @click="removeVariable(row.key)"
          >删</el-button
        >
      </div>
      <el-button size="small" @click="addVariable">添加变量</el-button>
      <div class="footer">
        <el-button type="primary" @click="handleSave">保存环境</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.hint {
  color: var(--aw-text-muted);
  font-size: 13px;
}

.hint code {
  color: var(--aw-accent);
}

.var-row {
  display: flex;
  gap: 8px;
  margin: 8px 0;
}

.var-row .el-input {
  flex: 1;
}

.footer {
  margin-top: 20px;
}
</style>
