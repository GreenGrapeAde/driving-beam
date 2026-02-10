<template>
  <div class="card h-full flex flex-col">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm font-semibold">ADB Beam Visualization</div>
      <div class="text-xs text-slate-500">Slot {{ slotName }}</div>
    </div>

    <div class="beam-wrap" style="height: 420px;">
      <canvas ref="beamCanvas" class="beam-canvas"></canvas>
    </div>

    <div class="mt-2 text-xs text-slate-600">
      WS: beam mask / polygons → canvas render (TODO)
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";

defineProps({
  slotName: { type: String, required: true },
});

const beamCanvas = ref(null);

onMounted(() => {
  const c = beamCanvas.value;
  if (!c) return;

  const rect = c.parentElement.getBoundingClientRect();
  c.width = Math.floor(rect.width);
  c.height = Math.floor(rect.height);

  const ctx = c.getContext("2d");

  // 더미 빔: 전체는 밝게 + 차량 차단 영역은 어둡게
  ctx.fillStyle = "rgba(255, 243, 200, 0.30)";
  ctx.fillRect(0, 0, c.width, c.height);

  // 차단 영역(폴리곤) 예시
  ctx.fillStyle = "rgba(0,0,0,0.45)";
  ctx.fillRect(c.width * 0.25, c.height * 0.35, c.width * 0.5, c.height * 0.25);

  ctx.strokeStyle = "rgba(255,255,255,0.5)";
  ctx.strokeRect(c.width * 0.25, c.height * 0.35, c.width * 0.5, c.height * 0.25);
});
</script>

<style scoped>

.beam-wrap {
  width: 100%;
  /* height: var(--pane-h);   여기서도 변수로 통일 */
  border-radius: 14px;
  overflow: hidden;
  background: #0b1220;
}

.beam-canvas {
  width: 100%;
  height: 100%;
}
</style>
