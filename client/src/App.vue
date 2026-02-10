<template>
  <div class="app-shell">
    <Sidebar :mode="mode" @update:mode="mode = $event" />

    <main class="content">
      <DashboardHeader :mode="mode" />
      <ModelCompareGrid :mode="mode" />
    </main>
  </div>
</template>

<script setup>
import { ref } from "vue";
import Sidebar from "./components/layout/Sidebar.vue";
import DashboardHeader from "./components/layout/DashboardHeader.vue";
import ModelCompareGrid from "./components/dashboard/ModelCompareGrid.vue";

const mode = ref("live"); // 'live' | 'playback'
</script>
