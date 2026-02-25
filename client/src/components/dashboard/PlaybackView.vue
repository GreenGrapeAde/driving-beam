<template>
  <section class="space-y-4 chat-safe">
    <UploadOnceBar
      :enabled="true"
      helper="Upload video for playback"
      @uploaded="onUploaded"
      @cleared="onCleared"
    />

    <div class="panel">
      <div class="flex items-center justify-between gap-3 mb-3">
        <div>
          <div class="text-sm text-slate-500">Playback</div>
          <div class="text-lg font-bold">Local video + server detections</div>
        </div>
        <div class="flex items-center gap-3 text-xs text-slate-500">
          <div class="flex items-center gap-2">
            <span>Status:</span>
            <span class="font-semibold">{{ uiState }}</span>
            <span v-if="store.isUploading" class="inline-flex items-center gap-2">
              <span class="spinner"></span>
              {{ store.uploadProgress }}%
            </span>
          </div>
          <span v-if="errorMsg" class="text-rose-600">{{ errorMsg }}</span>
        </div>
      </div>

      <div class="card h-full flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <div class="text-sm font-semibold">Playback + Overlay</div>
          <div class="text-xs text-slate-500">
            {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
            <span class="ml-2">dets: {{ lastDets.length }}</span>
            <span class="ml-2">server_fps: {{ metrics.server_fps?.toFixed?.(1) ?? "-" }}</span>
          </div>
        </div>

        <div ref="wrapEl" class="video-wrap">
          <video
            v-if="store.videoSrc"
            ref="videoEl"
            class="video-el"
            :src="store.videoSrc"
            playsinline
            @loadedmetadata="onLoadedMetadata"
            @timeupdate="onTimeUpdate"
            @seeking="onSeeking"
            @seeked="onSeeked"
            @play="onPlay"
            @pause="onPause"
          />

          <div v-else class="video-placeholder">
            <div class="text-xs text-slate-500 mt-1">No video yet. Upload one.</div>
          </div>

          <canvas ref="canvasEl" class="overlay-canvas"></canvas>
        </div>

        <div class="mt-3 flex items-center flex-wrap gap-3 text-xs text-slate-600">
          <div class="flex items-center gap-2">
            <button class="ui-btn-secondary icon-btn" type="button" :disabled="controlsDisabled" @click="emitPlay">
              <span aria-label="Play">&#9658;</span>
            </button>
            <button class="ui-btn-secondary icon-btn" type="button" :disabled="controlsDisabled" @click="emitPause">
              <span aria-label="Pause">&#10074;&#10074;</span>
            </button>
          </div>

          <div class="flex items-center gap-2 min-w-[220px]">
            <span>Seek</span>
            <input
              class="progress-slider"
              type="range"
              min="0"
              max="1"
              step="0.001"
              :value="progress"
              @input="onSeekInput"
              :disabled="controlsDisabled || duration === 0"
            />
            <span class="w-16 text-right">{{ formatTime(currentTime) }}</span>
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
              :disabled="controlsDisabled"
            />
            <span class="w-8 text-right">{{ Math.round(volume * 100) }}%</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const WS_BASE = "ws://localhost:8000";

import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import UploadOnceBar from "../sub/UploadOnceBar.vue";
import { usePlaybackCropStore } from "@/playbackCrop";

const store = usePlaybackCropStore();

const uiState = ref("NO_VIDEO"); // NO_VIDEO | UPLOADING | READY | AI_ON | ERROR
const errorMsg = ref("");

const ws = ref(null);

// video refs
const videoEl = ref(null);
const canvasEl = ref(null);
const wrapEl = ref(null);

const duration = ref(0);
const currentTime = ref(0);
const progress = ref(0);
const volume = ref(0.5);
const isSeeking = ref(false);
const seekHoldUntil = ref(0);

// meta from server
const meta = ref({ fps_src: 30, frame_w: 0, frame_h: 0, infer_stride: 10 });

// detections buffer: [{t_ms, detections, frame_index}]
const detBuffer = ref([]);
const lastDets = ref([]);
const metrics = ref({});

// render/cache
const wrapSize = ref({ w: 0, h: 0, dpr: 1 });
const mapInfo = ref({ frameW: 0, frameH: 0, scale: 1, offX: 0, offY: 0 });
const ctxRef = ref(null);

let rafId = null;
let ro = null;
let lastDrawTs = 0;
let lastDebugTs = 0;
const needsRedraw = ref(false);

const DEV = import.meta?.env?.DEV ?? false;
const DET_TOL_MS = 120;
const SEEK_TRIM_MS = 2000;
const SEEK_HOLD_MS = 250;

const controlsDisabled = computed(() => !store.videoSrc || store.isUploading);

async function onUploaded(payload) {
  errorMsg.value = "";
  uiState.value = "UPLOADING";

  store.setVideoLocal(payload.src);

  try {
    await store.uploadVideo(payload.file);
    uiState.value = "READY";
    detBuffer.value = [];
    lastDets.value = [];
    metrics.value = {};
    clearCanvas();
    startWs();
  } catch (e) {
    uiState.value = "ERROR";
    errorMsg.value = e?.message || "upload failed";
  }
}

function onCleared() {
  stopWs();
  store.reset();
  detBuffer.value = [];
  lastDets.value = [];
  metrics.value = {};
  duration.value = 0;
  currentTime.value = 0;
  progress.value = 0;
  uiState.value = "NO_VIDEO";
  clearCanvas();
}

function startWs() {
  errorMsg.value = "";
  if (!store.filename) {
    errorMsg.value = "No uploaded filename.";
    return;
  }
  stopWs();

  const socket = new WebSocket(`${WS_BASE}/ws/stream/upload`);
  ws.value = socket;

  socket.onopen = () => {
    uiState.value = "AI_ON";
    socket.send(JSON.stringify({ filename: store.filename }));
  };

  socket.onmessage = (evt) => {
    let msg;
    try {
      msg = JSON.parse(evt.data);
    } catch {
      return;
    }

    if (msg.type === "meta") {
      meta.value = {
        fps_src: msg.fps_src ?? 30,
        frame_w: msg.frame_w ?? 0,
        frame_h: msg.frame_h ?? 0,
        infer_stride: msg.infer_stride ?? 10,
      };
      updateMapInfo();
      return;
    }

    if (msg.type === "error") {
      uiState.value = "ERROR";
      errorMsg.value = msg.message || "ws error";
      return;
    }

    if (msg.type === "end") {
      stopWs(false);
      uiState.value = store.videoSrc ? "READY" : "NO_VIDEO";
      return;
    }

    if (msg.type === "det") {
      const fps = meta.value.fps_src || 30;
      const t_ms = typeof msg.t_ms === "number"
        ? msg.t_ms
        : (msg.frame_index ? (msg.frame_index / fps) * 1000 : 0);

      detBuffer.value.push({ t_ms, detections: msg.detections ?? [], frame_index: msg.frame_index ?? 0 });
      trimDetBuffer(currentTime.value * 1000, 10000);
      metrics.value = msg.metrics || {};
      needsRedraw.value = true;
    }
  };

  socket.onerror = () => {
    uiState.value = "ERROR";
    errorMsg.value = "WebSocket error";
  };

  socket.onclose = () => {
    ws.value = null;
  };
}

function sendWsControl(action, payload = {}) {
  if (!ws.value) return;
  try {
    ws.value.send(JSON.stringify({ type: "control", action, ...payload }));
  } catch {}
}

function stopWs(sendStop = true) {
  if (ws.value) {
    try {
      if (sendStop) ws.value.send(JSON.stringify({ type: "control", action: "stop" }));
    } catch {}
    try { ws.value.close(); } catch {}
  }
  ws.value = null;
}

function emitPlay() {
  if (controlsDisabled.value) return;
  videoEl.value?.play().catch(() => {});
}

function emitPause() {
  videoEl.value?.pause();
}

function onVolumeChange(e) {
  const val = parseFloat(e.target.value);
  volume.value = isNaN(val) ? 0.5 : val;
  if (videoEl.value) videoEl.value.volume = volume.value;
}

function onSeekInput(e) {
  if (!videoEl.value || duration.value === 0) return;
  const frac = Math.max(0, Math.min(1, parseFloat(e.target.value) || 0));
  videoEl.value.currentTime = frac * duration.value;
  currentTime.value = videoEl.value.currentTime || 0;
  progress.value = duration.value ? currentTime.value / duration.value : 0;
}

function onLoadedMetadata() {
  if (!videoEl.value) return;
  duration.value = videoEl.value.duration || 0;
  if (videoEl.value) videoEl.value.volume = volume.value;
  updateMapInfo();
  needsRedraw.value = true;
}

function onTimeUpdate() {
  if (!videoEl.value) return;
  currentTime.value = videoEl.value.currentTime || 0;
  progress.value = duration.value ? currentTime.value / duration.value : 0;
  needsRedraw.value = true;
}

function onSeeking() {
  if (!videoEl.value) return;
  isSeeking.value = true;
  const t_ms = (videoEl.value.currentTime || 0) * 1000;
  trimDetBuffer(t_ms, SEEK_TRIM_MS);
  clearCanvas();
  seekHoldUntil.value = performance.now() + SEEK_HOLD_MS;
  sendWsControl("seek", { t_ms });
}

function onSeeked() {
  isSeeking.value = false;
  needsRedraw.value = true;
}

function onPlay() {
  if (store.isUploading) {
    videoEl.value?.pause();
    return;
  }
  startRaf();
}

function onPause() {
  stopRaf();
  needsRedraw.value = true;
}

function startRaf() {
  if (rafId) return;
  const loop = () => {
    updateOverlay();
    rafId = requestAnimationFrame(loop);
  };
  rafId = requestAnimationFrame(loop);
}

function stopRaf() {
  if (!rafId) return;
  cancelAnimationFrame(rafId);
  rafId = null;
}

function formatTime(sec) {
  const s = Math.floor(sec || 0);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

function resizeCanvas(wrapRect) {
  const c = canvasEl.value;
  if (!c || !wrapRect) return;

  const dpr = window.devicePixelRatio || 1;
  wrapSize.value = { w: wrapRect.width, h: wrapRect.height, dpr };

  c.width = Math.max(1, Math.floor(wrapRect.width * dpr));
  c.height = Math.max(1, Math.floor(wrapRect.height * dpr));
  c.style.width = `${wrapRect.width}px`;
  c.style.height = `${wrapRect.height}px`;

  const ctx = c.getContext("2d");
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctxRef.value = ctx;

  updateMapInfo();
  needsRedraw.value = true;
}

function updateMapInfo() {
  const { w: wrapW, h: wrapH } = wrapSize.value;
  if (!wrapW || !wrapH) return;

  const frameW = meta.value.frame_w || videoEl.value?.videoWidth || 0;
  const frameH = meta.value.frame_h || videoEl.value?.videoHeight || 0;
  if (!frameW || !frameH) return;

  const scale = Math.min(wrapW / frameW, wrapH / frameH);
  const drawW = frameW * scale;
  const drawH = frameH * scale;
  const offX = (wrapW - drawW) / 2;
  const offY = (wrapH - drawH) / 2;

  mapInfo.value = { frameW, frameH, scale, offX, offY };
}

function trimDetBuffer(t_ms, keepMs) {
  const minT = t_ms - keepMs;
  const maxT = t_ms + keepMs;
  detBuffer.value = detBuffer.value.filter((d) => d.t_ms >= minT && d.t_ms <= maxT);
}

function selectDetForTime(t_ms_now) {
  const buf = detBuffer.value;
  if (!buf.length) return null;
  let best = null;
  let bestDiff = Infinity;
  for (const d of buf) {
    const diff = Math.abs((d.t_ms ?? 0) - t_ms_now);
    if (diff < bestDiff) {
      bestDiff = diff;
      best = d;
    }
  }
  if (bestDiff > DET_TOL_MS) return null;
  return { ...best, delta: bestDiff };
}

function mapFrameToCanvas(det) {
  const { scale, offX, offY } = mapInfo.value;
  const w = Math.max(0, (det.x2 - det.x1) * scale);
  const h = Math.max(0, (det.y2 - det.y1) * scale);
  return {
    x: offX + det.x1 * scale,
    y: offY + det.y1 * scale,
    w,
    h,
  };
}

function updateOverlay() {
  const v = videoEl.value;
  const ctx = ctxRef.value;
  const { w: wrapW, h: wrapH } = wrapSize.value;
  if (!v || !ctx || !wrapW || !wrapH) return;

  const now = performance.now();
  if (now - lastDrawTs < 33 && !needsRedraw.value) return; // <= ~30fps
  lastDrawTs = now;
  needsRedraw.value = false;

  if (isSeeking.value || now < seekHoldUntil.value) {
    ctx.clearRect(0, 0, wrapW, wrapH);
    return;
  }

  const t_ms_now = (v.currentTime || 0) * 1000;
  const match = selectDetForTime(t_ms_now);
  const dets = match?.detections ?? [];
  lastDets.value = dets;

  ctx.clearRect(0, 0, wrapW, wrapH);

  const { frameW, frameH } = mapInfo.value;
  if (!frameW || !frameH) return;

  ctx.lineWidth = 2;
  ctx.font = "14px sans-serif";

  for (const det of dets) {
    const mapped = mapFrameToCanvas(det);
    if (mapped.w <= 0 || mapped.h <= 0) continue;

    ctx.strokeStyle = "lime";
    ctx.strokeRect(mapped.x, mapped.y, mapped.w, mapped.h);

    const cls = det.cls ?? "obj";
    const conf = det.conf ?? 0;
    const id = det.id != null ? `#${det.id}` : "";
    const label = `${cls}${id} ${conf.toFixed ? conf.toFixed(2) : conf}`;

    ctx.fillStyle = "lime";
    ctx.fillText(label, mapped.x, Math.max(14, mapped.y - 6));
  }

  if (DEV && now - lastDebugTs > 500) {
    lastDebugTs = now;
    const delta = match?.delta ?? null;
    console.log(
      "[playback] t_ms:", Math.round(t_ms_now),
      "sel_t:", match?.t_ms ?? null,
      "delta:", delta != null ? Math.round(delta) : null,
      "buf:", detBuffer.value.length
    );
  }
}

function clearCanvas() {
  const ctx = ctxRef.value;
  const { w: wrapW, h: wrapH } = wrapSize.value;
  if (!ctx || !wrapW || !wrapH) return;
  ctx.clearRect(0, 0, wrapW, wrapH);
}

watch(
  () => store.isUploading,
  (val) => {
    if (val) videoEl.value?.pause();
  }
);

onMounted(() => {
  if (wrapEl.value) {
    ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      resizeCanvas(rect);
    });
    ro.observe(wrapEl.value);
  }
});

onBeforeUnmount(() => {
  stopRaf();
  stopWs();
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
  height: 520px;
  border-radius: 14px;
  overflow: hidden;
  background: #0b1220;
}

.video-el {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
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
  width: 200px;
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

.spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid rgba(148,163,184,0.5);
  border-top-color: rgba(15,23,42,0.9);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
