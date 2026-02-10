<template>
  <div class="card h-full flex flex-col">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm font-semibold">Video + Detection Overlay</div>
      <div class="text-xs text-slate-500">Slot {{ slotName }}</div>
    </div>

    <div
      class="video-wrap"
      style="height: 420px;"
      @click="openFilePicker"
      @dragover="onDragOver"
      @drop="onDrop"
    >
      <input
        ref="fileInput"
        type="file"
        accept="video/*"
        class="hidden"
        @change="onFileChange"
      />

      <video
        v-if="videoSrc"
        ref="videoEl"
        class="video-el"
        :src="videoSrc"
        preload="metadata"
        playsinline
        controls
        @play="isPlaying = true"
        @pause="isPlaying = false"
        @loadedmetadata="onMeta"
        @error="onErr"
      />

      <div v-else class="video-placeholder">
        <div class="text-xs text-slate-500 mt-1">
          Drop a video or click to select
        </div>
      </div>

      <canvas ref="overlay" class="overlay-canvas"></canvas>
    </div>

    <div class="mt-2 flex items-center gap-2 text-xs text-slate-600">
      <button
        v-if="videoSrc"
        class="ui-btn-secondary"
        type="button"
        @click="togglePlay"
      >
        {{ isPlaying ? "Pause" : "Play" }}
      </button>
      <span v-if="selectedFile">{{ selectedFile.name }}</span>
      <span v-else>Overlay: bbox / id / center (WS JSON) ??canvas draw (TODO)</span>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  slotName: { type: String, required: true },
});

const overlay = ref(null);
const fileInput = ref(null);
const videoEl = ref(null);
const selectedFile = ref(null);
const videoSrc = ref("");
const isPlaying = ref(false);
let objectUrl = null;

const emit = defineEmits(["upload"]);

function openFilePicker() {
  fileInput.value?.click();
}

function handleFiles(files) {
  console.log("canPlay mp4:", videoEl.value?.canPlayType(selectedFile.value?.type || "video/mp4"));
  
  const file = files?.[0];

  const probe = document.createElement("video");
  console.log("file.type:", file.type);
  console.log("canPlayType(file.type):", probe.canPlayType(file.type || "video/mp4"));
  console.log("canPlayType(H.264 baseline):", probe.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"'));
  console.log("canPlayType(H.265/HEVC):", probe.canPlayType('video/mp4; codecs="hvc1"'));
  console.log("canPlayType(AV1):", probe.canPlayType('video/mp4; codecs="av01.0.05M.08"'));

  if (!file) return;
  selectedFile.value = file;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(file);
  videoSrc.value = objectUrl;
  nextTick(async () => {
    if (!videoEl.value) return;
    videoEl.value.load();
    try {
      await videoEl.value.play();
      console.log("play success");
    } catch (err) {
      console.error("play failed:", err);
    }
  });
  emit("upload", { slot: props.slotName, file });
}

function onFileChange(e) {
  handleFiles(e.target.files);
}

function onDrop(e) {
  e.preventDefault();
  handleFiles(e.dataTransfer.files);
}

function onDragOver(e) {
  e.preventDefault();
}

function togglePlay() {
  if (!videoEl.value) return;
  if (videoEl.value.paused) {
    videoEl.value.play().catch(() => {});
  } else {
    videoEl.value.pause();
  }
}

// 동영상 에러 로그 확인 -----------------------------------
function onMeta() {
  console.log("metadata loaded",
    videoEl.value.videoWidth,
    videoEl.value.videoHeight,
    videoEl.value.duration
  );
}
// -------------------------------------------------------
function onErr() {
  console.error("video error:", videoEl.value?.error);
}

onBeforeUnmount(() => {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
});

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
