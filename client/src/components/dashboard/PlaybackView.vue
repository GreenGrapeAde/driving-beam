<!-- src/components/dashboard/PlaybackView.vue -->
<template>
  <section class="space-y-4 chat-safe">
    <UploadOnceBar
      :enabled="true"
      helper="Upload video for playback"
      @uploaded="onUploaded"
      @cleared="onCleared"
    />

    <!-- Status line -->
    <div class="panel flex items-center justify-between">
      <div class="text-sm text-slate-600">
        <span class="font-semibold">Playback</span>
        <span class="ml-2">Status:</span>
        <span class="ml-1 font-semibold">{{ uiState }}</span>
        <span v-if="errorMsg" class="ml-3 text-rose-600">{{ errorMsg }}</span>
      </div>

      <div class="flex items-center gap-2">
        <button class="ui-btn" type="button" :disabled="!canStart" @click="startWs">Start</button>
        <button class="ui-btn-secondary" type="button" :disabled="!canPause" @click="pauseWs">Pause</button>
        <button class="ui-btn-secondary" type="button" :disabled="!canResume" @click="resumeWs">Resume</button>
        <button class="ui-btn-secondary" type="button" :disabled="!ws" @click="stopWs">Stop</button>
      </div>
    </div>

    <!-- Frame viewer -->
    <div class="panel">
      <div class="flex items-center justify-between mb-3">
        <div>
          <div class="text-sm text-slate-500">WebSocket Frames</div>
          <div class="text-lg font-bold">Annotated Frame Stream</div>
        </div>
        <div class="text-xs text-slate-500">
          frame: {{ frameIndex }} |
          server_fps: {{ metrics.server_fps?.toFixed?.(1) ?? "-" }} |
          stride: {{ metrics.infer_stride ?? "-" }}
        </div>
      </div>

      <div class="w-full h-[520px] rounded-xl border border-slate-200 bg-slate-100 overflow-hidden grid place-items-center">
        <img
          v-if="frameB64"
          class="max-w-full max-h-full object-contain"
          :src="`data:image/jpeg;base64,${frameB64}`"
        />
        <div v-else class="text-slate-500 text-sm">
          No frame yet. Upload and click Start.
        </div>
      </div>

      <!-- Guidance -->
      <div class="mt-3 text-xs text-slate-600">
        ROI crop/extract/save는 <span class="font-semibold">Manual</span> 모드에서 수행합니다.
        (같은 업로드 파일을 사용)
      </div>
    </div>
  </section>
</template>

<script setup>
const WS_BASE = "ws://localhost:8000";

import { computed, onBeforeUnmount, ref } from "vue";
import UploadOnceBar from "../sub/UploadOnceBar.vue";
import { useManualCropStore } from "@/manualCrop";

const store = useManualCropStore();

// UI State
const uiState = ref("NO_VIDEO"); // NO_VIDEO | UPLOADING | READY | PLAYING | PAUSED | END | ERROR
const errorMsg = ref("");

// server upload info
const uploadedFilename = ref("");
const uploadedVideoPath = ref(""); // server path if needed later

// WS
const ws = ref(null);
const frameB64 = ref("");
const frameIndex = ref(0);
const metrics = ref({});

// playback control

const canStart = computed(() => uiState.value === "READY" || uiState.value === "PAUSED");
const canPause = computed(() => uiState.value === "PLAYING");
const canResume = computed(() => uiState.value === "PAUSED");

async function onUploaded(payload) {
  errorMsg.value = "";
  uiState.value = "UPLOADING";

  // 로컬 미리보기(필요하면)
  store.setVideoLocal(payload.src);

  try {
    // 서버 업로드 (manual에서 이미 쓰는 함수 재사용)
    const res = await store.uploadVideo(payload.file); 
    // store.uploadVideo가 { filename, path }를 반환하도록 되어있어야 가장 좋음.
    // 만약 반환 안 하면 store.videoPath / store.filename 같은 상태를 확인해서 매핑.

    // 안전하게 둘 다 처리
    uploadedFilename.value = res?.filename || payload.name || payload.file?.name || "";
    uploadedVideoPath.value = res?.path || store.videoPath || "";

    uiState.value = "READY";
  } catch (e) {
    uiState.value = "ERROR";
    errorMsg.value = e?.message || "upload failed";
  }
}

function onCleared() {
  stopWs();
  store.setVideoLocal("");
  uploadedFilename.value = "";
  uploadedVideoPath.value = "";
  frameB64.value = "";
  frameIndex.value = 0;
  metrics.value = {};
  uiState.value = "NO_VIDEO";
}

function startWs() {
  errorMsg.value = "";
  if (!uploadedFilename.value) {
    errorMsg.value = "No uploaded filename.";
    return;
  }

  stopWs();

  const url = `${WS_BASE}/ws/stream/upload`;
  const socket = new WebSocket(url);
  ws.value = socket;

  socket.onopen = () => {
    uiState.value = "PLAYING";
    socket.send(JSON.stringify({ filename: uploadedFilename.value }));
  };

  socket.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);

    if (msg.type === "state") {
      uiState.value = msg.state || uiState.value;
      return;
    }
  
    if (msg.type === "error") {
      uiState.value = "ERROR";
      errorMsg.value = msg.message || "ws error";
      return;
    }

    if (msg.type === "end") {
      uiState.value = "END";
      return;
    }

    if (msg.type === "frame") {
      frameB64.value = msg.image_base64 || "";
      frameIndex.value = msg.frame_index || 0;
      metrics.value = msg.metrics || {};
    }
  };

  socket.onerror = () => {
    uiState.value = "ERROR";
    errorMsg.value = "WebSocket error";
  };

  socket.onclose = () => {
    if (uiState.value === "PLAYING" || uiState.value === "PAUSED") {
      // 의도치 않은 close면 상태 정리
      uiState.value = uploadedFilename.value ? "READY" : "NO_VIDEO";
    }
  };
}

function pauseWs() {
  if (!ws.value) return;
  ws.value.send(JSON.stringify({ type: "control", action: "pause" }));
}

function resumeWs() {
  if (!ws.value) return;
  ws.value.send(JSON.stringify({ type: "control", action: "resume" }));
}

function stopWs() {
  if (ws.value) {
    try {
      ws.value.send(JSON.stringify({ type: "control", action: "stop" }));
    } catch {}
    try { ws.value.close(); } catch {}
  }
  ws.value = null;
}

onBeforeUnmount(() => {
  stopWs();
});
</script>