<script setup lang="ts">
import { ref } from "vue";
import type { HistoryItem } from "../types";

defineProps<{
  items: HistoryItem[];
}>();

const expanded = ref<string[]>([]);

function formatTime(timestamp: string): string {
  if (!timestamp) {
    return "";
  }
  return timestamp.replace("T", " ").slice(0, 19);
}
</script>

<template>
  <aside class="history-panel panel">
    <el-collapse v-model="expanded">
      <el-collapse-item name="history">
        <template #title>
          <span class="history-title">最近请求</span>
          <span class="history-count">{{ items.length }}</span>
        </template>
        <div v-if="!items.length" class="empty">暂无历史记录</div>
        <button
          v-for="item in items"
          :key="item.timestamp + (item.request_id || '')"
          class="history-item"
          type="button"
        >
          <span class="name">{{ item.request_name || item.method }}</span>
          <span class="status">{{ item.status_code ?? "失败" }}</span>
          <span class="time">{{ item.elapsed_ms }} ms</span>
          <span class="stamp">{{ formatTime(item.timestamp) }}</span>
        </button>
      </el-collapse-item>
    </el-collapse>
  </aside>
</template>

<style scoped>
.panel {
  background: var(--aw-bg-panel);
  border: 1px solid var(--aw-border);
  border-radius: var(--aw-radius);
  box-shadow: var(--aw-shadow);
}

.history-panel {
  flex-shrink: 0;
}

.history-panel :deep(.el-collapse) {
  border: none;
}

.history-panel :deep(.el-collapse-item__header) {
  background: transparent;
  border: none;
  color: var(--aw-text);
  height: 42px;
  padding: 0 14px;
}

.history-panel :deep(.el-collapse-item__wrap) {
  background: transparent;
  border: none;
}

.history-panel :deep(.el-collapse-item__content) {
  padding: 0 10px 12px;
}

.history-title {
  font-size: 13px;
  font-weight: 600;
}

.history-count {
  margin-left: 8px;
  font-size: 11px;
  color: var(--aw-text-muted);
  background: var(--aw-bg-input);
  padding: 1px 7px;
  border-radius: 10px;
}

.empty {
  color: var(--aw-text-muted);
  font-size: 12px;
  padding: 8px 4px;
}

.history-item {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2px 8px;
  text-align: left;
  padding: 8px 6px;
  border: none;
  border-top: 1px solid var(--aw-border);
  background: transparent;
  color: var(--aw-text);
  cursor: default;
  font-size: 12px;
}

.history-item:first-of-type {
  border-top: none;
}

.name {
  grid-column: 1 / -1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status {
  color: var(--aw-send);
}

.time {
  color: var(--aw-text-muted);
}

.stamp {
  grid-column: 1 / -1;
  color: var(--aw-text-muted);
  font-size: 11px;
}
</style>
