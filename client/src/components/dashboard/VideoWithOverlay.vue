<template>
  <div class="card h-full flex flex-col">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm font-semibold">Video + Detection Overlay</div>
      <div class="text-xs text-slate-500">Slot {{ slotName }}</div>
    </div>

    <div class="video-wrap" style="height: 420px;">
      <video
        v-if="videoSrc"
        ref="videoEl"
        class="video-el"
        :src="videoSrc"
        autoplay
        muted
        playsinline
        controls
        @play="isPlaying = true"
        @pause="isPlaying = false"
      />

      <div v-else class="video-placeholder">
        <div class="text-xs text-slate-500 mt-1">
          Upload once above to play in both panels
        </div>
      </div>

      <canvas ref="overlay" class="overlay-canvas"></canvas>
    </div>

    <div class="mt-2 flex items-center gap-2 text-xs text-slate-600">
      <span v-if="videoSrc">{{ isPlaying ? "Playing" : "Paused" }}</span>
      <span v-else>Overlay: bbox / id / center (WS JSON) -> canvas draw (TODO)</span>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch, nextTick } from "vue";

const props = defineProps({
  slotName: { type: String, required: true },
  videoSrc: { type: String, default: "" },
});

const overlay = ref(null);
const videoEl = ref(null);
const isPlaying = ref(false);

watch(
  () => props.videoSrc,
  (src) => {
    if (!src || !videoEl.value) return;
    videoEl.value.load();
    nextTick(() => videoEl.value?.play().catch(() => {}));
  }
);

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
</style>
