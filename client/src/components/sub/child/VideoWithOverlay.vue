<template>
  <div class="card h-full flex flex-col">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm font-semibold">{{ mode === 'live' ? 'Live Stream + Overlay' : mode === 'playback' ? 'Playback + Overlay' : 'Manual Crop Preview' }}</div>
      <div class="text-xs text-slate-500">Slot {{ slotName }}</div>
    </div>

    <div class="video-wrap" style="height: 420px;">
      <video
        v-if="videoSrc"
        ref="videoEl"
        class="video-el"
        :src="videoSrc"
        playsinline
        @play="isPlaying = true"
        @pause="isPlaying = false"
        @timeupdate="onTimeUpdate"
        @loadedmetadata="onLoadedMetadata"
      />

      <div v-else class="video-placeholder">
        <div class="text-xs text-slate-500 mt-1">
          Upload once above to play in both panels
        </div>
      </div>

      <canvas ref="overlay" class="overlay-canvas"></canvas>
    </div>
    <!-- playback 모드일 때만 동영상 기능 보이기 -->
    <div 
      v-if="mode === 'playback' || mode === 'manual'"
    >
      <div class="mt-3 flex items-center flex-wrap gap-3 text-xs text-slate-600">
        <div class="flex items-center gap-2">
          <button class="ui-btn-secondary icon-btn" type="button" :disabled="!videoSrc" @click="emitPlay">
            <span aria-label="Play">&#9658;</span>
          </button>
          <button class="ui-btn-secondary icon-btn" type="button" :disabled="!videoSrc" @click="emitPause">
            <span aria-label="Pause">&#10074;&#10074;</span>
          </button>
        </div>

        <div class="flex items-center gap-2 min-w-[200px]">
          <span>Seek</span>
          <input
            class="progress-slider"
            type="range"
            min="0"
            max="1"
            step="0.001"
            :value="progress"
            @input="onSeekInput"
            :disabled="!videoSrc || duration === 0"
          />
          <span class="w-12 text-right">{{ formatTime(currentTime) }}</span>
        </div>

        <div class="flex items-center gap-2">
          <span>Volume</span>
          <input
            class="volume-slider"
            type="range"
            min="0"
            max="1"
            step="0.01"
            :value="volume"
            @input="onVolumeChange"
            :disabled="!videoSrc"
          />
          <span class="w-8 text-right">{{ Math.round(volume * 100) }}%</span>
        </div>

        <span v-if="videoSrc">{{ isPlaying ? "Playing" : "Paused" }}</span>
        <span v-else>Overlay: bbox / id / center (WS JSON) -> canvas draw (TODO)</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";

const props = defineProps({
  mode: { type: String, required: true },
  slotName: { type: String, required: true },
  videoSrc: { type: String, default: "" },
  playToken: { type: Number, default: 0 },
  pauseToken: { type: Number, default: 0 },
  volume: { type: Number, default: 0.5 },
  seekToken: { type: Number, default: 0 },
  seekFraction: { type: Number, default: 0 },
});

const emit = defineEmits(["play", "pause", "volume-change", "seek"]);

const overlay = ref(null);
const videoEl = ref(null);
const isPlaying = ref(false);
const duration = ref(0);
const currentTime = ref(0);
const progress = ref(0);

watch(
  () => props.videoSrc,
  (src) => {
    if (!src || !videoEl.value) return;
    videoEl.value.load();
    videoEl.value.volume = props.volume ?? 0.5;
    duration.value = 0;
    currentTime.value = 0;
    progress.value = 0;
    isPlaying.value = false;
  }
);

watch(
  () => props.playToken,
  () => {
    if (videoEl.value && props.videoSrc) {
      videoEl.value.play().catch(() => {});
    }
  }
);

watch(
  () => props.pauseToken,
  () => {
    if (videoEl.value && !videoEl.value.paused) {
      videoEl.value.pause();
    }
  }
);

watch(
  () => props.volume,
  (val) => {
    if (videoEl.value) {
      videoEl.value.volume = val ?? 0.5;
    }
  }
);

watch(
  () => props.seekToken,
  () => {
    if (!videoEl.value || duration.value === 0) return;
    const target = Math.max(0, Math.min(1, props.seekFraction ?? 0)) * duration.value;
    videoEl.value.currentTime = target;
    currentTime.value = target;
    progress.value = duration.value ? target / duration.value : 0;
  }
);

function emitPlay() {
  emit("play");
}

function emitPause() {
  emit("pause");
}

function onVolumeChange(e) {
  const val = parseFloat(e.target.value);
  emit("volume-change", isNaN(val) ? 0.5 : val);
}

function onSeekInput(e) {
  const val = parseFloat(e.target.value);
  const frac = isNaN(val) ? 0 : Math.max(0, Math.min(1, val));
  emit("seek", frac);
}

function onTimeUpdate() {
  if (!videoEl.value) return;
  duration.value = videoEl.value.duration || duration.value;
  currentTime.value = videoEl.value.currentTime || 0;
  progress.value = duration.value ? currentTime.value / duration.value : 0;
}

function onLoadedMetadata() {
  if (!videoEl.value) return;
  duration.value = videoEl.value.duration || 0;
}

function formatTime(sec) {
  const s = Math.floor(sec || 0);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

onMounted(() => {
  const c = overlay.value;
  if (!c) return;
  const parent = c.parentElement;
  const rect = parent.getBoundingClientRect();
  c.width = Math.floor(rect.width);
  c.height = Math.floor(rect.height);

  const ctx = c.getContext("2d");
  ctx.strokeStyle = "rgba(0, 180, 255, 0.9)";
  ctx.lineWidth = 2;
  ctx.strokeRect(40, 40, 180, 120);
  ctx.fillStyle = "rgba(0, 180, 255, 0.9)";
  ctx.fillText("ID: 7", 46, 36);
});
</script>

<style scoped>
.video-wrap {
  position: relative;
  width: 100%;
  border-radius: 14px;
  overflow: hidden;
  background: #0b1220;
}

.video-el {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 1;
}

.video-placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  text-align: center;
  background: radial-gradient(circle at 30% 20%, rgba(255,255,255,0.08), transparent 55%),
              radial-gradient(circle at 70% 80%, rgba(255,255,255,0.06), transparent 55%);
}

.overlay-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
  pointer-events: none;
}

.volume-slider {
  width: 120px;
}

.progress-slider {
  width: 180px;
}

.icon-btn {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 18px;
  padding: 0;
}
</style>




