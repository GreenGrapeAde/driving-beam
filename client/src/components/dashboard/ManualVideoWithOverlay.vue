<template>
  <div class="card h-full flex flex-col">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm font-semibold">Manual Crop Preview</div>
      <div class="text-xs text-slate-500">Slot {{ slotName }}</div>
    </div>

    <div ref="wrapEl" class="video-wrap" style="height: 620px;">
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
          Upload once above to play in manual crop
        </div>
      </div>

      <canvas
        ref="overlay"
        class="overlay-canvas"
        :class="{ 'roi-enabled': enableRoi }"
        @mousedown.prevent="onMouseDown"
        @mousemove.prevent="onMouseMove"
        @mouseup.prevent="onMouseUp"
        @mouseleave="onMouseUp"
        @contextmenu.prevent
      />
    </div>

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
      <span v-else>Overlay: ROI -> canvas draw (TODO)</span>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from "vue";

const props = defineProps({
  slotName: { type: String, required: true },
  videoSrc: { type: String, default: "" },
  playToken: { type: Number, default: 0 },
  pauseToken: { type: Number, default: 0 },
  volume: { type: Number, default: 0.5 },
  seekToken: { type: Number, default: 0 },
  seekFraction: { type: Number, default: 0 },
  enableRoi: { type: Boolean, default: false },
});

const emit = defineEmits([
  "play",
  "pause",
  "volume-change",
  "seek",
  "roi-change",
  "time-update",
  "display-change",
]);

const overlay = ref(null);
const wrapEl = ref(null);
const videoEl = ref(null);
const isPlaying = ref(false);
const duration = ref(0);
const currentTime = ref(0);
const progress = ref(0);

const isDragging = ref(false);
const dragStart = ref(null);
const dragEnd = ref(null);

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
    clearOverlay();
    requestAnimationFrame(syncCanvasSize);
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
  emit("time-update", { currentTime: currentTime.value, duration: duration.value });
}

function onLoadedMetadata() {
  if (!videoEl.value) return;
  duration.value = videoEl.value.duration || 0;
  syncCanvasSize();
}

function formatTime(sec) {
  const s = Math.floor(sec || 0);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

function getDisplaySize() {
  const c = overlay.value;
  if (!c) return { w: 0, h: 0 };
  const rect = c.getBoundingClientRect();
  return { w: rect.width, h: rect.height };
}

function syncCanvasSize() {
  const c = overlay.value;
  const wrap = wrapEl.value || c?.parentElement;
  if (!c || !wrap) return;
  const rect = wrap.getBoundingClientRect();
  const w = Math.max(1, Math.floor(rect.width));
  const h = Math.max(1, Math.floor(rect.height));
  if (c.width !== w || c.height !== h) {
    c.width = w;
    c.height = h;
    emit("display-change", { width: w, height: h });
  }


  drawRoi();
}

function onMouseDown(e) {
  if (!props.enableRoi) return;
  isDragging.value = true;
  dragStart.value = getLocalPoint(e);
  dragEnd.value = dragStart.value;
  drawRoi();
}

function onMouseMove(e) {
  if (!props.enableRoi || !isDragging.value) return;
  dragEnd.value = getLocalPoint(e);
  drawRoi();
}

function onMouseUp() {
  if (!props.enableRoi || !isDragging.value) return;
  isDragging.value = false;

  const roi = getRoiRect();

  // ------------------------------------------------
  const c = overlay.value;

  console.log("UP roi =", roi);
  console.log("canvas wh =", c?.width, c?.height);
  // ------------------------------------------------

  if (roi && roi.w > 0 && roi.h > 0) {
    const { w, h } = getDisplaySize();
    emit("roi-change", { ...roi, displayW: w, displayH: h });
  }
}

function getLocalPoint(e) {
  const c = overlay.value;
  const rect = c.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(rect.width, e.clientX - rect.left)),
    y: Math.max(0, Math.min(rect.height, e.clientY - rect.top)),
  };
}

function getRoiRect() {
  if (!dragStart.value || !dragEnd.value) return null;
  const x1 = Math.min(dragStart.value.x, dragEnd.value.x);
  const y1 = Math.min(dragStart.value.y, dragEnd.value.y);
  const x2 = Math.max(dragStart.value.x, dragEnd.value.x);
  const y2 = Math.max(dragStart.value.y, dragEnd.value.y);
  return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
}

function clearOverlay() {
  const c = overlay.value;
  if (!c) return;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);
}

function drawRoi() {
  const c = overlay.value;

  if (!c) return;

  // drawRoi는 호출되고 있음
  // console.log("drawRoi called");

  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);
  const roi = getRoiRect();
  if (!roi) return;
  ctx.strokeStyle = "rgba(0, 255, 0, 0.9)";
  ctx.lineWidth = 2;
  ctx.strokeRect(roi.x, roi.y, roi.w, roi.h);
}

let ro = null;

onMounted(() => {
  // [debugging]----------------------------------------------
  const c = overlay.value;
  if (c) {
    c.addEventListener("mousedown", () => {
      console.log("canvas mousedown detected");
    });
  }
  console.log("props.enableRoi =", props.enableRoi);
  // ---------------------------------------------------------
  syncCanvasSize();
  window.addEventListener("resize", syncCanvasSize);
  if (wrapEl.value) {
    ro = new ResizeObserver(() => syncCanvasSize());
    ro.observe(wrapEl.value);
  }
});

onUnmounted(() => {
  window.removeEventListener("resize", syncCanvasSize);
  if (ro) {
    ro.disconnect();
    ro = null;
  }
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

.overlay-canvas.roi-enabled {
  pointer-events: auto;
  cursor: crosshair;
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

