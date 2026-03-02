<template>
  <div class="app-shell">
    <Sidebar :mode="mode" @update:mode="mode = $event" @reset=reload />

  <main class="content">
    <div class="content-body">         <!-- 이 안에서만 스크롤 -->
      <DashboardHeader :mode="mode" />   <!-- 헤더: flex item, 고정 높이 -->
      <div style="margin: -10px -28px 20px -28px; border-bottom: 1px solid rgba(15, 23, 42, 0.08);" /> <!-- 구분선 -->
      <LiveView v-if="mode === 'live'" :mode="mode" />
      <PlaybackView v-else-if="mode === 'playback'" :mode="mode" />
      <ManualCrop :mode="mode" ref="manualCropRef" v-else />
    </div>
  </main>

    <!-- Chat widget layout with toggle -->
    <div class="chat-shell">
      <button class="chat-fab" type="button" @click="toggleChat">
        {{ chatOpen ? "×" : "Chat" }}
      </button>
      <aside class="chat-panel" v-show="chatOpen">
        <div class="chat-panel__header">
          <div>
            <div class="chat-title">Assistant</div>
            <div class="chat-subtitle">How can I help you?</div>
          </div>
          <span class="chat-status">∙ online</span>
        </div>
        <div class="chat-panel__body">
          <div class="chat-placeholder">Chat content will appear here.</div>
        </div>
        <div class="chat-panel__footer">
          <div class="chat-input-placeholder">Type a message…</div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import Sidebar from "./components/layout/Sidebar.vue";
import DashboardHeader from "./components/layout/DashboardHeader.vue";
import ManualCrop from "./components/dashboard/ManualCrop.vue";
import LiveView from "./components/dashboard/LiveView.vue";
import PlaybackView from "./components/dashboard/PlaybackView.vue";

const mode = ref("live"); // 'live' | 'playback' | 'manual'
const chatOpen = ref(false);

function toggleChat() {
  chatOpen.value = !chatOpen.value;
}

function reload() {
  window.location.reload();
}

const manualCropRef = ref(null);

watch(mode, (newMode, oldMode) => {
  if (oldMode === 'manual' && newMode !== 'manual') {
    manualCropRef.value?.onCleared();
  }
});

</script>
