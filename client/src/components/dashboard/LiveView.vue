<template>
  <section class="space-y-4 chat-safe">
    <div class="panel">
      <div class="flex items-center justify-between gap-3 mb-3">
        <div>
          <div class="text-sm text-slate-500">Live</div>
          <div class="text-lg font-bold">GoPro 실시간 스트리밍</div>
        </div>
        <div class="flex items-center gap-3 text-xs">
          <span class="inline-flex items-center gap-1.5">
            <span class="status-dot" :class="isStreaming ? 'active' : 'inactive'" />
            <span class="text-slate-500">{{ statusLabel }}</span>
          </span>
          <span v-if="errorMsg" class="text-rose-600">{{ errorMsg }}</span>
        </div>
      </div>

      <div class="card h-full flex flex-col">
        <div ref="wrapEl" class="video-wrap">

          <!-- MJPEG 스트림 -->
          <img
            v-if="isStreaming"
            :src="streamUrl"
            class="video-el"
            @error="onStreamError"
          />

          <!-- 연결 전 placeholder -->
          <div v-else class="video-placeholder">
            <div class="ph-left">
              <div class="ph-title">GoPro 라이브</div>
              <div class="ph-desc">
                아래 버튼을 눌러<br>실시간 스트리밍을 시작합니다.
              </div>
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

        </div>

        <!-- 컨트롤 -->
        <div class="mt-3 flex items-center gap-3 text-xs text-slate-600">
          <button
            class="ui-btn-secondary px-4 py-1.5"
            @click="isStreaming ? stopLive() : startLive()"
          >
            {{ isStreaming ? '연결 끊기' : '스트리밍 시작' }}
          </button>
          <span v-if="isStreaming" class="text-slate-400">
            AI 박스 오버레이 포함 · MJPEG
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from "vue";

const API_BASE = "http://localhost:8000";

const wrapEl      = ref(null);
const isStreaming  = ref(false);
const streamUrl    = ref("");
const errorMsg     = ref("");

const statusLabel = computed(() => {
  if (isStreaming.value) return "스트리밍 중";
  return "연결 안 됨";
});

function startLive() {
  errorMsg.value    = "";
  streamUrl.value   = `${API_BASE}/live/mjpeg`;
  isStreaming.value = true;
}

function stopLive() {
  isStreaming.value = false;
  streamUrl.value   = "";
  errorMsg.value    = "";
}

function onStreamError() {
  errorMsg.value    = "스트림 연결 실패. 서버를 확인해주세요.";
  isStreaming.value = false;
  streamUrl.value   = "";
}
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
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 80px;
  background: #f8fafc;
}
.ph-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 320px;
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
.ph-right { flex-shrink: 0; opacity: 0.9; }

.status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.status-dot.active   { background: #22c55e; }
.status-dot.inactive { background: #94a3b8; }
</style>