<template>
  <div class="app-shell">
    <Sidebar :mode="mode" @update:mode="mode = $event" />

    <main class="content">
      <DashboardHeader :mode="mode" />
      <ModelCompareGrid :mode="mode" />
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
            <div class="chat-subtitle">Adaptive beam tester chat</div>
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
import { ref } from "vue";
import Sidebar from "./components/layout/Sidebar.vue";
import DashboardHeader from "./components/layout/DashboardHeader.vue";
import ModelCompareGrid from "./components/dashboard/ModelCompareGrid.vue";

const mode = ref("live"); // 'live' | 'playback'
const chatOpen = ref(false);

function toggleChat() {
  chatOpen.value = !chatOpen.value;
}
</script>
