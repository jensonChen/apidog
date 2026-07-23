<script setup lang="ts">
const BRAND_ICON_SRC = "/favicon.png";

defineProps<{
  desktopShell: boolean;
}>();
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

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.brand-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid var(--aw-border);
  background: #1a2430;
  pointer-events: none;
}

.brand-name {
  font-size: 14px;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: var(--aw-text);
}
</style>
