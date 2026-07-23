<script setup lang="ts">
import type { WorkbenchTab } from "../types";

defineProps<{
  tabs: WorkbenchTab[];
  activeTabId: string;
}>();

const emit = defineEmits<{
  select: [tabId: string];
  add: [];
  close: [tabId: string];
  closeAll: [];
}>();
</script>

<template>
  <div class="tab-bar">
    <div class="tab-list">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-item"
        :class="{ active: tab.id === activeTabId }"
        @click="emit('select', tab.id)"
      >
        <span class="tab-title">{{ tab.title }}</span>
        <span
          v-if="tab.response?.status_code"
          class="tab-status"
          :class="{ ok: tab.response.ok, fail: tab.response.error }"
        >
          {{ tab.response.error ? "×" : tab.response.status_code }}
        </span>
        <span
          v-if="tabs.length > 1"
          class="tab-close"
          @click.stop="emit('close', tab.id)"
        >
          ×
        </span>
      </button>
      <button class="tab-add" title="新建标签" @click="emit('add')">+</button>
    </div>
    <button v-if="tabs.length > 1" class="close-all" @click="emit('closeAll')">
      全部关闭
    </button>
  </div>
</template>

<style scoped>
.tab-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  min-height: 38px;
}

.tab-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  overflow-x: auto;
  padding-bottom: 2px;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 200px;
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid var(--aw-border);
  background: var(--aw-bg-input);
  color: var(--aw-text-muted);
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}

.tab-item:hover {
  border-color: color-mix(in srgb, var(--aw-accent) 40%, var(--aw-border));
  color: var(--aw-text);
}

.tab-item.active {
  border-color: var(--aw-accent);
  background: var(--aw-accent-soft);
  color: var(--aw-text);
}

.tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-status {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--aw-text) 8%, transparent);
}

.tab-status.ok {
  color: var(--aw-send);
}

.tab-status.fail {
  color: var(--aw-danger);
}

.tab-close {
  opacity: 0.6;
  font-size: 14px;
  line-height: 1;
}

.tab-close:hover {
  opacity: 1;
  color: var(--aw-danger);
}

.tab-add {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px dashed var(--aw-border);
  background: transparent;
  color: var(--aw-text-muted);
  cursor: pointer;
  flex-shrink: 0;
}

.tab-add:hover {
  border-color: var(--aw-accent);
  color: var(--aw-accent);
}

.close-all {
  border: none;
  background: transparent;
  color: var(--aw-text-muted);
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
  padding: 6px 8px;
}

.close-all:hover {
  color: var(--aw-danger);
}
</style>
