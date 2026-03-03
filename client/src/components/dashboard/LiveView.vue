<template>
  <section class="space-y-4 chat-safe">
    <div class="panel">
      <div class="flex items-center justify-between gap-3 mb-3">
        <div>
          <div class="text-sm text-slate-500">Live</div>
          <div class="text-lg font-bold">GoPro 실시간 스트리밍</div>
        </div>
        <div class="flex items-center gap-3 text-xs">
          <!-- 연결 상태 -->
          <span class="inline-flex items-center gap-1.5">
            <span class="status-dot" :class="isConnected ? 'active' : 'inactive'" />
            <span class="text-slate-500">{{ statusLabel }}</span>
          </span>
          <span v-if="errorMsg" class="text-rose-600">{{ errorMsg }}</span>
        </div>
      </div>

      <div class="card h-full flex flex-col">
        <div ref="wrapEl" class="video-wrap">

          <!-- 라이브 영상 -->
          <video
            v-show="isConnected"
            ref="videoEl"
            class="video-el"
            autoplay
            playsinline
            muted
          />

          <!-- 연결 전 placeholder -->
          <div v-if="!isConnected" class="video-placeholder">
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

          <!-- 연결 중 오버레이 -->
          <div v-if="isConnecting" class="task-overlay">
            <div class="text-white text-center">
              <div class="text-sm opacity-80 mb-2">연결 중...</div>
              <div class="spinner-lg" />
            </div>
          </div>

        </div>

        <!-- 컨트롤 -->
        <div class="mt-3 flex items-center gap-3 text-xs text-slate-600">
          <button
            class="ui-btn-secondary px-4 py-1.5"
            :disabled="isConnecting"
            @click="isConnected ? stopLive() : startLive()"
          >
            {{ isConnected ? '연결 끊기' : '스트리밍 시작' }}
          </button>
          <span v-if="isConnected" class="text-slate-400">
            AI 박스 오버레이 포함 · 서버 렌더링
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from "vue";

const API_BASE = "http://localhost:8000";

const videoEl    = ref(null);
const wrapEl     = ref(null);
const errorMsg   = ref("");
const isConnecting = ref(false);
const isConnected  = ref(false);

let pc = null;

const statusLabel = computed(() => {
  if (isConnecting.value) return "연결 중";
  if (isConnected.value)  return "연결됨";
  return "연결 안 됨";
});

async function startLive() {
  errorMsg.value   = "";
  isConnecting.value = true;

  try {
    pc = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });

    // 서버가 보내는 video track → video 태그에 연결
    pc.ontrack = (evt) => {
      if (videoEl.value && evt.streams[0]) {
        videoEl.value.srcObject = evt.streams[0];
      }
    };

    pc.onconnectionstatechange = () => {
      if (pc.connectionState === "connected") {
        isConnecting.value = false;
        isConnected.value  = true;
      }
      if (pc.connectionState === "failed" || pc.connectionState === "disconnected") {
        stopLive();
        errorMsg.value = "연결이 끊어졌습니다.";
      }
    };

    // offer 생성 (video 수신 전용)
    const offer = await pc.createOffer({ offerToReceiveVideo: true });
    await pc.setLocalDescription(offer);

    // 서버에 offer 전송
    const res = await fetch(`${API_BASE}/live/webrtc`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ sdp: pc.localDescription.sdp }),
    });

    if (!res.ok) throw new Error(`서버 오류 ${res.status}`);

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    await pc.setRemoteDescription({ type: "answer", sdp: data.sdp });

  } catch (e) {
    errorMsg.value     = e.message || "연결 실패";
    isConnecting.value = false;
    isConnected.value  = false;
    if (pc) { pc.close(); pc = null; }
  }
}

function stopLive() {
  if (pc) { pc.close(); pc = null; }
  if (videoEl.value) videoEl.value.srcObject = null;
  isConnected.value  = false;
  isConnecting.value = false;
}

onBeforeUnmount(() => { stopLive(); });
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

.task-overlay {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.65);
  display: flex; align-items: center; justify-content: center;
  z-index: 10;
}

/* 연결 상태 dot */
.status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.status-dot.active   { background: #22c55e; }
.status-dot.inactive { background: #94a3b8; }

/* 로딩 스피너 (큰 버전) */
.spinner-lg {
  width: 32px; height: 32px;
  border-radius: 50%;
  border: 3px solid rgba(255,255,255,0.3);
  border-top-color: white;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>