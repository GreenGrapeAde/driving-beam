<template>
  <section class="space-y-4 chat-safe">
    <div class="flex flex-wrap items-center gap-2">
      <button 
        class="ui-btn"
        type="button"
        v-if="mode === 'playback'"
        @click="openPicker">
          Upload once
      </button>
      <button 
        class="ui-btn-secondary"
        type="button"
        v-if="mode === 'playback' && videoSrc"
        @click="clearVideo">
          Delete
      </button>
      <span 
        class="text-s 
        text-slate-600" 
        v-if="fileName">
          Loaded: {{ fileName }}
      </span>
      <span
        class="text-s
        text-slate-500"
        v-else
        v-if="mode === 'playback'">
          One upload feeds both A/B panels
        </span>
      <input ref="fileInput" type="file" accept="video/*" class="hidden" @change="onFileChange" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch">
      <ModelPane
        :mode="mode"
        slotName="A"
        title="Model A (Baseline)"
        :video-src="videoSrc"
        :play-token="playToken"
        :pause-token="pauseToken"
        :volume="volume"
        :seek-token="seekToken"
        :seek-fraction="seekFraction"
        @play="handlePlay"
        @pause="handlePause"
        @volume-change="handleVolume"
        @seek="handleSeek"
      />
      <ModelPane
        :mode="mode"
        slotName="B"
        title="Model B (Custom)"
        :video-src="videoSrc"
        :play-token="playToken"
        :pause-token="pauseToken"
        :volume="volume"
        :seek-token="seekToken"
        :seek-fraction="seekFraction"
        @play="handlePlay"
        @pause="handlePause"
        @volume-change="handleVolume"
        @seek="handleSeek"
      />
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
const playToken = ref(0);
const pauseToken = ref(0);
const volume = ref(0.5);
const seekToken = ref(0);
const seekFraction = ref(0);
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
  seekFraction.value = 0;
  e.target.value = ""; // allow re-upload of same file name
  // autoplay 방지: 사용자가 play 눌러야 시작
}

function clearVideo() {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = null;
  videoSrc.value = "";
  fileName.value = "";
  playToken.value = 0;
  pauseToken.value = 0;
  seekToken.value = 0;
  seekFraction.value = 0;
}

function handlePlay() {
  playToken.value += 1;
}

function handlePause() {
  pauseToken.value += 1;
}

function handleVolume(val) {
  volume.value = val;
}

function handleSeek(fraction) {
  seekFraction.value = fraction;
  seekToken.value += 1;
}

onBeforeUnmount(() => {
  clearVideo();
});
</script>
