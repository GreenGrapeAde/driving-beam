<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch">

    <!-- 왼쪽: 실시간 크롭 미리보기 -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-bold">실시간 미리보기</h3>
        <div class="text-xs text-slate-500">최근 추출 이미지</div>
      </div>
      <div class="bg-slate-100 rounded-xl border border-slate-200 p-3 h-[300px] overflow-y-auto">
        <div v-if="recentCrops.length === 0" class="h-full flex items-center justify-center text-sm text-slate-400">
          분석 시작 후 추출된 이미지가 표시됩니다
        </div>
        <div v-else class="grid grid-cols-3 gap-2">
          <div v-for="(item, i) in recentCrops" :key="i"
               class="aspect-square bg-slate-200 rounded-lg overflow-hidden flex items-center justify-center text-xs text-slate-500">
            <!-- 실제 이미지 없이 클래스 + 인덱스 카드로 표현 -->
            <div class="text-center px-1">
              <div class="text-lg font-bold" :style="{ color: classColor(item.cls) }">
                {{ clsEmoji(item.cls) }}
              </div>
              <div class="font-semibold text-slate-700">{{ item.cls }}</div>
              <div class="text-slate-400">#{{ item.idx }}</div>
              <div class="text-slate-400">{{ (item.conf * 100).toFixed(0) }}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 오른쪽: 실시간 로그 -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-bold">추출 로그</h3>
        <div class="text-xs text-slate-500">
          <span v-if="isAnalyzing" class="text-sky-500">● 분석 중</span>
          <span v-else-if="analyzePhase === 'done' || logRows.length > 0">완료</span>
        </div>
      </div>

      <div class="bg-slate-100 rounded-xl border border-slate-200 h-[300px] flex flex-col">
        <!-- 로그 스크롤 영역 -->
        <div ref="logEl" class="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-0.5">
          <div v-if="logRows.length === 0" class="text-slate-400 mt-2">
            분석 시작 후 로그가 출력됩니다
          </div>
          <div v-for="(row, i) in logRows" :key="i"
               class="flex gap-2 text-slate-600 leading-5">
            <span class="text-slate-400 shrink-0">{{ row.time }}</span>
            <span :class="row.color">{{ row.msg }}</span>
          </div>
        </div>

        <!-- 하단 요약 -->
        <div v-if="summary" class="border-t border-slate-200 px-3 py-2 text-xs text-slate-700 bg-white rounded-b-xl">
          {{ summary }}
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from "vue";

const props = defineProps({
  detList:       { type: Array,   default: () => [] },
  isAnalyzing:   { type: Boolean, default: false },
  analyzeWritten:{ type: Number,  default: 0 },
  analyzePhase:  { type: String,  default: "" },
});

const logEl   = ref(null);
const logRows = ref([]);

// ── 최근 크롭 카드 (det 기준, 최대 12개) ────────────────────
const recentCrops = computed(() => {
  const all = [];
  for (const entry of props.detList.slice(-30)) {
    for (const det of entry.detections ?? []) {
      all.push({ cls: det.cls, conf: det.conf, idx: all.length + 1 });
    }
  }
  return all.slice(-12).reverse();
});

// ── 클래스별 집계 ────────────────────────────────────────────
const classCounts = computed(() => {
  const counts = {};
  for (const entry of props.detList) {
    for (const det of entry.detections ?? []) {
      counts[det.cls] = (counts[det.cls] || 0) + 1;
    }
  }
  return counts;
});

// ── 완료 요약 문장 ────────────────────────────────────────────
const summary = computed(() => {
  if (props.analyzePhase !== "done" && !props.analyzeWritten) return null;
  if (props.isAnalyzing) return null;
  const parts = Object.entries(classCounts.value)
    .map(([cls, n]) => `${cls}: ${n}개`);
  if (!parts.length) return null;
  const total = Object.values(classCounts.value).reduce((a, b) => a + b, 0);
  return parts.join(", ") + `  ·  총 ${total}개의 이미지가 추출되었습니다.`;
});

// ── 로그 추가 헬퍼 ───────────────────────────────────────────
function now() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}:${String(d.getSeconds()).padStart(2,"0")}`;
}

function pushLog(msg, color = "text-slate-600") {
  logRows.value.push({ time: now(), msg, color });
  if (logRows.value.length > 200) logRows.value.shift();
  nextTick(() => {
    if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight;
  });
}

// ── detList 변화 감지 → 로그 출력 ───────────────────────────
let lastDetCount = 0;
watch(() => props.detList.length, (len) => {
  if (len <= lastDetCount) return;
  const entry = props.detList[len - 1];
  const dets  = entry?.detections ?? [];
  if (dets.length > 0) {
    const summary = dets.map(d => `${d.cls}(${(d.conf*100).toFixed(0)}%)`).join(", ");
    pushLog(`프레임 ${entry.frame_index}  →  ${summary}`, "text-slate-700");
  }
  lastDetCount = len;
});

// ── phase 변화 → 로그 출력 ──────────────────────────────────
watch(() => props.analyzePhase, (phase) => {
  if (phase === "analyzing") pushLog("분석 시작", "text-sky-500");
  if (phase === "zipping")   pushLog(`추론 완료 · ZIP 생성 중 (${props.analyzeWritten}장)`, "text-amber-500");
  if (phase === "done")      pushLog(`완료 · ${props.analyzeWritten}장 저장됨`, "text-emerald-500");
});

// ── 유틸 ────────────────────────────────────────────────────
function classColor(cls) {
  return { car: "#3b82f6", bus: "#f59e0b", truck: "#10b981" }[cls] ?? "#94a3b8";
}

function clsEmoji(cls) {
  return { car: "🚗", bus: "🚌", truck: "🚛" }[cls] ?? "🚙";
}
</script>