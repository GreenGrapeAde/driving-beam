<template>
  <section class="space-y-4 chat-safe">
    <UploadOnceBar
      :enabled="mode === 'playback'"
      helper="One upload feeds both A/B panels"
      @uploaded="onUploaded"
      @cleared="clearVideo"
    />

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
import UploadOnceBar from "./UploadOnceBar.vue";

defineProps({
  mode: { type: String, required: true },
});

const videoSrc = ref("");
const playToken = ref(0);
const pauseToken = ref(0);
const volume = ref(0.5);
const seekToken = ref(0);
const seekFraction = ref(0);

function onUploaded(payload) {
  videoSrc.value = payload.src;
  seekFraction.value = 0;
}

function clearVideo() {
  videoSrc.value = "";
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
