<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import type { ExecuteResponse } from "../types";

const props = defineProps<{
  result: ExecuteResponse | null;
  tabTitle?: string;
}>();

const dialogVisible = ref(false);

const formattedBody = computed(() => {
  if (!props.result) {
    return "";
  }
  if (props.result.body_json !== null) {
    return JSON.stringify(props.result.body_json, null, 2);
  }
  return props.result.body_text;
});

const statusTagType = computed(() => {
  if (!props.result || props.result.error) {
    return "danger";
  }
  if (props.result.ok) {
    return "success";
  }
  return "warning";
});

function openResponseDialog() {
  if (!props.result || !formattedBody.value) {
    return;
  }
  dialogVisible.value = true;
}

async function copyBody() {
  if (!formattedBody.value) {
    ElMessage.warning("没有可复制的内容");
    return;
  }
  try {
    await navigator.clipboard.writeText(formattedBody.value);
    ElMessage.success("已复制响应内容");
  } catch {
    ElMessage.error("复制失败，请手动选择复制");
  }
}
</script>

<template>
  <section class="response panel">
    <div class="response-head">
      <div class="head-left">
        <h2>响应结果</h2>
        <span v-if="tabTitle" class="tab-ref">{{ tabTitle }}</span>
      </div>
      <div v-if="result" class="meta">
        <el-tag :type="statusTagType">
          {{ result.error ? "失败" : result.status_code }}
        </el-tag>
        <span v-if="result.parsed_method">{{ result.parsed_method }}</span>
        <span>{{ result.elapsed_ms }} ms</span>
        <el-button size="small" plain @click="copyBody">复制</el-button>
        <el-button
          size="small"
          type="primary"
          plain
          @click="dialogVisible = true"
        >
          大窗查看
        </el-button>
      </div>
    </div>

    <div v-if="!result" class="empty">暂无响应</div>
    <template v-else>
      <p v-if="result.resolved_url" class="url-line">
        {{ result.resolved_url }}
      </p>
      <p v-if="result.error" class="error-line">{{ result.error }}</p>
      <div
        class="body-wrap"
        title="双击放大查看"
        @dblclick="openResponseDialog"
      >
        <pre class="body-pre">{{ formattedBody }}</pre>
      </div>
    </template>

    <el-dialog
      v-model="dialogVisible"
      :title="`响应详情 · ${tabTitle || '当前标签'}`"
      width="86%"
      top="4vh"
      class="response-dialog"
      destroy-on-close
      :close-on-press-escape="true"
      @close="dialogVisible = false"
    >
      <div class="dialog-meta">
        <el-tag :type="statusTagType">
          {{ result?.error ? "失败" : result?.status_code }}
        </el-tag>
        <span>{{ result?.elapsed_ms }} ms</span>
        <span class="dialog-url">{{ result?.resolved_url }}</span>
        <el-button size="small" plain @click="copyBody">复制全部</el-button>
      </div>
      <pre class="dialog-pre">{{ formattedBody }}</pre>
    </el-dialog>
  </section>
</template>

<style scoped>
.panel {
  background: var(--aw-bg-panel);
  border: 1px solid var(--aw-border);
  border-radius: var(--aw-radius);
  box-shadow: var(--aw-shadow);
}

.response {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
  padding: 14px 16px;
}

.response-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
  flex-shrink: 0;
}

.head-left {
  min-width: 0;
}

.response-head h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--aw-text-muted);
}

.tab-ref {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--aw-accent);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 280px;
}

.meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  color: var(--aw-text-muted);
  font-size: 12px;
}

.empty {
  color: var(--aw-text-muted);
  padding: 40px 0;
  text-align: center;
  font-size: 13px;
}

.url-line {
  margin: 0 0 8px;
  font-size: 11px;
  color: var(--aw-text-muted);
  word-break: break-all;
  flex-shrink: 0;
}

.error-line {
  margin: 0 0 8px;
  color: var(--aw-danger);
  font-size: 13px;
  flex-shrink: 0;
}

.body-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: var(--aw-bg-input);
  border: 1px solid var(--aw-border);
  border-radius: 8px;
  cursor: pointer;
}

.body-pre {
  margin: 0;
  padding: 12px;
  font-family: var(--aw-mono);
  font-size: 12px;
  line-height: 1.55;
  color: var(--aw-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.dialog-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  color: var(--aw-text-muted);
  font-size: 12px;
}

.dialog-url {
  flex: 1;
  min-width: 200px;
  word-break: break-all;
}

.dialog-pre {
  margin: 0;
  max-height: 72vh;
  overflow: auto;
  padding: 14px;
  background: var(--aw-bg-input);
  border-radius: 8px;
  font-family: var(--aw-mono);
  font-size: 13px;
  line-height: 1.55;
  color: var(--aw-text);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>

<style>
.response-dialog .el-dialog {
  background: var(--aw-bg-panel);
}

.response-dialog .el-dialog__title {
  color: var(--aw-text);
}
</style>
