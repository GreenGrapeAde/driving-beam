<template>
  <div class="panel">
    <div class="flex items-center justify-between gap-3 mb-3">
      <div>
        <h2 class="text-lg font-bold">{{ title }}</h2>
        <p class="text-xs text-slate-600">
          {{ mode === "live" ? "Live stream + WebSocket overlay" : "Playback file + overlay" }}
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button class="ui-btn" @click="onLoadModel">
          Load Model
        </button>
        <button class="ui-btn-secondary" @click="onTestPing">
          Test
        </button>
      </div>
    </div>

    <div class="flex flex-col gap-4">
      <VideoWithOverlay :slotName="slotName" @upload="onUpload" />
      <BeamPanel :slotName="slotName" />
    </div>
  </div>
</template>

<script setup>
import VideoWithOverlay from "./VideoWithOverlay.vue";
import BeamPanel from "./BeamPanel.vue";

const props = defineProps({
  mode: { type: String, required: true },
  slotName: { type: String, required: true }, // 'A' | 'B'
  title: { type: String, required: true },
});

function onLoadModel() {
  // TODO: 파일 선택 → FastAPI 업로드 → slot(A/B) assign
  alert(`[${props.slotName}] Load Model (TODO)`);
}

function onTestPing() {
  // TODO: /health 또는 ws 연결 테스트
  alert(`[${props.slotName}] Test (TODO)`);
}
</script>
