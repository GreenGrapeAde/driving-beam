<template>
  <div class="panel">
    <div class="flex items-center justify-between gap-3 mb-3">
      <div>
        <h2 class="text-lg font-bold">{{ title }}</h2>
        <p class="text-xs text-slate-600">
          {{ mode === "live" ? "Live stream + WebSocket overlay" : "Playback file + overlay" }}
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button class="ui-btn" @click="onLoadModel">
          Load Model
        </button>
        <button class="ui-btn-secondary" @click="onTestPing">
          Test
        </button>
      </div>
    </div>

    <div class="flex flex-col gap-4">
      <VideoWithOverlay
        :slotName="slotName"
        :video-src="videoSrc"
        :play-token="playToken"
        :pause-token="pauseToken"
        :volume="volume"
        :seek-token="seekToken"
        :seek-fraction="seekFraction"
        :mode="mode"
        @play="$emit('play')"
        @pause="$emit('pause')"
        @volume-change="$emit('volume-change', $event)"
        @seek="$emit('seek', $event)"
      />
      <BeamPanel :slotName="slotName" />
    </div>
  </div>
</template>

<script setup>
import VideoWithOverlay from "./VideoWithOverlay.vue";
import BeamPanel from "./BeamPanel.vue";

const props = defineProps({
  mode: { type: String, required: true },
  slotName: { type: String, required: true }, // 'A' | 'B'
  title: { type: String, required: true },
  videoSrc: { type: String, default: "" },
  playToken: { type: Number, default: 0 },
  pauseToken: { type: Number, default: 0 },
  volume: { type: Number, default: 0.5 },
  seekToken: { type: Number, default: 0 },
  seekFraction: { type: Number, default: 0 },
});

const emit = defineEmits(["play", "pause", "volume-change", "seek"]);

function onLoadModel() {
  alert(`[${props.slotName}] Load Model (TODO)`);
}

function onTestPing() {
  alert(`[${props.slotName}] Test (TODO)`);
}
</script>
