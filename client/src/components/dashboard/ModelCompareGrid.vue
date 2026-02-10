<template>
  <section class="space-y-4">
    <div class="flex flex-wrap items-center gap-2">
      <button class="ui-btn" type="button" @click="openPicker">Upload once</button>
      <button class="ui-btn-secondary" type="button" :disabled="!videoSrc" @click="clearVideo">Delete</button>
      <span class="text-xs text-slate-600" v-if="fileName">Loaded: {{ fileName }}</span>
      <span class="text-xs text-slate-500" v-else>One upload feeds both A/B panels</span>
      <input ref="fileInput" type="file" accept="video/*" class="hidden" @change="onFileChange" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch">
      <ModelPane :mode="mode" slotName="A" title="Model A (Baseline)" :video-src="videoSrc" />
      <ModelPane :mode="mode" slotName="B" title="Model B (Custom)" :video-src="videoSrc" />
    </div>

    <MetricsTable />
  </section>
</template>

<script setup>
import { ref, onBeforeUnmount } from "vue";
import ModelPane from "./ModelPane.vue";
import MetricsTable from "./MetricsTable.vue";

defineProps({
  mode: { type: String, required: true },
});

const fileInput = ref(null);
const videoSrc = ref("");
const fileName = ref("");
let objectUrl = null;

function openPicker() {
  fileInput.value?.click();
}

function onFileChange(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(file);
  videoSrc.value = objectUrl;
  fileName.value = file.name;
  e.target.value = ""; // allow re-upload of same file name
}

function clearVideo() {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = null;
  videoSrc.value = "";
  fileName.value = "";
}

onBeforeUnmount(() => {
  clearVideo();
});
</script>
