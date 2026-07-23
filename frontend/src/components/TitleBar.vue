<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

const BRAND_ICON_SRC = "/favicon.png";
const WINDOW_API_READY_EVENT = "pywebviewready";

const props = defineProps<{
  desktopShell: boolean;
}>();

const canControlWindow = ref(false);

function refreshWindowApiReady() {
  const bridge = (window as Window & { pywebview?: { api?: unknown } })
    .pywebview;
  canControlWindow.value = Boolean(props.desktopShell && bridge?.api);
}

async function callWindowApi(
  methodName: "minimize" | "toggle_maximize" | "close",
) {
  const api = (
    window as Window & {
      pywebview?: {
        api?: {
          minimize: () => Promise<void>;
          toggle_maximize: () => Promise<void>;
          close: () => Promise<void>;
        };
      };
    }
  ).pywebview?.api;
  if (!api) {
    return;
  }
  await api[methodName]();
}

function handleMinimize() {
  void callWindowApi("minimize");
}

function handleToggleMaximize() {
  void callWindowApi("toggle_maximize");
}

function handleClose() {
  void callWindowApi("close");
}

onMounted(() => {
  refreshWindowApiReady();
  window.addEventListener(WINDOW_API_READY_EVENT, refreshWindowApiReady);
});

onUnmounted(() => {
  window.removeEventListener(WINDOW_API_READY_EVENT, refreshWindowApiReady);
});
</script>

<template>
  <header class="title-bar" :class="{ desktop: desktopShell }">
    <div class="drag-region">
      <div class="brand" title="ApiDog">
        <img
          class="brand-mark"
          :src="BRAND_ICON_SRC"
          alt=""
          width="28"
          height="28"
        />
        <span class="brand-name">ApiDog</span>
      </div>
      <slot />
    </div>
    <div v-if="canControlWindow" class="window-controls">
      <button
        type="button"
        class="win-btn"
        title="最小化"
        @click="handleMinimize"
      >
        <span aria-hidden="true">─</span>
      </button>
      <button
        type="button"
        class="win-btn"
        title="最大化"
        @click="handleToggleMaximize"
      >
        <span aria-hidden="true">□</span>
      </button>
      <button
        type="button"
        class="win-btn close"
        title="关闭"
        @click="handleClose"
      >
        <span aria-hidden="true">×</span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.title-bar {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  height: 40px;
  border-bottom: 1px solid var(--aw-border);
  background: color-mix(in srgb, var(--aw-bg-panel) 92%, #0b121a);
  user-select: none;
}

.title-bar.desktop {
  height: 42px;
}

.drag-region {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
}

.title-bar.desktop .drag-region {
  -webkit-app-region: drag;
  app-region: drag;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.brand-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid var(--aw-border);
  background: #1a2430;
}

.brand-name {
  font-size: 14px;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: var(--aw-text);
}

.window-controls {
  display: flex;
  flex-shrink: 0;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.win-btn {
  width: 46px;
  height: 100%;
  border: 0;
  background: transparent;
  color: var(--aw-text-muted);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
}

.win-btn:hover {
  background: color-mix(in srgb, var(--aw-text) 10%, transparent);
  color: var(--aw-text);
}

.win-btn.close:hover {
  background: #e81123;
  color: #fff;
}
</style>
