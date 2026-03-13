<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">
    <!-- 왼쪽: 실시간 크롭 미리보기 -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-bold">후보군</h3>
        <div class="text-xs text-slate-500">미리보기 ({{ recentCrops.length }}장)</div>
      </div>
      <div class="bg-slate-100 rounded-xl border border-slate-200 p-3 h-[300px] overflow-y-auto">
        <div v-if="recentCrops.length === 0" class="h-full flex items-center justify-center text-sm text-slate-400">
          분석 시작 후 추출된 이미지가 표시됩니다
        </div>
        <div v-else class="grid grid-cols-3 gap-2">
          <div v-for="(item, i) in recentCrops" :key="item.id ?? i"
              class="aspect-square bg-slate-200 rounded-lg overflow-hidden relative"
              :class="{ 'opacity-30 grayscale': isRemoved(item.id) }">
            <img
              v-if="item.thumb"
              :src="`data:image/jpeg;base64,${item.thumb}`"
              class="w-full h-full object-cover"
            />
            <span class="absolute bottom-1 left-1 text-[10px] font-bold px-1 rounded"
                  :style="{ background: classColor(item.class_name), color: '#fff' }">
              {{ item.class_name }}
            </span>
            <!-- 제거 표시 -->
            <div v-if="analyzePhase === 'done' && isRemoved(item.id)"
                class="absolute inset-0 flex items-center justify-center">
              <span class="text-xl font-bold text-red-400">✕</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 중간: 최종 결과 -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-bold">필터링 결과</h3>
        <div class="text-xs text-slate-500">미리보기 ({{ recentCrops.length }}장 중 {{ filteredCrops.length }}장)</div>
      </div>
      <div class="bg-slate-100 rounded-xl border border-slate-200 p-3 h-[300px] overflow-y-auto">
        <div v-if="filteredCrops.length === 0" class="h-full flex items-center justify-center text-sm text-slate-400">
          {{ analyzePhase === 'done' ? '통과된 이미지 없음' : '분석 완료 후 표시됩니다' }}
        </div>
        <div v-else class="grid grid-cols-3 gap-2">
          <div v-for="(item, i) in filteredCrops" :key="item.id ?? i"
              class="aspect-square bg-slate-200 rounded-lg overflow-hidden relative">
            <img
              v-if="item.thumb"
              :src="`data:image/jpeg;base64,${item.thumb}`"
              class="w-full h-full object-cover"
            />
            <span class="absolute bottom-1 left-1 text-[10px] font-bold px-1 rounded"
                  :style="{ background: classColor(item.class_name), color: '#fff' }">
              {{ item.class_name }}
            </span>
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
          <span v-else-if="cancelToken > 0 && logRows.some(r => r.msg.includes('취소'))" class="text-red-400">취소됨</span>
          <span v-else-if="analyzePhase === 'done' || logRows.length > 0">완료</span>
        </div>
      </div>

      <div class="bg-slate-100 rounded-xl border border-slate-200 h-[300px] flex flex-col">
        <!-- 로그 스크롤 영역 -->
        <div ref="logEl" class="flex-1 overflow-y-auto p-3 font-mono text-sm space-y-1">
          <div v-if="logRows.length === 0" class="text-slate-400 mt-2">
            분석 시작 후 로그가 출력됩니다
          </div>
          <div v-for="(row, i) in logRows" :key="i"
               class="flex gap-2 text-slate-600 leading-5">
            <span class="text-slate-400 text-base shrink-0">{{ row.time }}</span>
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
  clearToken:     { type: Number,  default: 0 },
  writtenCounts: { type: Object, default: () => ({}) },
  recentCrops: { type: Array, default: () => [] },
  filteredCrops: { type: Array, default: () => [] },
  cancelToken: { type: Number, default: 0 },
});

const logEl   = ref(null);
const logRows = ref([]);

const removedSet = computed(() =>
  new Set(props.recentCrops
    .filter(c => !props.filteredCrops.find(f => f.id === c.id))
    .map(c => c.id)
  )
)

function isRemoved(id) {
  return !!id && removedSet.value.has(id)
}


// ── 완료 요약 문장 ────────────────────────────────────────────
const summary = computed(() => {
  if (props.analyzePhase !== "done") return null;
  if (props.isAnalyzing) return null;
  const parts = Object.entries(props.writtenCounts)
    .map(([cls, n]) => `${cls}: ${n}개`);
  if (!parts.length) return null;
  return parts.join(", ") + `  ·  총 ${props.analyzeWritten}개의 이미지가 추출되었습니다.`;
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
  lastDetCount = len;

  const total = props.analyzeWritten;
  if (!total || !Object.keys(props.writtenCounts).length) return;

  const parts = Object.entries(props.writtenCounts)
    .map(([cls, n]) => `${cls}: ${n}개 (${(n / total * 100).toFixed(1)}%)`)
    .join(", ");
  pushLog(`총 프레임 ${entry.frame_index}  →  ${parts}`, "text-slate-700 text-base");
});

// ── phase 변화 → 로그 출력 ──────────────────────────────────
watch(() => props.analyzePhase, (phase) => {
  if (phase === "analyzing")        pushLog("분석 시작", "text-sky-500 text-base");
  if (phase === "siglip")           pushLog("추론 완료 · SigLIP 필터링 중", "text-black-500 text-base");
  if (phase === "zipping_compress") pushLog("SigLIP 완료 · ZIP 압축 중", "text-black-500 text-base");
  if (phase === "done")             pushLog(`완료 · ${props.analyzeWritten}장 저장됨`, "text-emerald-500 text-base");
});

// ── 로그 reset용 ──────────────────────────────────
watch(() => props.clearToken, () => {
  logRows.value    = [];
  lastDetCount     = 0;
  // filteredCrops는 store에서 관리하므로 별도 처리 불필요
});

// ── 유틸 ────────────────────────────────────────────────────
function classColor(cls) {
  return { car: "#3b82f6", bus: "#f59e0b", truck: "#10b981" }[cls] ?? "#94a3b8";
}

// ── 생성 취소 ────────────────────────────────────────────────────
watch(() => props.cancelToken, (val) => {
  if (val === 0) return
  pushLog("생성 취소", "text-red-500 text-base")
})

</script>