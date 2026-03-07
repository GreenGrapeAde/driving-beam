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
          <span class="font-semibold">{{ uiState }}</span>
          <span v-if="store.isUploading" class="inline-flex items-center gap-1">
            <span class="spinner"></span> 업로드 {{ store.uploadProgress }}%
          </span>
          <span v-if="store.isAnalyzing" class="inline-flex items-center gap-1 text-sky-500">
            <span class="spinner"></span>
            {{ phaseLabel }} {{ store.analyzeProgress }}%
            <span v-if="store.analyzeEta > 0 && store.analyzePhase === 'analyzing'">
              (잔여 {{ store.analyzeEta }}초)
            </span>
          </span>
          <span v-if="errorMsg" class="text-rose-600">{{ errorMsg }}</span>
        </div>
      </div>

      <!-- 진행률 바 -->
      <div v-if="store.isAnalyzing || store.isUploading"
           class="w-full h-1.5 bg-slate-200 rounded-full mb-3 overflow-hidden">
        <div
          class="h-full rounded-full transition-all duration-300"
          :class="progressBarColor"
          :style="{ width: progressBarWidth + '%' }"
        />
      </div>

      <div class="card h-full flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <div class="text-sm font-semibold">Playback + Overlay</div>
          <div class="text-xs text-slate-500">
            {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
            <span class="ml-2">dets: {{ lastDets.length }}</span>
            <span v-if="store.metaInfo" class="ml-2">
              {{ store.metaInfo.frame_w }}×{{ store.metaInfo.frame_h }}
              · stride {{ store.metaInfo.infer_stride }}
            </span>
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
            <!-- 좌측 텍스트 -->
            <div class="ph-left">
              <div class="ph-title">동영상 분석 및<br>데이터셋 추출</div>
              <div class="ph-desc">
                동영상을 업로드하면 AI가 자동으로<br>분석하고 Occlusion 상황의 데이터셋을<br>생성할 수 있습니다.
              </div>
            </div>
            <!-- 우측 아이콘 -->
            <div class="ph-right">
              <svg width="140" height="168" viewBox="0 0 54 64" fill="none">
                <rect x="2" y="2" width="42" height="54" rx="5" fill="#dbeafe" stroke="#93c5fd" stroke-width="2"/>
                <path d="M30 2 L44 16 L30 16 Z" fill="#93c5fd"/>
                <circle cx="39" cy="49" r="13" fill="#2563eb"/>
                <polygon points="35,44 35,54 47,49" fill="white"/>
              </svg>
            </div>
          </div>

          <canvas ref="canvasEl" class="overlay-canvas"></canvas>

          <!-- 분석 중 오버레이 (추론 + 크롭 + ZIP) -->
          <div v-if="store.isAnalyzing" class="task-overlay">
            <div class="text-white text-center px-6">

              <!-- 진행률 숫자 -->
              <div class="text-3xl font-bold mb-2">{{ store.analyzeProgress }}%</div>

              <!-- phase별 메시지 -->
              <div class="text-sm opacity-90 mb-1">{{ phaseLabel }}</div>

              <!-- 크롭 저장 수 (analyzing 중) -->
              <div v-if="store.analyzePhase === 'analyzing'" class="text-xs opacity-60">
                <span v-if="store.analyzeWritten > 0">{{ store.analyzeWritten }}장 저장됨</span>
                <span v-if="store.analyzeEta > 0" class="ml-2">· 잔여 약 {{ store.analyzeEta }}초</span>
              </div>

              <!-- ZIP 생성 중 메시지 -->
              <div v-if="store.analyzePhase === 'zipping'" class="text-xs opacity-60">
                총 {{ store.analyzeWritten }}장 · ZIP 압축 중...
              </div>

              <!-- 진행바 -->
              <div class="mt-4 w-56 h-1.5 bg-white/20 rounded-full overflow-hidden mx-auto">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  :class="overlayBarColor"
                  :style="{ width: store.analyzeProgress + '%' }"
                />
              </div>

              <!-- 취소 버튼 (analyzing 중에만) -->
              <button
                v-if="store.analyzePhase === 'analyzing'"
                class="mt-4 px-4 py-1 text-xs bg-white/20 hover:bg-white/30 rounded"
                @click="onCancelAnalyze"
              >취소</button>
            </div>
          </div>
        </div>

        <div class="mt-3 flex items-center flex-wrap gap-3 text-xs text-slate-600">
          <div class="flex items-center gap-2">
            <button class="ui-btn-secondary icon-btn" type="button"
              :disabled="!canPlay" @click="emitPlay">
              <span>&#9658;</span>
            </button>
            <button class="ui-btn-secondary icon-btn" type="button"
              :disabled="!canPlay" @click="emitPause">
              <span>&#10074;&#10074;</span>
            </button>
          </div>

          <div class="flex items-center gap-2 min-w-[220px]">
            <span>Seek</span>
            <input class="progress-slider" type="range" min="0" max="1" step="0.001"
              :value="progress" @input="onSeekInput"
              :disabled="!canPlay || duration === 0" />
            <span class="w-16 text-right">{{ formatTime(currentTime) }}</span>
          </div>

          <div class="flex items-center gap-2">
            <span>Volume</span>
            <input class="volume-slider" type="range" min="0" max="1" step="0.01"
              :value="volume" @input="onVolumeChange" :disabled="!canPlay" />
            <span class="w-8 text-right">{{ Math.round(volume * 100) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <MetricsTable
      :det-list="store.detList"
      :is-analyzing="store.isAnalyzing"
      :analyze-written="store.analyzeWritten"
      :analyze-phase="store.analyzePhase"
      :clear-token="clearToken"
      :written-counts="store.writtenCounts"
    />
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import UploadOnceBar from "../sub/UploadOnceBar.vue";
import { usePlaybackCropStore } from "@/playbackCrop";
import MetricsTable from "../sub/MetricsTable.vue";

const store = usePlaybackCropStore();

const uiState  = ref("NO_VIDEO");
const errorMsg = ref("");

const videoEl  = ref(null);
const canvasEl = ref(null);
const wrapEl   = ref(null);

const duration      = ref(0);
const currentTime   = ref(0);
const progress      = ref(0);
const volume        = ref(0.5);
const isSeeking     = ref(false);
const seekHoldUntil = ref(0);

const wrapSize    = ref({ w: 0, h: 0 });
const mapInfo     = ref({ frameW: 0, frameH: 0, scale: 1, offX: 0, offY: 0 });
const ctxRef      = ref(null);
const needsRedraw = ref(false);
const lastDets    = ref([]);

let rafId      = null;
let ro         = null;
let lastDrawTs = 0;

const clearToken = ref(0);

// ── computed ──────────────────────────────────────────────────
const canPlay = computed(() =>
  !!store.videoSrc && !store.isUploading && !store.isAnalyzing && store.detList.length > 0
);

// phase → 한글 레이블
const phaseLabel = computed(() => {
  if (store.analyzePhase === "zipping")   return "ZIP 생성 중";
  if (store.analyzePhase === "done")      return "완료";
  return "분석 + 크롭 중";
});

// 상단 진행바 색상
const progressBarColor = computed(() => {
  if (store.isUploading)                    return "bg-slate-400";
  if (store.analyzePhase === "zipping")     return "bg-amber-400";
  return "bg-sky-500";
});

// 오버레이 안 진행바 색상
const overlayBarColor = computed(() => {
  if (store.analyzePhase === "zipping") return "bg-amber-400";
  return "bg-sky-400";
});

// 상단 진행바 너비
const progressBarWidth = computed(() => {
  if (store.isUploading)   return store.uploadProgress;
  if (store.isAnalyzing)   return store.analyzeProgress;
  return 0;
});

// ─── 업로드 완료 → 추론+크롭+다운로드 ───────────────────────
async function onUploaded(payload) {
  errorMsg.value = "";
  uiState.value  = "UPLOADING";
  store.setVideoLocal(payload.src);

  try {
    await store.uploadVideo(payload.file);
    uiState.value = "ANALYZING";
    // 추론 + 크롭 동시 + 완료 시 자동 다운로드
    await store.analyzeVideo(store.filename, 3, 0.4);
    uiState.value = "READY";
    needsRedraw.value = true;
  } catch (e) {
    if (e?.message === "cancelled") { uiState.value = "READY"; return; }
    uiState.value  = "ERROR";
    errorMsg.value = e?.message || "failed";
  }
}

function onCleared() {
  clearToken.value += 1;
  store.cancelAnalyze();
  store.reset();
  duration.value    = 0;
  currentTime.value = 0;
  progress.value    = 0;
  lastDets.value    = [];
  uiState.value     = "NO_VIDEO";
  errorMsg.value    = "";
  stopRaf();
  clearCanvas();
}

function onCancelAnalyze() {
  store.cancelAnalyze();
  uiState.value = "READY";
}

// ─── 비디오 이벤트 ────────────────────────────────────────────
function onLoadedMetadata() {
  if (!videoEl.value) return;
  duration.value = videoEl.value.duration || 0;
  videoEl.value.volume = volume.value;
  updateMapInfo();
  needsRedraw.value = true;
}

function onTimeUpdate() {
  if (!videoEl.value) return;
  currentTime.value = videoEl.value.currentTime || 0;
  progress.value    = duration.value ? currentTime.value / duration.value : 0;
  needsRedraw.value = true;
}

function onSeeking() {
  isSeeking.value     = true;
  seekHoldUntil.value = performance.now() + 150;
  clearCanvas();
}

function onSeeked()  { isSeeking.value = false; needsRedraw.value = true; }
function onPlay()    { startRaf(); }
function onPause()   { stopRaf(); needsRedraw.value = true; updateOverlay(); }
function emitPlay()  { if (canPlay.value) videoEl.value?.play().catch(() => {}); }
function emitPause() { videoEl.value?.pause(); }

function onVolumeChange(e) {
  volume.value = parseFloat(e.target.value) || 0.5;
  if (videoEl.value) videoEl.value.volume = volume.value;
}

function onSeekInput(e) {
  if (!videoEl.value || duration.value === 0) return;
  const frac = Math.max(0, Math.min(1, parseFloat(e.target.value) || 0));
  videoEl.value.currentTime = frac * duration.value;
  currentTime.value = videoEl.value.currentTime || 0;
  progress.value    = duration.value ? currentTime.value / duration.value : 0;
}

// ─── RAF ─────────────────────────────────────────────────────
function startRaf() {
  if (rafId) return;
  const loop = () => { updateOverlay(); rafId = requestAnimationFrame(loop); };
  rafId = requestAnimationFrame(loop);
}

function stopRaf() {
  if (!rafId) return;
  cancelAnimationFrame(rafId);
  rafId = null;
}

watch(needsRedraw, (val) => { if (val && !rafId) updateOverlay(); });

// ─── Canvas ───────────────────────────────────────────────────
function resizeCanvas(rect) {
  const c = canvasEl.value;
  if (!c || !rect) return;
  const dpr = window.devicePixelRatio || 1;
  wrapSize.value = { w: rect.width, h: rect.height };
  c.width  = Math.max(1, Math.floor(rect.width  * dpr));
  c.height = Math.max(1, Math.floor(rect.height * dpr));
  c.style.width  = `${rect.width}px`;
  c.style.height = `${rect.height}px`;
  const ctx = c.getContext("2d");
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctxRef.value = ctx;
  updateMapInfo();
  needsRedraw.value = true;
}

function updateMapInfo() {
  const { w: wW, h: wH } = wrapSize.value;
  if (!wW || !wH) return;
  const frameW = store.metaInfo?.frame_w || videoEl.value?.videoWidth  || 0;
  const frameH = store.metaInfo?.frame_h || videoEl.value?.videoHeight || 0;
  if (!frameW || !frameH) return;
  const scale = Math.min(wW / frameW, wH / frameH);
  mapInfo.value = {
    frameW, frameH, scale,
    offX: (wW - frameW * scale) / 2,
    offY: (wH - frameH * scale) / 2,
  };
}

function selectNearestDet(t_ms_now) {
  const list = store.detList;
  if (!list.length) return null;
  let best = list[0];
  let bestDiff = Math.abs(list[0].t_ms - t_ms_now);
  for (let i = 1; i < list.length; i++) {
    const diff = Math.abs(list[i].t_ms - t_ms_now);
    if (diff < bestDiff) { bestDiff = diff; best = list[i]; }
  }
  return best;
}

function mapFrameToCanvas(det) {
  const { scale, offX, offY } = mapInfo.value;
  return {
    x: offX + det.x1 * scale,
    y: offY + det.y1 * scale,
    w: Math.max(0, (det.x2 - det.x1) * scale),
    h: Math.max(0, (det.y2 - det.y1) * scale),
  };
}

function updateOverlay() {
  const v   = videoEl.value;
  const ctx = ctxRef.value;
  const { w: wW, h: wH } = wrapSize.value;
  if (!v || !ctx || !wW || !wH) return;

  const now = performance.now();
  if (now - lastDrawTs < 16 && !needsRedraw.value) return;
  lastDrawTs = now;
  needsRedraw.value = false;

  ctx.clearRect(0, 0, wW, wH);
  if (isSeeking.value || now < seekHoldUntil.value) return;

  const { frameW, frameH } = mapInfo.value;
  if (!frameW || !frameH) return;

  const t_ms_now = (v.currentTime || 0) * 1000;
  const match    = selectNearestDet(t_ms_now);
  const dets     = match?.detections ?? [];
  lastDets.value = dets;

  ctx.lineWidth = 2;
  ctx.font = "14px sans-serif";

  for (const det of dets) {
    const m = mapFrameToCanvas(det);
    if (m.w <= 0 || m.h <= 0) continue;
    ctx.strokeStyle = "lime";
    ctx.strokeRect(m.x, m.y, m.w, m.h);
    const label = `${det.cls ?? "obj"}${det.id != null ? " #" + det.id : ""} ${det.conf?.toFixed(2) ?? ""}`;
    ctx.fillStyle = "lime";
    ctx.fillText(label, m.x, Math.max(14, m.y - 6));
  }
}

function clearCanvas() {
  const ctx = ctxRef.value;
  const { w: wW, h: wH } = wrapSize.value;
  if (ctx && wW && wH) ctx.clearRect(0, 0, wW, wH);
}

function formatTime(sec) {
  const s = Math.floor(sec || 0);
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;
}

watch(() => store.detList.length, (len) => {
  if (len > 0) { updateMapInfo(); needsRedraw.value = true; }
});

onMounted(() => {
  if (wrapEl.value) {
    ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect) resizeCanvas(rect);
    });
    ro.observe(wrapEl.value);
  }
});

onBeforeUnmount(() => {
  stopRaf();
  store.cancelAnalyze();
  store.reset();
  clearCanvas();
  if (ro) { ro.disconnect(); ro = null; }
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
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: contain; z-index: 1;
}
.video-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;  /* ← space-between → center */
  gap: 80px;                /* ← 두 요소 사이 간격 */
  background: #f8fafc;
  /* padding 제거 */
}

.ph-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 320px;         /* ← 텍스트 너비 제한 */
}

.ph-title {
  font-size: 38px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}

.ph-desc {
  font-size: 16px;
  color: #64748b;
  line-height: 1.8;
}

.ph-right {
  flex-shrink: 0;
  opacity: 0.9;
}

.overlay-canvas {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  z-index: 2; pointer-events: none;
}
.task-overlay {
  position: absolute; inset: 0;
  background: rgba(0, 0, 0, 0.70);
  display: flex; align-items: center; justify-content: center;
  z-index: 10;
}
.volume-slider   { width: 120px; }
.progress-slider { width: 200px; }
.icon-btn {
  width: 40px; height: 40px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 999px; font-size: 18px; padding: 0;
}
.spinner {
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid rgba(148,163,184,0.5);
  border-top-color: rgba(15,23,42,0.9);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>