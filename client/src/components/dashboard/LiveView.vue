<template>
  <section class="space-y-4 chat-safe">
    <div class="panel">
      <div class="flex items-center justify-between gap-3 mb-3">
        <div>
          <div class="text-sm text-slate-500">Live</div>
          <div class="text-lg font-bold">실시간 스트리밍</div>
        </div>
        <div class="flex items-center gap-3 text-xs">
          <span class="inline-flex items-center gap-1.5">
            <span class="status-dot" :class="store.isStreaming ? 'active' : 'inactive'" />
            <span class="text-slate-500">{{ statusLabel }}</span>
          </span>
          <span v-if="store.isStreaming" class="text-slate-400">
            저장됨: {{ store.writtenCount }}장
          </span>
          <span v-if="store.errorMsg" class="text-rose-600">{{ store.errorMsg }}</span>
        </div>
      </div>

      <div class="card h-full flex flex-col">
        <div ref="wrapEl" class="video-wrap">

          <img
            v-if="store.isStreaming"
            ref="imgEl"
            :src="store.streamUrl"
            class="video-el"
            @error="store.onStreamError()"
            @load="onImgLoad"
          />

          <div v-else class="video-placeholder">
            <div class="ph-left">
              <div class="ph-title">실시간 데이터셋 추출</div>
              <div class="ph-desc">아래 버튼을 눌러<br>실시간 스트리밍을 시작합니다.</div>
            </div>
            <div class="ph-right">
              <svg width="140" height="168" viewBox="0 0 54 64" fill="none">
                <rect x="2" y="2" width="42" height="54" rx="5" fill="#dbeafe" stroke="#93c5fd" stroke-width="2"/>
                <path d="M30 2 L44 16 L30 16 Z" fill="#93c5fd"/>
                <circle cx="39" cy="49" r="13" fill="#2563eb"/>
                <polygon points="35,44 35,54 47,49" fill="white"/>
              </svg>
            </div>
          </div>

          <canvas ref="canvasEl" class="overlay-canvas" />
        </div>

        <div class="mt-3 flex items-center gap-3 text-xs text-slate-600">
          <button class="ui-btn-secondary px-4 py-1.5"
                  @click="store.isStreaming ? store.stopLive() : store.startLive()">
            {{ store.isStreaming ? '연결 끊기' : '스트리밍 시작' }}
          </button>
          <button v-if="store.isStreaming"
                  class="ui-btn px-4 py-1.5"
                  @click="store.exportZip()">
            ZIP 다운로드
          </button>
          <span v-if="store.exportMsg" class="text-emerald-600">{{ store.exportMsg }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useLiveCropStore } from "@/liveCrop";

const store = useLiveCropStore();

const wrapEl   = ref(null);
const imgEl    = ref(null);
const canvasEl = ref(null);

let ctxRef   = null;
let wrapSize = { w: 0, h: 0 };
let rafId    = null;
let ro       = null;

const statusLabel = computed(() =>
  store.isStreaming ? "스트리밍 중" : "연결 안 됨"
);

// ── canvas resize ────────────────────────────────────────────
function resizeCanvas(rect) {
  const c = canvasEl.value;
  if (!c || !rect) return;
  const dpr = window.devicePixelRatio || 1;
  wrapSize = { w: rect.width, h: rect.height };
  c.width  = Math.floor(rect.width  * dpr);
  c.height = Math.floor(rect.height * dpr);
  c.style.width  = `${rect.width}px`;
  c.style.height = `${rect.height}px`;
  const ctx = c.getContext("2d");
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctxRef = ctx;
}

function onImgLoad() {
  if (imgEl.value) {
    store.frameW = imgEl.value.naturalWidth  || store.frameW;
    store.frameH = imgEl.value.naturalHeight || store.frameH;
  }
}

// ── RAF 드로우 루프 ──────────────────────────────────────────
function startRaf() {
  if (rafId) return;
  const loop = () => { drawOverlay(); rafId = requestAnimationFrame(loop); };
  rafId = requestAnimationFrame(loop);
}

function stopRaf() {
  if (!rafId) return;
  cancelAnimationFrame(rafId);
  rafId = null;
  if (ctxRef) ctxRef.clearRect(0, 0, wrapSize.w, wrapSize.h);
}

function drawOverlay() {
  const ctx = ctxRef;
  const { w: wW, h: wH } = wrapSize;
  const frameW = store.frameW;
  const frameH = store.frameH;
  if (!ctx || !wW || !wH || !frameW || !frameH) return;

  ctx.clearRect(0, 0, wW, wH);
  if (!store.dets.length) return;

  const scale = Math.min(wW / frameW, wH / frameH);
  const offX  = (wW - frameW * scale) / 2;
  const offY  = (wH - frameH * scale) / 2;

  ctx.lineWidth = 2;
  ctx.font = "14px sans-serif";

  for (const det of store.dets) {
    const x = offX + det.x1 * scale;
    const y = offY + det.y1 * scale;
    const w = (det.x2 - det.x1) * scale;
    const h = (det.y2 - det.y1) * scale;
    ctx.strokeStyle = "lime";
    ctx.strokeRect(x, y, w, h);
    ctx.fillStyle = "lime";
    ctx.fillText(`${det.cls} ${(det.conf * 100).toFixed(0)}%`, x, Math.max(14, y - 6));
  }
}

// isStreaming 변화 감지 → RAF 시작/종료
watch(() => store.isStreaming, (val) => {
  if (val) startRaf();
  else     stopRaf();
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
  store.reset();
  stopRaf();
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
  position: absolute; inset: 0;
  display: flex; align-items: center;
  justify-content: center; gap: 80px;
  background: #f8fafc;
}
.ph-left { display: flex; flex-direction: column; gap: 16px; max-width: 320px; }
.ph-title { font-size: 38px; font-weight: 700; color: #0f172a; line-height: 1.3; }
.ph-desc  { font-size: 16px; color: #64748b; line-height: 1.8; }
.ph-right { flex-shrink: 0; opacity: 0.9; }
.overlay-canvas {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  z-index: 2; pointer-events: none;
}
.status-dot {
  width: 8px; height: 8px; border-radius: 50%; display: inline-block;
}
.status-dot.active   { background: #22c55e; }
.status-dot.inactive { background: #94a3b8; }
</style>